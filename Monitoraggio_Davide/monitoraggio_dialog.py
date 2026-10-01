import os
import tempfile

from qgis.PyQt.QtCore import QSettings, Qt, QThread, QTimer, QUrl
from qgis.PyQt.QtGui import QColor, QBrush, QDesktopServices
from qgis.PyQt.QtWidgets import (
    QAbstractItemView, QCheckBox, QComboBox, QDialog,
    QFileDialog, QFormLayout, QFrame, QGridLayout, QGroupBox, QHBoxLayout,
    QHeaderView, QLabel, QLineEdit, QMessageBox, QProgressBar, QPushButton,
    QScrollArea, QSizePolicy, QSpinBox, QTabWidget, QTableWidget,
    QTableWidgetItem, QTextEdit, QVBoxLayout, QWidget
)

from .config import AREAS, DEFAULT_AREA, DEFAULT_PROVINCE, PLUGIN_VERSION, SENSOR_TYPES, SOURCE_CATALOG
from .database import POSTGIS_NOTE, initialize_sqlite, save_diagnostic, save_radar_product, upsert_sources
from .core.freshness import annotate_freshness
from .diagnostics import DiagnosticWorker
from .connectors.arpa_lombardia import ArpaLombardiaWorker
from .connectors.arpav import ArpavWorker
from .connectors.ingv import IngvWorker
from .connectors.meteotrentino import MeteotrentinoWorker
from .connectors.arpae_emilia_romagna import ArpaeEmiliaRomagnaWorker
from .connectors.aineva import AinevaWorker
from .connectors.radar_lombardia import RadarLombardiaWorker
from .map_manager import (
    ensure_google_hybrid, replace_capitals_layer, replace_earthquake_layer,
    replace_radar_layer, replace_sensor_layer, set_lombardia_rip,
)
from .qt_compat import (
    ALIGN_CENTER, HEADER_CONTENTS, HEADER_STRETCH, NON_MODAL,
    NO_EDIT_TRIGGERS, WINDOW, WINDOW_CLOSE, WINDOW_MAXIMIZE, WINDOW_MINIMIZE,
)
from .thresholds import apply_thresholds, load_thresholds, write_template


STYLE = """
QWidget#monitorRoot { background:#f4f6f7; color:#000; }
QLabel#titleLabel { font-size:13pt; font-weight:700; }
QLabel#heartbeatLabel { background:#edf7f0; border:1px solid #b9d7c2; border-radius:5px; padding:2px 7px; font-weight:700; }
QLabel#statusChip { background:#e8f3ec; border:1px solid #b9d6c2; border-radius:9px; padding:4px 8px; font-weight:600; }
QTabWidget::pane { border:1px solid #d6dde2; background:#fff; }
QTabBar::tab { background:#e9edf0; border:1px solid #d4dbe0; padding:6px 8px; margin-right:1px; font-weight:600; }
QTabBar::tab:selected { background:#fff; border-bottom:3px solid #4d8b61; }
QGroupBox { background:#fff; border:1px solid #d8dee3; border-radius:6px; margin-top:12px; padding-top:9px; font-weight:700; }
QGroupBox::title { subcontrol-origin:margin; left:9px; padding:0 5px; }
QLineEdit,QComboBox,QTextEdit,QTableWidget,QSpinBox { background:#fff; border:1px solid #cdd5db; border-radius:4px; padding:4px; selection-background-color:#dceee2; }
QHeaderView::section { background:#edf1f3; border:0; border-right:1px solid #d9dfe3; border-bottom:1px solid #d9dfe3; padding:5px; font-weight:700; }
QPushButton { background:#f7f9fa; border:1px solid #c7d0d6; border-radius:5px; padding:7px 9px; min-height:18px; }
QPushButton:hover { background:#e9eef1; }
QPushButton:checked,QPushButton#primaryButton { background:#4d8b61; color:#fff; border:1px solid #3e7550; font-weight:700; }
QPushButton#quickButton { background:#eaf3ed; border:1px solid #b6cfbe; font-weight:700; }
QProgressBar { border:1px solid #cdd5db; border-radius:4px; background:#f8fafb; text-align:center; }
QProgressBar::chunk { background:#6aa37a; border-radius:3px; }
"""


class MonitoraggioDialog(QDialog):
    def __init__(self, iface, parent=None):
        super().__init__(parent)
        self.iface = iface
        self.settings = QSettings("MonitoraggioDavide", "QGISPlugin")
        self.diag_rows = []
        self.diag_thread = None
        self.diag_worker = None
        self.arpa_thread = None
        self.arpa_worker = None
        self._arpa_queue = []
        self._arpa_totals = None
        self._pending_regional_reload = False
        self.ingv_thread = None
        self.ingv_worker = None
        self.aineva_thread = None
        self.aineva_worker = None
        self.radar_thread = None
        self.radar_worker = None
        self.live_layer = None
        self.thresholds = []
        self.threshold_path = self.settings.value("threshold_csv", "", type=str)
        self.cache_path = self.settings.value("cache_sqlite", "", type=str)
        if self.threshold_path and os.path.isfile(self.threshold_path):
            try: self.thresholds = load_thresholds(self.threshold_path)
            except Exception: self.thresholds = []
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self._auto_refresh)
        self.setWindowTitle("Monitoraggio Davide · v%s" % PLUGIN_VERSION)
        self.setWindowFlags(WINDOW | WINDOW_MINIMIZE | WINDOW_MAXIMIZE | WINDOW_CLOSE)
        self.setWindowModality(NON_MODAL)
        self.setMinimumSize(800, 560)
        self.resize(1120, 760)
        self._build()
        self.clock = QTimer(self)
        self.clock.timeout.connect(self._tick)
        self.clock.start(1000)
        self._tick()
        QTimer.singleShot(700, self.open_live_view)

    def _build(self):
        self.setStyleSheet(STYLE)
        root_widget = QWidget(self); root_widget.setObjectName("monitorRoot")
        outer = QVBoxLayout(self); outer.setContentsMargins(0,0,0,0); outer.addWidget(root_widget)
        root = QVBoxLayout(root_widget); root.setContentsMargins(6,6,6,6); root.setSpacing(5)
        header = QGridLayout()
        title = QLabel("Monitoraggio Davide · Quadro operativo"); title.setObjectName("titleLabel")
        self.live = QLabel(); self.live.setObjectName("heartbeatLabel")
        self.status = QLabel("Lombardia · Brescia"); self.status.setObjectName("statusChip")
        self.phase = QLabel("Pronto")
        self.progress = QProgressBar(); self.progress.setRange(0,100); self.progress.setValue(0); self.progress.setFixedWidth(180)
        self.source_status = QLabel("Fonti: non verificate")
        self.btn_detail = QPushButton("DETTAGLI DIAGNOSTICA"); self.btn_detail.clicked.connect(lambda: self.tabs.setCurrentWidget(self.diag_page))
        header.addWidget(title,0,0); header.addWidget(self.live,0,1); header.setColumnStretch(2,1); header.addWidget(self.status,0,3)
        header.addWidget(self.phase,1,0); header.addWidget(self.progress,1,1); header.addWidget(self.source_status,1,2); header.addWidget(self.btn_detail,1,3)
        root.addLayout(header)

        geo = QHBoxLayout(); geo.addWidget(QLabel("ZONE MONITORATE:"))
        self.all_areas = QCheckBox("Tutte")
        self.all_areas.setToolTip("Seleziona contemporaneamente tutte le aree")
        self.all_areas.toggled.connect(self._toggle_all_areas)
        geo.addWidget(self.all_areas)
        self.area_buttons = {}
        for area in AREAS:
            button = QCheckBox(area)
            button.setToolTip("Aggiungi o rimuovi %s dal monitoraggio" % area)
            self.area_buttons[area] = button
            button.toggled.connect(lambda checked=False, a=area: self._area_toggled(a, checked)); geo.addWidget(button)
        geo.addSpacing(10); geo.addWidget(QLabel("Provincia / capoluogo:")); self.province = QComboBox(); self.province.currentTextChanged.connect(self._province_changed); geo.addWidget(self.province)
        self.btn_brescia = QPushButton("BRESCIA"); self.btn_brescia.setObjectName("quickButton"); self.btn_brescia.clicked.connect(lambda: self.set_area("Lombardia", "Brescia")); geo.addWidget(self.btn_brescia)
        self.btn_padova = QPushButton("PADOVA"); self.btn_padova.setObjectName("quickButton"); self.btn_padova.clicked.connect(lambda: self.set_area("Veneto", "Padova")); geo.addWidget(self.btn_padova)
        geo.addStretch(1); root.addLayout(geo)

        live_row = QHBoxLayout()
        self.btn_open_live = QPushButton("APRI QUADRO LIVE")
        self.btn_open_live.setObjectName("primaryButton")
        self.btn_open_live.clicked.connect(self.open_live_view)
        live_row.addWidget(self.btn_open_live)
        self.auto_refresh = QCheckBox("Aggiornamento automatico")
        self.auto_refresh.setChecked(True)
        self.auto_refresh.toggled.connect(self._toggle_refresh)
        live_row.addWidget(self.auto_refresh)
        self.rip_checkbox = QCheckBox("Reticolo Idrico Principale Lombardia")
        self.rip_checkbox.setChecked(True)
        self.rip_checkbox.setToolTip("RIP ufficiale Regione Lombardia · Allegato A D.G.R. XII/3668/2024")
        self.rip_checkbox.toggled.connect(self._toggle_rip)
        live_row.addWidget(self.rip_checkbox)
        self.capitals_checkbox = QCheckBox("Capoluoghi in mappa")
        self.capitals_checkbox.setChecked(True)
        self.capitals_checkbox.toggled.connect(self._toggle_capitals)
        live_row.addWidget(self.capitals_checkbox)
        live_row.addWidget(QLabel("Ogni"))
        self.refresh_minutes = QSpinBox(); self.refresh_minutes.setRange(5, 60); self.refresh_minutes.setValue(10); self.refresh_minutes.setSuffix(" min")
        self.refresh_minutes.valueChanged.connect(self._toggle_refresh)
        live_row.addWidget(self.refresh_minutes)
        self.last_refresh = QLabel("Non ancora aggiornato")
        live_row.addWidget(self.last_refresh, 1)
        root.addLayout(live_row)

        self.tabs = QTabWidget(); self.tabs.setUsesScrollButtons(True); self.tabs.tabBar().setExpanding(False); root.addWidget(self.tabs,1)
        self._dashboard(); self._sensors(); self._meteo_radar()
        self._placeholder("Fiumi e dighe", "Idrometri, portate, invasi, scarichi e serie temporali.")
        self._snow()
        self._placeholder("Frane", "Piezometri, inclinometri, estensimetri, GNSS e stato dei sistemi.")
        self._seismic()
        self._placeholder("Copernicus", "CEMS Rapid Mapping, GFM/EFAS, EFFIS e immagini Sentinel.")
        self._thresholds_page()
        self._diagnostics(); self._settings()
        self.set_area(DEFAULT_AREA, DEFAULT_PROVINCE[DEFAULT_AREA])

    def _dashboard(self):
        page = QWidget(); layout = QVBoxLayout(page)
        box = QGroupBox("Sintesi operativa"); grid = QGridLayout(box)
        cards = [("Sensori caricati","—","#edf7f0"),("Con ultimo dato","—","#fff7df"),("Allarmi","—","#fdecec"),("Fonti disponibili",str(len(SOURCE_CATALOG)),"#eef1f3")]
        for i,(label,value,color) in enumerate(cards):
            card=QLabel("%s\n%s"%(label,value)); card.setAlignment(ALIGN_CENTER); card.setStyleSheet("background:%s;border:1px solid #d8dee3;border-radius:7px;padding:18px;font-size:11pt;font-weight:700;"%color); grid.addWidget(card,0,i)
            if i == 0: self.card_sensors = card
            if i == 1: self.card_measures = card
            if i == 2: self.card_alerts = card
        layout.addWidget(box)
        monitoring=QGroupBox("Monitoraggio CFMR Lombardia"); actions=QGridLayout(monitoring)
        self.btn_radar=QPushButton("CARICA RADAR ARPA"); self.btn_radar.setObjectName("primaryButton"); self.btn_radar.clicked.connect(self.load_radar); actions.addWidget(self.btn_radar,0,0)
        self.radar_label=QLabel("Composito radar non ancora caricato"); self.radar_label.setWordWrap(True); actions.addWidget(self.radar_label,0,1,1,4)
        links=(
            ("ALLERTALOM","https://www.allertalom.regione.lombardia.it/"),
            ("ARCHIVIO BMP","https://www.allertalom.regione.lombardia.it/comunicati?t=CFMRPREV"),
            ("LIRIS GUEST","https://iris.arpalombardia.it/gisINM/login.php"),
            ("RADARLOM","https://www.arpalombardia.it/temi-ambientali/meteo-e-clima/radar-meteo/"),
            ("PVR · ACCESSO ISTITUZIONALE","https://www.protezionecivile.servizirl.it/servizi/servizi/dettaglio?id=49"),
        )
        for column,(label,url) in enumerate(links):
            button=QPushButton(label); button.clicked.connect(lambda checked=False, target=url: QDesktopServices.openUrl(QUrl(target))); actions.addWidget(button,1,column)
        access_note=QLabel("Dati radar e collegamenti ufficiali. PVR/SINERGIE 2.0 richiede accesso autorizzato; il plugin non memorizza credenziali."); access_note.setWordWrap(True); actions.addWidget(access_note,2,0,1,5)
        layout.addWidget(monitoring)
        note=QLabel("v%s · Reti regionali, ARPAE Emilia-Romagna, INGV e soglie documentate. I dati automatici recenti possono essere provvisori." % PLUGIN_VERSION); note.setWordWrap(True); layout.addWidget(note); layout.addStretch(1)
        self.tabs.addTab(page,"Sala Operativa")

    def _sensors(self):
        page=QWidget(); layout=QVBoxLayout(page); table=QTableWidget(len(SENSOR_TYPES),4)
        table.setHorizontalHeaderLabels(["Tipo sensore","Unita","Stato tecnico","Criticita misura"]); table.verticalHeader().setVisible(False); table.setEditTriggers(NO_EDIT_TRIGGERS); table.setAlternatingRowColors(True)
        for row,(kind,unit) in enumerate(SENSOR_TYPES):
            for col,value in enumerate((kind,unit,"Da collegare","Non disponibile")): table.setItem(row,col,QTableWidgetItem(value))
        table.horizontalHeader().setSectionResizeMode(0,HEADER_STRETCH)
        for col in (1,2,3): table.horizontalHeader().setSectionResizeMode(col,HEADER_CONTENTS)
        layout.addWidget(table); self.tabs.addTab(page,"Sensori")

    def _placeholder(self, tab, text):
        page=QWidget(); layout=QVBoxLayout(page); box=QGroupBox(tab); bl=QVBoxLayout(box); label=QLabel(text); label.setWordWrap(True); bl.addWidget(label); bl.addWidget(QLabel("Modulo predisposto per i connettori della fase successiva.")); layout.addWidget(box); layout.addStretch(1); self.tabs.addTab(page,tab)

    def _meteo_radar(self):
        page=QWidget(); layout=QVBoxLayout(page)
        commands=QHBoxLayout(); self.btn_arpa=QPushButton("CARICA RETE REGIONALE"); self.btn_arpa.setObjectName("primaryButton"); self.btn_arpa.clicked.connect(self.load_arpa); commands.addWidget(self.btn_arpa)
        self.arpa_label=QLabel("Pronto · il filtro geografico usa la provincia selezionata"); commands.addWidget(self.arpa_label,1); layout.addLayout(commands)
        self.arpa_table=QTableWidget(0,12); self.arpa_table.setHorizontalHeaderLabels(["Stazione","Comune","Prov.","Sensore","Unita","Quota","Ultimo dato","Criticita","Freschezza","Eta min","Data/ora","ID sensore"]); self.arpa_table.verticalHeader().setVisible(False); self.arpa_table.setEditTriggers(NO_EDIT_TRIGGERS); self.arpa_table.setAlternatingRowColors(True)
        self.arpa_table.horizontalHeader().setSectionResizeMode(0,HEADER_STRETCH)
        for col in range(1,12): self.arpa_table.horizontalHeader().setSectionResizeMode(col,HEADER_CONTENTS)
        layout.addWidget(self.arpa_table,1); self.tabs.addTab(page,"Meteo e radar")

    def _seismic(self):
        page=QWidget(); layout=QVBoxLayout(page)
        actions=QHBoxLayout(); self.btn_ingv=QPushButton("CARICA TERREMOTI INGV"); self.btn_ingv.setObjectName("primaryButton"); self.btn_ingv.clicked.connect(self.load_ingv); actions.addWidget(self.btn_ingv)
        self.ingv_label=QLabel("Eventi degli ultimi 7 giorni nell'Italia settentrionale"); actions.addWidget(self.ingv_label,1); layout.addLayout(actions)
        self.ingv_table=QTableWidget(0,6); self.ingv_table.setHorizontalHeaderLabels(["Data/ora","Magnitudo","Tipo","Profondita km","Localita","ID evento"]); self.ingv_table.verticalHeader().setVisible(False); self.ingv_table.setEditTriggers(NO_EDIT_TRIGGERS); self.ingv_table.setAlternatingRowColors(True)
        for col in (0,1,2,3,5): self.ingv_table.horizontalHeader().setSectionResizeMode(col,HEADER_CONTENTS)
        self.ingv_table.horizontalHeader().setSectionResizeMode(4,HEADER_STRETCH); layout.addWidget(self.ingv_table,1); self.tabs.addTab(page,"Sismica")

    def _snow(self):
        page=QWidget(); layout=QVBoxLayout(page)
        actions=QHBoxLayout(); self.btn_aineva=QPushButton("CARICA BOLLETTINO AINEVA"); self.btn_aineva.setObjectName("primaryButton"); self.btn_aineva.clicked.connect(self.load_aineva); actions.addWidget(self.btn_aineva)
        open_button=QPushButton("APRI BOLLETTINO UFFICIALE"); open_button.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://bollettini.aineva.it/bulletin/latest"))); actions.addWidget(open_button)
        self.aineva_label=QLabel("Bollettino stagionale neve e valanghe · open data CAAML"); actions.addWidget(self.aineva_label,1); layout.addLayout(actions)
        self.aineva_table=QTableWidget(0,7); self.aineva_table.setHorizontalHeaderLabels(["Pubblicato","Valido da","Valido a","Pericolo max","Livelli","Problemi valanghivi","Aree"]); self.aineva_table.verticalHeader().setVisible(False); self.aineva_table.setEditTriggers(NO_EDIT_TRIGGERS)
        for col in range(5): self.aineva_table.horizontalHeader().setSectionResizeMode(col,HEADER_CONTENTS)
        self.aineva_table.horizontalHeader().setSectionResizeMode(5,HEADER_STRETCH); self.aineva_table.horizontalHeader().setSectionResizeMode(6,HEADER_STRETCH)
        layout.addWidget(self.aineva_table)
        note=QLabel("I sensori nivometrici e nivopluviometrici delle reti regionali restano disponibili nella scheda Meteo e radar. Il bollettino AINEVA esprime un pericolo per zone, non per il singolo pendio."); note.setWordWrap(True); layout.addWidget(note); layout.addStretch(1)
        self.tabs.addTab(page,"Neve e valanghe")

    def _thresholds_page(self):
        page=QWidget(); layout=QVBoxLayout(page)
        actions=QHBoxLayout(); load=QPushButton("IMPORTA SOGLIE CSV"); load.setObjectName("primaryButton"); load.clicked.connect(self.import_thresholds); actions.addWidget(load)
        template=QPushButton("CREA MODELLO CSV"); template.clicked.connect(self.save_threshold_template); actions.addWidget(template)
        clear=QPushButton("RIMUOVI SOGLIE"); clear.clicked.connect(self.clear_thresholds); actions.addWidget(clear); actions.addStretch(1); layout.addLayout(actions)
        self.threshold_label=QLabel("Nessuna soglia caricata. Sono accettate solo soglie accompagnate da fonte/riferimento."); self.threshold_label.setWordWrap(True); layout.addWidget(self.threshold_label)
        self.threshold_table=QTableWidget(0,9); self.threshold_table.setHorizontalHeaderLabels(["Fonte","ID sensore","Stazione","Sensore","Direzione","Attenzione","Preallarme","Allarme","Riferimento"]); self.threshold_table.verticalHeader().setVisible(False); self.threshold_table.setEditTriggers(NO_EDIT_TRIGGERS)
        self.threshold_table.horizontalHeader().setSectionResizeMode(2,HEADER_STRETCH)
        for col in (0,1,3,4,5,6,7,8): self.threshold_table.horizontalHeader().setSectionResizeMode(col,HEADER_CONTENTS)
        layout.addWidget(self.threshold_table,1); self.tabs.addTab(page,"Eventi e soglie"); self._refresh_threshold_table()

    def _diagnostics(self):
        self.diag_page=QWidget(); layout=QVBoxLayout(self.diag_page)
        actions=QHBoxLayout(); self.btn_diag=QPushButton("ESEGUI TEST FONTI"); self.btn_diag.setObjectName("primaryButton"); self.btn_diag.clicked.connect(self.run_diagnostics); actions.addWidget(self.btn_diag)
        actions.addStretch(1); layout.addLayout(actions)
        self.diag_summary=QLabel("Nessun test eseguito."); layout.addWidget(self.diag_summary)
        self.diag_table=QTableWidget(0,6); self.diag_table.setHorizontalHeaderLabels(["Fonte","Gruppo","Esito","HTTP","ms","Dettaglio"]); self.diag_table.verticalHeader().setVisible(False); self.diag_table.setEditTriggers(NO_EDIT_TRIGGERS); self.diag_table.setAlternatingRowColors(True)
        for col in range(5): self.diag_table.horizontalHeader().setSectionResizeMode(col,HEADER_CONTENTS)
        self.diag_table.horizontalHeader().setSectionResizeMode(5,HEADER_STRETCH); layout.addWidget(self.diag_table,1); self.tabs.addTab(self.diag_page,"Diagnostica")

    def _settings(self):
        page=QWidget(); layout=QVBoxLayout(page)
        db=QGroupBox("Geodatabase"); form=QFormLayout(db); self.pg_host=QLineEdit(); self.pg_db=QLineEdit("monitoraggio_utr"); self.pg_user=QLineEdit(); self.pg_port=QSpinBox(); self.pg_port.setRange(1,65535); self.pg_port.setValue(5432)
        form.addRow("Server PostGIS",self.pg_host); form.addRow("Database",self.pg_db); form.addRow("Porta",self.pg_port); form.addRow("Utente",self.pg_user); note=QLabel(POSTGIS_NOTE); note.setWordWrap(True); form.addRow(note)
        self.cache_path_edit=QLineEdit(self.cache_path); self.cache_path_edit.setReadOnly(True); form.addRow("Cache SQLite",self.cache_path_edit)
        cache=QPushButton("CREA/SELEZIONA CACHE SQLITE"); cache.clicked.connect(self.create_cache); form.addRow(cache); layout.addWidget(db)
        src=QGroupBox("Fonti predisposte"); sl=QVBoxLayout(src)
        for item in SOURCE_CATALOG: sl.addWidget(QLabel("• %s · %s"%(item["name"],item["group"])))
        layout.addWidget(src); layout.addStretch(1); self.tabs.addTab(page,"Impostazioni")

    def selected_areas(self):
        return [area for area in AREAS if self.area_buttons[area].isChecked()]

    def set_area(self, area, province=None):
        """Selezione rapida esclusiva usata dai pulsanti Brescia e Padova."""
        had_selection = bool(getattr(self, "current_area", None))
        for name, button in self.area_buttons.items():
            button.blockSignals(True); button.setChecked(name == area); button.blockSignals(False)
        self._sync_area_controls(preferred_province=province or DEFAULT_PROVINCE[area])
        if had_selection:
            self._queue_regional_reload()

    def _area_toggled(self, area, checked):
        selected = self.selected_areas()
        if not selected:
            self.area_buttons[area].blockSignals(True)
            self.area_buttons[area].setChecked(True)
            self.area_buttons[area].blockSignals(False)
            selected = [area]
        self._sync_area_controls()
        self._queue_regional_reload()

    def _toggle_all_areas(self, checked):
        if checked:
            target = set(AREAS)
        elif len(self.selected_areas()) == len(AREAS):
            target = {DEFAULT_AREA}
        else:
            return
        for area, button in self.area_buttons.items():
            button.blockSignals(True); button.setChecked(area in target); button.blockSignals(False)
        preferred = DEFAULT_PROVINCE[DEFAULT_AREA] if len(target) == 1 else None
        self._sync_area_controls(preferred_province=preferred)
        self._queue_regional_reload()

    def _sync_area_controls(self, preferred_province=None):
        selected = self.selected_areas()
        self.current_area = selected[0]
        self.all_areas.blockSignals(True)
        self.all_areas.setChecked(len(selected) == len(AREAS))
        self.all_areas.blockSignals(False)
        previous = self.province.currentText()
        self.province.blockSignals(True)
        self.province.clear()
        if len(selected) == 1:
            area = selected[0]
            self.province.addItem("Tutta la regione" if area != "Trentino" else "Tutta la provincia")
            self.province.addItems(AREAS[area])
            target = preferred_province or (previous if self.province.findText(previous) >= 0 else DEFAULT_PROVINCE[area])
            self.province.setCurrentIndex(max(0, self.province.findText(target)))
            self.province.setEnabled(True)
        else:
            self.province.addItem("Tutte le province · %d aree" % len(selected))
            self.province.setEnabled(False)
        self.province.blockSignals(False)
        self._update_geo_status()
        if hasattr(self, "capitals_checkbox"):
            self._refresh_capitals_layer()

    def _province_changed(self, _text):
        self._update_geo_status()
        if getattr(self, "current_area", None) is not None and len(self.selected_areas()) == 1:
            self._queue_regional_reload()

    def _queue_regional_reload(self):
        self._pending_regional_reload = True
        self.arpa_label.setText("Cambio aree in corso · preparo %s" % ", ".join(self.selected_areas()))
        if self.arpa_thread is None:
            QTimer.singleShot(0, self._run_pending_regional_reload)

    def _run_pending_regional_reload(self):
        if self._pending_regional_reload and self.arpa_thread is None:
            self._pending_regional_reload = False
            self.load_arpa(silent=True)
    def _update_geo_status(self):
        selected = self.selected_areas() if hasattr(self, "area_buttons") else [DEFAULT_AREA]
        area_text = "Tutte le aree" if len(selected) == len(AREAS) else " + ".join(selected)
        detail = self.province.currentText() if len(selected) == 1 else "%d regioni" % len(selected)
        self.status.setText("%s · %s" % (area_text, detail))
    def _tick(self): self.live.setText("v%s · LIVE %s" % (PLUGIN_VERSION, __import__("datetime").datetime.now().strftime("%H:%M:%S")))

    def open_live_view(self):
        try:
            ensure_google_hybrid()
            set_lombardia_rip(self.rip_checkbox.isChecked())
            self._refresh_capitals_layer()
            self._toggle_refresh()
            if self.selected_areas() and self.arpa_thread is None:
                self.load_arpa()
            if "Lombardia" in self.selected_areas() and self.radar_thread is None:
                self.load_radar(silent=True)
            if self.ingv_thread is None:
                self.load_ingv(silent=True)
        except Exception as exc:
            self.phase.setText("Errore basemap")
            QMessageBox.warning(self, "Monitoraggio Davide · Mappa", str(exc))

    def _toggle_rip(self, enabled):
        try:
            layer = set_lombardia_rip(enabled)
            self.phase.setText("Reticolo Idrico Principale attivo" if layer else "Reticolo Idrico Principale disattivato")
        except Exception as exc:
            self.rip_checkbox.blockSignals(True); self.rip_checkbox.setChecked(False); self.rip_checkbox.blockSignals(False)
            self.phase.setText("Errore Reticolo Idrico Principale")
            QMessageBox.warning(self, "Monitoraggio Davide · RIP Lombardia", str(exc))

    def _toggle_capitals(self, _enabled):
        self._refresh_capitals_layer()

    def _refresh_capitals_layer(self):
        try:
            _layer, count = replace_capitals_layer(self.selected_areas(), self.capitals_checkbox.isChecked())
            if self.capitals_checkbox.isChecked():
                self.phase.setText("Capoluoghi aggiornati · %d punti" % count)
        except Exception as exc:
            self.phase.setText("Capoluoghi non caricati · %s" % exc)

    def _toggle_refresh(self, *_args):
        if self.auto_refresh.isChecked():
            self.refresh_timer.start(self.refresh_minutes.value() * 60 * 1000)
        else:
            self.refresh_timer.stop()

    def _auto_refresh(self):
        if self.selected_areas() and self.arpa_thread is None:
            self.load_arpa(silent=True)
        if "Lombardia" in self.selected_areas() and self.radar_thread is None:
            self.load_radar(silent=True)
        if self.ingv_thread is None:
            self.load_ingv(silent=True)

    def load_radar(self, silent=False):
        if self.radar_thread:
            return
        self._radar_silent = silent
        self.btn_radar.setEnabled(False); self.radar_label.setText("Scarico l'ultimo composito radar ARPA Lombardia...")
        self.radar_thread=QThread(self); self.radar_worker=RadarLombardiaWorker(); self.radar_worker.moveToThread(self.radar_thread)
        self.radar_thread.started.connect(self.radar_worker.run); self.radar_worker.progress.connect(self._diag_progress)
        self.radar_worker.finished.connect(self._radar_finished); self.radar_worker.failed.connect(self._radar_failed)
        self.radar_worker.finished.connect(self.radar_thread.quit); self.radar_worker.failed.connect(self.radar_thread.quit)
        self.radar_thread.finished.connect(self._radar_cleanup); self.radar_thread.start()

    def _radar_finished(self, product):
        try:
            layer=replace_radar_layer(product)
            self.radar_label.setText("Radar caricato · %s · %s byte compressi" % (product.get("observed_at_utc", ""), product.get("compressed_bytes", 0)))
            self.phase.setText("Radar ARPA Lombardia aggiornato")
            self.iface.setActiveLayer(layer)
            if self.cache_path and os.path.isfile(self.cache_path):
                save_radar_product(self.cache_path, product)
        except Exception as exc:
            self._radar_failed("%s: %s" % (type(exc).__name__, exc))

    def _radar_failed(self, message):
        self.radar_label.setText("Radar non caricato · " + message); self.phase.setText("Errore radar ARPA Lombardia")
        if not getattr(self, "_radar_silent", False):
            QMessageBox.warning(self,"Monitoraggio Davide · Radar ARPA Lombardia",message)

    def _radar_cleanup(self):
        self.radar_thread.deleteLater(); self.radar_thread=None; self.radar_worker=None; self.btn_radar.setEnabled(True)

    def load_arpa(self, silent=False):
        if self.arpa_thread:
            return
        areas = self.selected_areas()
        if not areas:
            return
        province = self.province.currentText() if len(areas) == 1 else ""
        if not province or province.startswith("Tutta"):
            province = ""
        self._arpa_silent = silent
        self._arpa_queue = [{"area": area, "province": province if len(areas) == 1 else ""} for area in areas]
        self._arpa_totals = {
            "stations": 0, "sensors": 0, "measurements": 0, "points": 0,
            "alerts": 0, "attention": 0, "prealarm": 0,
            "recent": 0, "delayed": 0, "expired": 0, "errors": [], "sources": [],
        }
        self.arpa_table.setRowCount(0)
        self.btn_arpa.setEnabled(False)
        self.phase.setText("Avvio %d reti regionali" % len(areas))
        self.progress.setValue(0)
        self._start_next_regional_worker()

    def _start_next_regional_worker(self):
        if not self._arpa_queue:
            self._complete_regional_load()
            return
        item = self._arpa_queue.pop(0)
        area, province = item["area"], item["province"]
        source = {"Lombardia": "ARPA Lombardia", "Veneto": "ARPAV", "Trentino": "Meteotrentino", "Emilia-Romagna": "ARPAE Emilia-Romagna"}[area]
        self._arpa_active_area = area
        self._arpa_active_province = province
        self.current_source = source
        self.phase.setText("Avvio " + source)
        if area == "Lombardia": worker = ArpaLombardiaWorker(province=province)
        elif area == "Veneto": worker = ArpavWorker(province=province)
        elif area == "Trentino": worker = MeteotrentinoWorker()
        else: worker = ArpaeEmiliaRomagnaWorker()
        self.arpa_thread=QThread(self); self.arpa_worker=worker; self.arpa_worker.moveToThread(self.arpa_thread); self.arpa_thread.started.connect(self.arpa_worker.run); self.arpa_worker.progress.connect(self._diag_progress); self.arpa_worker.finished.connect(self._arpa_finished); self.arpa_worker.failed.connect(self._arpa_failed); self.arpa_worker.finished.connect(self.arpa_thread.quit); self.arpa_worker.failed.connect(self.arpa_thread.quit); self.arpa_thread.finished.connect(self._arpa_cleanup); self.arpa_thread.start()

    def _arpa_finished(self,stations,summary):
        source = getattr(self, "current_source", "Rete regionale")
        freshness=annotate_freshness(stations)
        counts=apply_thresholds(stations,self.thresholds,source)
        start_row = self.arpa_table.rowCount()
        self.arpa_table.setRowCount(start_row + len(stations))
        for row,station in enumerate(stations):
            latest=station.get("latest") or {}; value=latest.get("value"); values=(station.get("name"),station.get("municipality"),station.get("province"),station.get("sensor_type"),station.get("unit"),station.get("elevation"),"" if value is None else str(value),station.get("criticality","Soglia assente"),latest.get("freshness","Data assente"),latest.get("age_minutes"),latest.get("observed_at",""),station.get("sensor_id"))
            for col,item_value in enumerate(values): self.arpa_table.setItem(start_row+row,col,QTableWidgetItem("" if item_value is None else str(item_value)))
        totals = self._arpa_totals
        totals["stations"] += summary.get("stations", len(stations))
        totals["sensors"] += summary.get("sensors", len(stations))
        totals["measurements"] += summary.get("measurements", 0)
        totals["alerts"] += counts["Allarme"]
        totals["attention"] += counts["Attenzione"]
        totals["prealarm"] += counts["Preallarme"]
        totals["recent"] += freshness["Recente"]
        totals["delayed"] += freshness["Ritardato"]
        totals["expired"] += freshness["Scaduto"]
        totals["sources"].append(source)
        totals["points"] += self._add_arpa_layer(stations, source, self._arpa_active_province or "Tutta la regione")
        self.arpa_label.setText("%s caricato · restano %d reti" % (source, len(self._arpa_queue)))
        self.phase.setText(source+" caricato")
        self.last_refresh.setText("Aggiornato: "+__import__("datetime").datetime.now().strftime("%d/%m/%Y %H:%M:%S"))

    def _arpa_failed(self,message):
        source = getattr(self, "current_source", "Rete regionale")
        self._arpa_totals["errors"].append("%s: %s" % (source, message))
        self.phase.setText("Errore " + source)
        self.arpa_label.setText("%s non caricata · proseguo con le altre reti" % source)
        if not getattr(self, "_arpa_silent", False) and len(self.selected_areas()) == 1:
            QMessageBox.warning(self,"Monitoraggio Davide · rete regionale",message)

    def _arpa_cleanup(self):
        self.arpa_thread.deleteLater(); self.arpa_thread=None; self.arpa_worker=None; self.btn_arpa.setEnabled(True)
        if self._arpa_queue:
            self.btn_arpa.setEnabled(False)
            QTimer.singleShot(0, self._start_next_regional_worker)
        elif self._pending_regional_reload:
            QTimer.singleShot(0, self._run_pending_regional_reload)
        else:
            self._complete_regional_load()

    def _complete_regional_load(self):
        totals = self._arpa_totals
        self.card_sensors.setText("Sensori caricati\n%d" % totals["sensors"])
        self.card_measures.setText("Con ultimo dato\n%d" % totals["measurements"])
        self.card_alerts.setText("Allarmi\n%d" % totals["alerts"])
        message = "%d reti · %d stazioni · %d dati · %d punti · recenti:%d ritardati:%d scaduti:%d · A:%d P:%d ALL:%d" % (
            len(totals["sources"]), totals["stations"], totals["measurements"], totals["points"],
            totals["recent"], totals["delayed"], totals["expired"], totals["attention"],
            totals["prealarm"], totals["alerts"],
        )
        if totals["errors"]:
            message += " · errori:%d" % len(totals["errors"])
        self.arpa_label.setText(message)
        self.phase.setText("Reti regionali aggiornate")
        self.progress.setValue(100)
        self.btn_arpa.setEnabled(True)

    def _add_arpa_layer(self,stations,source,province):
        try:
            layer, feature_count = replace_sensor_layer(stations, province, source)
            self.live_layer = layer
            if feature_count:
                self.iface.setActiveLayer(layer)
                if len(self.selected_areas()) == 1:
                    self.iface.zoomToActiveLayer()
            return feature_count
        except Exception as exc:
            self.arpa_label.setText(self.arpa_label.text()+" · Layer non creato: "+str(exc))
            return 0

    def load_ingv(self, silent=False):
        if self.ingv_thread: return
        self.btn_ingv.setEnabled(False); self.ingv_label.setText("Scarico INGV...")
        self.ingv_thread=QThread(self); self.ingv_worker=IngvWorker(days=7); self.ingv_worker.moveToThread(self.ingv_thread); self.ingv_thread.started.connect(self.ingv_worker.run); self.ingv_worker.progress.connect(self._diag_progress); self.ingv_worker.finished.connect(self._ingv_finished); self.ingv_worker.failed.connect(self._ingv_failed); self.ingv_worker.finished.connect(self.ingv_thread.quit); self.ingv_worker.failed.connect(self.ingv_thread.quit); self.ingv_thread.finished.connect(self._ingv_cleanup); self.ingv_thread.start()

    def _ingv_finished(self, events):
        self.ingv_table.setRowCount(len(events))
        for row,event in enumerate(events):
            values=(event["time"],event["magnitude"],event["mag_type"],event["depth"],event["place"],event["event_id"])
            for col,value in enumerate(values): self.ingv_table.setItem(row,col,QTableWidgetItem("" if value is None else str(value)))
        _layer,count=replace_earthquake_layer(events); self.ingv_label.setText("%d eventi · %d punti in mappa"%(len(events),count)); self.phase.setText("INGV caricato")

    def _ingv_failed(self, message):
        self.ingv_label.setText(message); self.phase.setText("Errore INGV")

    def _ingv_cleanup(self): self.ingv_thread.deleteLater(); self.ingv_thread=None; self.ingv_worker=None; self.btn_ingv.setEnabled(True)

    def load_aineva(self):
        if self.aineva_thread: return
        self.btn_aineva.setEnabled(False); self.aineva_label.setText("Scarico bollettino AINEVA..."); self.aineva_table.setRowCount(0)
        self.aineva_thread=QThread(self); self.aineva_worker=AinevaWorker(); self.aineva_worker.moveToThread(self.aineva_thread); self.aineva_thread.started.connect(self.aineva_worker.run); self.aineva_worker.progress.connect(self._diag_progress); self.aineva_worker.finished.connect(self._aineva_finished); self.aineva_worker.failed.connect(self._aineva_failed); self.aineva_worker.finished.connect(self.aineva_thread.quit); self.aineva_worker.failed.connect(self.aineva_thread.quit); self.aineva_thread.finished.connect(self._aineva_cleanup); self.aineva_thread.start()

    def _aineva_finished(self, bulletin):
        level=bulletin.get("max_danger")
        if level is None:
            self.aineva_label.setText("Nessun bollettino giornaliero disponibile · possibile periodo fuori stagione")
        else:
            names={1:"Debole",2:"Moderato",3:"Marcato",4:"Forte",5:"Molto forte"}; self.aineva_table.setRowCount(1)
            values=(bulletin.get("published_at",""),bulletin.get("valid_from",""),bulletin.get("valid_to",""),"%s · %s"%(level,names.get(level,"")),", ".join(str(item) for item in bulletin.get("danger_levels",[])),", ".join(bulletin.get("problems",[])),", ".join(bulletin.get("regions",[])))
            for col,value in enumerate(values): self.aineva_table.setItem(0,col,QTableWidgetItem(str(value)))
            self.aineva_label.setText("Bollettino AINEVA caricato · pericolo massimo %s"%level)
        self.phase.setText("AINEVA completato"); self.progress.setValue(100)

    def _aineva_failed(self, message):
        self.aineva_label.setText(message); self.phase.setText("Errore AINEVA")

    def _aineva_cleanup(self): self.aineva_thread.deleteLater(); self.aineva_thread=None; self.aineva_worker=None; self.btn_aineva.setEnabled(True)

    def run_diagnostics(self):
        if self.diag_thread: return
        self.diag_rows=[]; self.diag_table.setRowCount(0); self.btn_diag.setEnabled(False); self.phase.setText("Diagnostica fonti"); self.progress.setValue(0)
        self.diag_thread=QThread(self); self.diag_worker=DiagnosticWorker(SOURCE_CATALOG); self.diag_worker.moveToThread(self.diag_thread); self.diag_thread.started.connect(self.diag_worker.run); self.diag_worker.progress.connect(self._diag_progress); self.diag_worker.row.connect(self._diag_row); self.diag_worker.finished.connect(self._diag_finished); self.diag_worker.finished.connect(self.diag_thread.quit); self.diag_thread.finished.connect(self._diag_cleanup); self.diag_thread.start()

    def _diag_progress(self,value,text): self.progress.setValue(value); self.phase.setText(text)
    def _diag_row(self,row):
        self.diag_rows.append(row); r=self.diag_table.rowCount(); self.diag_table.insertRow(r)
        values=(row["source"],row["group"],row["status"],row["http"],str(row["ms"]),row["detail"])
        color={"OK":"#dceee2","AVVISO":"#fff1b8","ERRORE":"#f7caca"}.get(row["status"],"#fff")
        for c,value in enumerate(values): item=QTableWidgetItem(value); item.setBackground(QBrush(QColor(color))); self.diag_table.setItem(r,c,item)
        if self.cache_path and os.path.isfile(self.cache_path):
            try: save_diagnostic(self.cache_path,row)
            except Exception as exc: self.phase.setText("Cache diagnostica: "+str(exc))
    def _diag_finished(self,summary):
        text="OK %d · Avvisi %d · Errori %d"%(summary["ok"],summary["warnings"],summary["errors"]); self.diag_summary.setText(text); self.source_status.setText("Fonti: "+text); self.phase.setText("Diagnostica completata"); self.progress.setValue(100)
    def _diag_cleanup(self): self.diag_thread.deleteLater(); self.diag_thread=None; self.diag_worker=None; self.btn_diag.setEnabled(True)
    def _refresh_threshold_table(self):
        if not hasattr(self,"threshold_table"): return
        self.threshold_table.setRowCount(len(self.thresholds))
        for row,item in enumerate(self.thresholds):
            values=(item["source"],item["sensor_id"],item["station_name"],item["sensor_type"],item["direction"],item["attention"],item["prealarm"],item["alarm"],item["reference"])
            for col,value in enumerate(values): self.threshold_table.setItem(row,col,QTableWidgetItem("" if value is None else str(value)))
        self.threshold_label.setText("%d configurazioni caricate · %s"%(len(self.thresholds),self.threshold_path or "nessun file"))
    def import_thresholds(self):
        path,_=QFileDialog.getOpenFileName(self,"Importa soglie documentate","","CSV (*.csv)")
        if not path: return
        try:
            rows=load_thresholds(path)
            undocumented=[row for row in rows if not row["reference"]]
            if undocumented: raise ValueError("Ogni riga deve indicare il riferimento ufficiale")
            self.thresholds=rows; self.threshold_path=path; self.settings.setValue("threshold_csv",path); self._refresh_threshold_table()
            QMessageBox.information(self,"Monitoraggio Davide","Importate %d configurazioni. Ricarica la rete regionale per applicarle."%len(rows))
        except Exception as exc: QMessageBox.warning(self,"Monitoraggio Davide · Soglie",str(exc))
    def save_threshold_template(self):
        path,_=QFileDialog.getSaveFileName(self,"Salva modello soglie","soglie_monitoraggio.csv","CSV (*.csv)")
        if path:
            try: write_template(path); QMessageBox.information(self,"Monitoraggio Davide","Modello CSV creato.")
            except Exception as exc: QMessageBox.warning(self,"Monitoraggio Davide · Soglie",str(exc))
    def clear_thresholds(self):
        self.thresholds=[]; self.threshold_path=""; self.settings.remove("threshold_csv"); self._refresh_threshold_table()
    def create_cache(self):
        path,_=QFileDialog.getSaveFileName(self,"Crea cache locale",os.path.join(os.path.expanduser("~"),"monitoraggio_utr_cache.sqlite"),"SQLite (*.sqlite)")
        if path:
            initialize_sqlite(path); upsert_sources(path,SOURCE_CATALOG); self.cache_path=path; self.cache_path_edit.setText(path); self.settings.setValue("cache_sqlite",path); QMessageBox.information(self,"Monitoraggio Davide","Cache locale inizializzata e catalogo fonti registrato.")

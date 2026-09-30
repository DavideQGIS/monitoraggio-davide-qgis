import os
import tempfile

from qgis.PyQt.QtCore import QSettings, Qt, QThread, QTimer, QUrl
from qgis.PyQt.QtGui import QColor, QBrush, QDesktopServices
from qgis.PyQt.QtWidgets import (
    QAbstractItemView, QButtonGroup, QCheckBox, QComboBox, QDialog,
    QFileDialog, QFormLayout, QFrame, QGridLayout, QGroupBox, QHBoxLayout,
    QHeaderView, QLabel, QLineEdit, QMessageBox, QProgressBar, QPushButton,
    QScrollArea, QSizePolicy, QSpinBox, QTabWidget, QTableWidget,
    QTableWidgetItem, QTextEdit, QVBoxLayout, QWidget
)

from .config import AREAS, DEFAULT_AREA, DEFAULT_PROVINCE, PLUGIN_VERSION, SENSOR_TYPES, SOURCE_CATALOG
from .database import POSTGIS_NOTE, initialize_sqlite
from .diagnostics import DiagnosticWorker
from .connectors.arpa_lombardia import ArpaLombardiaWorker
from .connectors.arpav import ArpavWorker
from .connectors.ingv import IngvWorker
from .connectors.meteotrentino import MeteotrentinoWorker
from .connectors.arpae_emilia_romagna import ArpaeEmiliaRomagnaWorker
from .map_manager import ensure_google_hybrid, replace_earthquake_layer, replace_sensor_layer
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
        self.ingv_thread = None
        self.ingv_worker = None
        self.live_layer = None
        self.thresholds = []
        self.threshold_path = self.settings.value("threshold_csv", "", type=str)
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

        geo = QHBoxLayout(); geo.addWidget(QLabel("AREA:"))
        self.area_group = QButtonGroup(self); self.area_group.setExclusive(True); self.area_buttons = {}
        for area in AREAS:
            button = QPushButton(area.upper()); button.setCheckable(True); self.area_group.addButton(button); self.area_buttons[area] = button
            button.clicked.connect(lambda checked=False, a=area: self.set_area(a)); geo.addWidget(button)
        geo.addSpacing(10); geo.addWidget(QLabel("Provincia:")); self.province = QComboBox(); self.province.currentTextChanged.connect(self._province_changed); geo.addWidget(self.province)
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
        self._placeholder("Neve", "Sensori nivometrici e nivopluviometrici, neve fresca, SWE e fusione.")
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
        note=QLabel("v%s · Reti regionali, ARPAE Emilia-Romagna, INGV e soglie documentate. I dati automatici recenti possono essere provvisori." % PLUGIN_VERSION); note.setWordWrap(True); layout.addWidget(note); layout.addStretch(1)
        self.tabs.addTab(page,"Quadro operativo")

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
        self.arpa_table=QTableWidget(0,10); self.arpa_table.setHorizontalHeaderLabels(["Stazione","Comune","Prov.","Sensore","Unita","Quota","Ultimo dato","Criticita","Data/ora","ID sensore"]); self.arpa_table.verticalHeader().setVisible(False); self.arpa_table.setEditTriggers(NO_EDIT_TRIGGERS); self.arpa_table.setAlternatingRowColors(True)
        self.arpa_table.horizontalHeader().setSectionResizeMode(0,HEADER_STRETCH)
        for col in range(1,10): self.arpa_table.horizontalHeader().setSectionResizeMode(col,HEADER_CONTENTS)
        layout.addWidget(self.arpa_table,1); self.tabs.addTab(page,"Meteo e radar")

    def _seismic(self):
        page=QWidget(); layout=QVBoxLayout(page)
        actions=QHBoxLayout(); self.btn_ingv=QPushButton("CARICA TERREMOTI INGV"); self.btn_ingv.setObjectName("primaryButton"); self.btn_ingv.clicked.connect(self.load_ingv); actions.addWidget(self.btn_ingv)
        self.ingv_label=QLabel("Eventi degli ultimi 7 giorni nell'Italia settentrionale"); actions.addWidget(self.ingv_label,1); layout.addLayout(actions)
        self.ingv_table=QTableWidget(0,6); self.ingv_table.setHorizontalHeaderLabels(["Data/ora","Magnitudo","Tipo","Profondita km","Localita","ID evento"]); self.ingv_table.verticalHeader().setVisible(False); self.ingv_table.setEditTriggers(NO_EDIT_TRIGGERS); self.ingv_table.setAlternatingRowColors(True)
        for col in (0,1,2,3,5): self.ingv_table.horizontalHeader().setSectionResizeMode(col,HEADER_CONTENTS)
        self.ingv_table.horizontalHeader().setSectionResizeMode(4,HEADER_STRETCH); layout.addWidget(self.ingv_table,1); self.tabs.addTab(page,"Sismica")

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
        cache=QPushButton("CREA CACHE SQLITE DI PROVA"); cache.clicked.connect(self.create_cache); form.addRow(cache); layout.addWidget(db)
        src=QGroupBox("Fonti predisposte"); sl=QVBoxLayout(src)
        for item in SOURCE_CATALOG: sl.addWidget(QLabel("• %s · %s"%(item["name"],item["group"])))
        layout.addWidget(src); layout.addStretch(1); self.tabs.addTab(page,"Impostazioni")

    def set_area(self, area, province=None):
        self.area_buttons[area].setChecked(True); self.province.blockSignals(True); self.province.clear(); self.province.addItem("Tutta la regione" if area != "Trentino" else "Tutta la provincia"); self.province.addItems(AREAS[area]); target=province or DEFAULT_PROVINCE[area]; index=self.province.findText(target); self.province.setCurrentIndex(max(0,index)); self.province.blockSignals(False); self.current_area=area; self._update_geo_status()

    def _province_changed(self, _text): self._update_geo_status()
    def _update_geo_status(self): self.status.setText("%s · %s"%(getattr(self,"current_area",DEFAULT_AREA),self.province.currentText() or DEFAULT_PROVINCE[DEFAULT_AREA]))
    def _tick(self): self.live.setText("v%s · LIVE %s" % (PLUGIN_VERSION, __import__("datetime").datetime.now().strftime("%H:%M:%S")))

    def open_live_view(self):
        try:
            ensure_google_hybrid()
            self._toggle_refresh()
            if self.current_area in ("Lombardia", "Veneto", "Trentino", "Emilia-Romagna") and self.arpa_thread is None:
                self.load_arpa()
            if self.ingv_thread is None:
                self.load_ingv(silent=True)
        except Exception as exc:
            self.phase.setText("Errore basemap")
            QMessageBox.warning(self, "Monitoraggio Davide · Mappa", str(exc))

    def _toggle_refresh(self, *_args):
        if self.auto_refresh.isChecked():
            self.refresh_timer.start(self.refresh_minutes.value() * 60 * 1000)
        else:
            self.refresh_timer.stop()

    def _auto_refresh(self):
        if self.current_area in ("Lombardia", "Veneto", "Trentino", "Emilia-Romagna") and self.arpa_thread is None:
            self.load_arpa(silent=True)
        if self.ingv_thread is None:
            self.load_ingv(silent=True)

    def load_arpa(self, silent=False):
        if self.arpa_thread: return
        area = getattr(self,"current_area",DEFAULT_AREA)
        province=self.province.currentText()
        if not province or province.startswith("Tutta"):
            province="Brescia"
        source = {"Lombardia": "ARPA Lombardia", "Veneto": "ARPAV", "Trentino": "Meteotrentino", "Emilia-Romagna": "ARPAE Emilia-Romagna"}[area]
        self.current_source = source
        self.arpa_table.setRowCount(0); self.btn_arpa.setEnabled(False); self.phase.setText("Avvio " + source); self.progress.setValue(0)
        if area == "Lombardia": worker = ArpaLombardiaWorker(province=province)
        elif area == "Veneto": worker = ArpavWorker(province=province)
        elif area == "Trentino": worker = MeteotrentinoWorker()
        else: worker = ArpaeEmiliaRomagnaWorker()
        self.arpa_thread=QThread(self); self.arpa_worker=worker; self.arpa_worker.moveToThread(self.arpa_thread); self.arpa_thread.started.connect(self.arpa_worker.run); self.arpa_worker.progress.connect(self._diag_progress); self.arpa_worker.finished.connect(self._arpa_finished); self.arpa_worker.failed.connect(self._arpa_failed); self.arpa_worker.finished.connect(self.arpa_thread.quit); self.arpa_worker.failed.connect(self.arpa_thread.quit); self.arpa_thread.finished.connect(self._arpa_cleanup); self.arpa_thread.start()

    def _arpa_finished(self,stations,summary):
        counts=apply_thresholds(stations,self.thresholds,getattr(self,"current_source",""))
        self.arpa_table.setRowCount(len(stations))
        for row,station in enumerate(stations):
            latest=station.get("latest") or {}; value=latest.get("value"); values=(station.get("name"),station.get("municipality"),station.get("province"),station.get("sensor_type"),station.get("unit"),station.get("elevation"),"" if value is None else str(value),station.get("criticality","Soglia assente"),latest.get("observed_at",""),station.get("sensor_id"))
            for col,item_value in enumerate(values): self.arpa_table.setItem(row,col,QTableWidgetItem("" if item_value is None else str(item_value)))
        source=getattr(self,"current_source","Rete regionale"); self.card_sensors.setText("Sensori caricati\n%d"%summary["sensors"]); self.card_measures.setText("Con ultimo dato\n%d"%summary["measurements"]); self.card_alerts.setText("Allarmi\n%d"%counts["Allarme"]); self.arpa_label.setText("%s · %d righe · %d ultimi dati · A:%d P:%d ALL:%d"%(source,summary["stations"],summary["measurements"],counts["Attenzione"],counts["Preallarme"],counts["Allarme"])); self.phase.setText(source+" caricato"); self.progress.setValue(100)
        self._add_arpa_layer(stations)
        self.last_refresh.setText("Aggiornato: "+__import__("datetime").datetime.now().strftime("%d/%m/%Y %H:%M:%S"))

    def _arpa_failed(self,message):
        self.phase.setText("Errore rete regionale"); self.arpa_label.setText(message); QMessageBox.warning(self,"Monitoraggio Davide · rete regionale",message)

    def _arpa_cleanup(self): self.arpa_thread.deleteLater(); self.arpa_thread=None; self.arpa_worker=None; self.btn_arpa.setEnabled(True)

    def _add_arpa_layer(self,stations):
        try:
            layer, feature_count = replace_sensor_layer(stations, self.province.currentText(), getattr(self,"current_source","Rete regionale"))
            self.live_layer = layer
            if feature_count:
                self.iface.setActiveLayer(layer)
                self.iface.zoomToActiveLayer()
            self.arpa_label.setText(self.arpa_label.text()+" · %d punti in mappa"%feature_count)
        except Exception as exc:
            self.arpa_label.setText(self.arpa_label.text()+" · Layer non creato: "+str(exc))

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
            initialize_sqlite(path); QMessageBox.information(self,"Monitoraggio Davide","Cache locale inizializzata.")

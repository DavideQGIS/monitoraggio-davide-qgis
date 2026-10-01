from qgis.PyQt.QtGui import QColor, QFont
from qgis.core import (
    QgsCategorizedSymbolRenderer, QgsFeature, QgsField, QgsGeometry,
    QgsMarkerSymbol, QgsPalLayerSettings, QgsPointXY, QgsProject, QgsRasterLayer,
    QgsRendererCategory, QgsTextBufferSettings, QgsTextFormat, QgsVectorLayer,
    QgsVectorLayerSimpleLabeling,
)
from .qt_compat import FIELD_DOUBLE, FIELD_INT, FIELD_STRING


GROUP_NAME = "Monitoraggio Davide"
BASEMAP_NAME = "Google Hybrid · Monitoraggio Davide"
SENSORS_PREFIX = "Sensori monitoraggio"
RIP_LAYER_NAME = "Reticolo Idrico Principale Lombardia · DGR XII/3668"
RIP_WMS_URL = "https://www.cartografia.servizirl.it/arcgis1/services/territorio/ReticoloIdrografico_RIRU/MapServer/WMSServer"
RADAR_LAYER_PREFIX = "Radar ARPA Lombardia"


def ensure_group():
    root = QgsProject.instance().layerTreeRoot()
    group = root.findGroup(GROUP_NAME)
    if group is None:
        group = root.insertGroup(0, GROUP_NAME)
    return group


def ensure_google_hybrid():
    project = QgsProject.instance()
    for layer in project.mapLayers().values():
        if layer.name() == BASEMAP_NAME:
            return layer
    uri = (
        "type=xyz&url=https://mt1.google.com/vt/"
        "lyrs%3Dy%26x%3D%7Bx%7D%26y%3D%7By%7D%26z%3D%7Bz%7D"
        "&zmax=20&zmin=0"
    )
    layer = QgsRasterLayer(uri, BASEMAP_NAME, "wms")
    if not layer.isValid():
        raise RuntimeError("QGIS non riesce a inizializzare il collegamento XYZ Google Hybrid.")
    layer.setCustomProperty("monitoraggio_utr", True)
    project.addMapLayer(layer, False)
    ensure_group().addLayer(layer)
    return layer


def set_lombardia_rip(enabled=True):
    """Aggiunge o rimuove il RIP ufficiale Lombardia (layer 7 del RIRU)."""
    project = QgsProject.instance()
    existing = [layer for layer in project.mapLayers().values() if layer.name() == RIP_LAYER_NAME]
    if not enabled:
        for layer in existing:
            project.removeMapLayer(layer.id())
        return None
    if existing:
        return existing[0]

    uri = "url=%s&layers=7&styles=&format=image/png&crs=EPSG:3857&featureCount=10" % RIP_WMS_URL
    layer = QgsRasterLayer(uri, RIP_LAYER_NAME, "wms")
    if not layer.isValid():
        raise RuntimeError("QGIS non riesce a inizializzare il WMS del Reticolo Idrico Principale Lombardia.")
    layer.setCustomProperty("monitoraggio_utr", True)
    layer.setCustomProperty("monitoraggio_utr/source", "RIRU Lombardia")
    layer.setCustomProperty("monitoraggio_utr/type", "reticolo_idrico_principale")
    project.addMapLayer(layer, False)
    ensure_group().insertLayer(0, layer)
    return layer


def replace_radar_layer(product):
    """Sostituisce il composito radar ARPA mantenendo un solo raster in progetto."""
    project = QgsProject.instance()
    for layer_id, old_layer in list(project.mapLayers().items()):
        if old_layer.name().startswith(RADAR_LAYER_PREFIX):
            project.removeMapLayer(layer_id)
    name = "%s · %s" % (RADAR_LAYER_PREFIX, product.get("observed_at_utc", ""))
    layer = QgsRasterLayer(product["path"], name)
    if not layer.isValid():
        raise RuntimeError("QGIS non riconosce il GeoTIFF radar scaricato da ARPA Lombardia.")
    renderer = layer.renderer()
    if renderer is not None and hasattr(renderer, "setOpacity"):
        renderer.setOpacity(0.68)
    elif hasattr(layer, "setOpacity"):
        layer.setOpacity(0.68)
    layer.setCustomProperty("monitoraggio_utr", True)
    layer.setCustomProperty("monitoraggio_utr/source", "ARPA Lombardia radar")
    layer.setCustomProperty("monitoraggio_utr/observed_at", product.get("observed_at", ""))
    project.addMapLayer(layer, False)
    ensure_group().insertLayer(0, layer)
    return layer


def _sensor_family(text):
    value = (text or "").lower()
    if "neve" in value or "nivo" in value:
        return "Neve"
    if "idro" in value or "livello" in value or "portata" in value:
        return "Idrologia"
    if "piogg" in value or "precipit" in value:
        return "Pioggia"
    if "temper" in value:
        return "Temperatura"
    if "vento" in value or "anemo" in value:
        return "Vento"
    if "umid" in value:
        return "Umidita"
    return "Altro"


def _apply_style(layer):
    colors = {
        "Regolare": "#22c55e", "Attenzione": "#facc15",
        "Preallarme": "#f97316", "Allarme": "#dc2626",
        "Soglia assente": "#64748b", "Dato assente": "#94a3b8",
    }
    categories = []
    for family, color in colors.items():
        symbol = QgsMarkerSymbol.createSimple({
            "name": "circle", "color": color, "outline_color": "#ffffff",
            "outline_width": "0.7", "size": "4.2",
        })
        categories.append(QgsRendererCategory(family, symbol, family))
    layer.setRenderer(QgsCategorizedSymbolRenderer("criticita", categories))


def replace_sensor_layer(stations, province, source="ARPA Lombardia"):
    project = QgsProject.instance()
    for layer_id, layer in list(project.mapLayers().items()):
        if layer.name().startswith("Sensori " + source):
            project.removeMapLayer(layer_id)
    layer = QgsVectorLayer("Point?crs=EPSG:4326", "Sensori %s · %s" % (source, province), "memory")
    provider = layer.dataProvider()
    provider.addAttributes([
        QgsField("stazione", FIELD_STRING), QgsField("comune", FIELD_STRING),
        QgsField("provincia", FIELD_STRING), QgsField("sensore", FIELD_STRING),
        QgsField("famiglia", FIELD_STRING), QgsField("unita", FIELD_STRING),
        QgsField("valore", FIELD_DOUBLE), QgsField("data_ora", FIELD_STRING),
        QgsField("stato", FIELD_STRING), QgsField("id_sensore", FIELD_STRING),
        QgsField("quota_m", FIELD_DOUBLE), QgsField("criticita", FIELD_STRING),
        QgsField("soglia_att", FIELD_DOUBLE), QgsField("soglia_pre", FIELD_DOUBLE),
        QgsField("soglia_all", FIELD_DOUBLE), QgsField("fonte_soglia", FIELD_STRING),
        QgsField("freschezza", FIELD_STRING), QgsField("eta_min", FIELD_INT),
        QgsField("etichetta", FIELD_STRING),
    ])
    layer.updateFields()
    features = []
    for station in stations:
        lon, lat = station.get("longitude"), station.get("latitude")
        if lon is None or lat is None:
            continue
        latest = station.get("latest") or {}
        value = latest.get("value")
        value_text = "n.d." if value is None else ("%.3f" % value).rstrip("0").rstrip(".")
        criticality = station.get("criticality", "Soglia assente")
        threshold = station.get("threshold") or {}
        freshness = latest.get("freshness", "Data assente")
        label = "%s · %s: %s %s · %s · %s" % (
            station.get("name", ""), station.get("sensor_type", ""),
            value_text, station.get("unit", ""), criticality, freshness,
        )
        feature = QgsFeature(layer.fields())
        feature.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(lon, lat)))
        feature.setAttributes([
            station.get("name", ""), station.get("municipality", ""),
            station.get("province", ""), station.get("sensor_type", ""),
            _sensor_family(station.get("sensor_type", "")), station.get("unit", ""),
            latest.get("value"), latest.get("observed_at", ""), latest.get("state", ""),
            station.get("sensor_id", ""), station.get("elevation"), criticality,
            threshold.get("attention"), threshold.get("prealarm"), threshold.get("alarm"),
            threshold.get("reference", ""), freshness, latest.get("age_minutes"), label,
        ])
        features.append(feature)
    provider.addFeatures(features)
    layer.updateExtents()
    layer.setCustomProperty("monitoraggio_utr", True)
    layer.setCustomProperty("monitoraggio_utr/source", source)
    _apply_style(layer)
    label_settings = QgsPalLayerSettings()
    label_settings.fieldName = "etichetta"
    text_format = QgsTextFormat()
    text_format.setFont(QFont("Arial", 8))
    text_format.setSize(8)
    text_format.setColor(QColor("#111827"))
    buffer_settings = QgsTextBufferSettings()
    buffer_settings.setEnabled(True)
    buffer_settings.setSize(1.0)
    buffer_settings.setColor(QColor("#ffffff"))
    text_format.setBuffer(buffer_settings)
    label_settings.setFormat(text_format)
    layer.setLabeling(QgsVectorLayerSimpleLabeling(label_settings))
    layer.setLabelsEnabled(True)
    project.addMapLayer(layer, False)
    group = ensure_group()
    group.insertLayer(0, layer)
    return layer, len(features)


def replace_earthquake_layer(events):
    project = QgsProject.instance()
    name = "Terremoti INGV · ultimi 7 giorni"
    for layer_id, old_layer in list(project.mapLayers().items()):
        if old_layer.name().startswith("Terremoti INGV"):
            project.removeMapLayer(layer_id)
    layer = QgsVectorLayer("Point?crs=EPSG:4326", name, "memory")
    provider = layer.dataProvider()
    provider.addAttributes([
        QgsField("evento", FIELD_STRING), QgsField("data_ora", FIELD_STRING),
        QgsField("magnitudo", FIELD_DOUBLE), QgsField("tipo_mag", FIELD_STRING),
        QgsField("prof_km", FIELD_DOUBLE), QgsField("localita", FIELD_STRING),
    ])
    layer.updateFields()
    features = []
    for event in events:
        feature = QgsFeature(layer.fields())
        feature.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(event["longitude"], event["latitude"])))
        feature.setAttributes([event["event_id"], event["time"], event["magnitude"], event["mag_type"], event["depth"], event["place"]])
        features.append(feature)
    provider.addFeatures(features)
    layer.updateExtents()
    symbol = QgsMarkerSymbol.createSimple({"name": "circle", "color": "#ef4444", "outline_color": "#7f1d1d", "size": "4.5"})
    layer.renderer().setSymbol(symbol)
    layer.setCustomProperty("monitoraggio_utr", True)
    layer.setCustomProperty("monitoraggio_utr/source", "INGV")
    project.addMapLayer(layer, False)
    ensure_group().insertLayer(0, layer)
    return layer, len(features)

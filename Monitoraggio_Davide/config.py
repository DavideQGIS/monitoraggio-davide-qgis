from .core.source_registry import source_catalog


PLUGIN_VERSION = "0.7.0-alpha4"


AREAS = {
    "Lombardia": ["Bergamo", "Brescia", "Como", "Cremona", "Lecco", "Lodi", "Mantova", "Milano", "Monza e Brianza", "Pavia", "Sondrio", "Varese"],
    "Veneto": ["Belluno", "Padova", "Rovigo", "Treviso", "Venezia", "Verona", "Vicenza"],
    "Trentino": ["Trento"],
    "Emilia-Romagna": ["Bologna", "Ferrara", "Forli-Cesena", "Modena", "Parma", "Piacenza", "Ravenna", "Reggio Emilia", "Rimini"],
}

DEFAULT_AREA = "Lombardia"
DEFAULT_PROVINCE = {"Lombardia": "Brescia", "Veneto": "Padova", "Trentino": "Trento", "Emilia-Romagna": "Tutta la regione"}

SENSOR_TYPES = [
    ("Pluviometrico", "mm"),
    ("Idrometrico", "m / cm"),
    ("Nivometrico", "cm"),
    ("Nivopluviometrico", "cm / mm"),
    ("Temperatura", "°C"),
    ("Vento", "m/s"),
    ("Umidita", "%"),
    ("Portata", "m³/s"),
    ("Diga / invaso", "m / m³"),
    ("Piezometro", "m"),
    ("Inclinometro", "mm"),
    ("Estensimetro", "mm"),
    ("GNSS frana", "mm"),
    ("Sismico", "ML / Mw"),
    ("Radar meteorologico", "dBZ / mm/h"),
    ("Copernicus flood", "area"),
    ("Copernicus fire", "area"),
]

SOURCE_CATALOG = source_catalog()

from .core.source_registry import source_catalog


PLUGIN_VERSION = "0.7.0-alpha9"


AREAS = {
    "Lombardia": ["Bergamo", "Brescia", "Como", "Cremona", "Lecco", "Lodi", "Mantova", "Milano", "Monza e Brianza", "Pavia", "Sondrio", "Varese"],
    "Veneto": ["Belluno", "Padova", "Rovigo", "Treviso", "Venezia", "Verona", "Vicenza"],
    "Trentino": ["Trento"],
    "Emilia-Romagna": ["Bologna", "Ferrara", "Forli-Cesena", "Modena", "Parma", "Piacenza", "Ravenna", "Reggio Emilia", "Rimini"],
}

DEFAULT_AREA = "Lombardia"
DEFAULT_PROVINCE = {"Lombardia": "Brescia", "Veneto": "Padova", "Trentino": "Trento", "Emilia-Romagna": "Tutta la regione"}

# Coordinate WGS84 dei capoluoghi provinciali/metropolitani visualizzati in mappa.
# Il campo province segue esattamente i nomi esposti dal selettore AREAS.
CAPITALS = [
    {"area": "Lombardia", "province": "Bergamo", "name": "Bergamo", "longitude": 9.6773, "latitude": 45.6983},
    {"area": "Lombardia", "province": "Brescia", "name": "Brescia", "longitude": 10.2118, "latitude": 45.5416},
    {"area": "Lombardia", "province": "Como", "name": "Como", "longitude": 9.0852, "latitude": 45.8081},
    {"area": "Lombardia", "province": "Cremona", "name": "Cremona", "longitude": 10.0227, "latitude": 45.1332},
    {"area": "Lombardia", "province": "Lecco", "name": "Lecco", "longitude": 9.3901, "latitude": 45.8566},
    {"area": "Lombardia", "province": "Lodi", "name": "Lodi", "longitude": 9.5037, "latitude": 45.3144},
    {"area": "Lombardia", "province": "Mantova", "name": "Mantova", "longitude": 10.7914, "latitude": 45.1564},
    {"area": "Lombardia", "province": "Milano", "name": "Milano", "longitude": 9.1900, "latitude": 45.4642},
    {"area": "Lombardia", "province": "Monza e Brianza", "name": "Monza", "longitude": 9.2744, "latitude": 45.5845},
    {"area": "Lombardia", "province": "Pavia", "name": "Pavia", "longitude": 9.1582, "latitude": 45.1847},
    {"area": "Lombardia", "province": "Sondrio", "name": "Sondrio", "longitude": 9.8715, "latitude": 46.1699},
    {"area": "Lombardia", "province": "Varese", "name": "Varese", "longitude": 8.8251, "latitude": 45.8206},
    {"area": "Veneto", "province": "Belluno", "name": "Belluno", "longitude": 12.2179, "latitude": 46.1425},
    {"area": "Veneto", "province": "Padova", "name": "Padova", "longitude": 11.8768, "latitude": 45.4064},
    {"area": "Veneto", "province": "Rovigo", "name": "Rovigo", "longitude": 11.7900, "latitude": 45.0703},
    {"area": "Veneto", "province": "Treviso", "name": "Treviso", "longitude": 12.2430, "latitude": 45.6669},
    {"area": "Veneto", "province": "Venezia", "name": "Venezia", "longitude": 12.3155, "latitude": 45.4408},
    {"area": "Veneto", "province": "Verona", "name": "Verona", "longitude": 10.9916, "latitude": 45.4384},
    {"area": "Veneto", "province": "Vicenza", "name": "Vicenza", "longitude": 11.5354, "latitude": 45.5455},
    {"area": "Trentino", "province": "Trento", "name": "Trento", "longitude": 11.1211, "latitude": 46.0748},
    {"area": "Emilia-Romagna", "province": "Bologna", "name": "Bologna", "longitude": 11.3426, "latitude": 44.4949},
    {"area": "Emilia-Romagna", "province": "Ferrara", "name": "Ferrara", "longitude": 11.6198, "latitude": 44.8381},
    {"area": "Emilia-Romagna", "province": "Forli-Cesena", "name": "Forlì", "longitude": 12.0407, "latitude": 44.2227},
    {"area": "Emilia-Romagna", "province": "Modena", "name": "Modena", "longitude": 10.9252, "latitude": 44.6471},
    {"area": "Emilia-Romagna", "province": "Parma", "name": "Parma", "longitude": 10.3279, "latitude": 44.8015},
    {"area": "Emilia-Romagna", "province": "Piacenza", "name": "Piacenza", "longitude": 9.6930, "latitude": 45.0526},
    {"area": "Emilia-Romagna", "province": "Ravenna", "name": "Ravenna", "longitude": 12.2035, "latitude": 44.4184},
    {"area": "Emilia-Romagna", "province": "Reggio Emilia", "name": "Reggio Emilia", "longitude": 10.6301, "latitude": 44.6989},
    {"area": "Emilia-Romagna", "province": "Rimini", "name": "Rimini", "longitude": 12.5683, "latitude": 44.0678},
]

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

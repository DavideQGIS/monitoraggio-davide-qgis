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

SOURCE_CATALOG = [
    {"name": "ARPA Lombardia - stazioni", "group": "Meteo/Idro/Neve", "area": "Lombardia", "url": "https://www.dati.lombardia.it/resource/nf78-nj6b.json?$limit=1"},
    {"name": "ARPA Lombardia - radar", "group": "Radar", "area": "Lombardia", "url": "https://radarlive.arpalombardia.it/CMP"},
    {"name": "ARPAV - rete idrometeorologica", "group": "Meteo/Idro/Neve", "area": "Veneto", "url": "https://www.arpa.veneto.it/api/risorse/data-meteo/xml/Ultime48ore.xml"},
    {"name": "Meteotrentino - stazioni", "group": "Meteo/Idro/Neve", "area": "Trentino", "url": "https://dati.meteotrentino.it/service.asmx/listaStazioniGeoJson"},
    {"name": "ARPAE Emilia-Romagna - idrometri e soglie", "group": "Idrometria", "area": "Emilia-Romagna", "url": "https://allertameteo.regione.emilia-romagna.it/o/api/allerta/get-sensor-values-no-time?variabile=254,0,0/1,-,-,-/B13215"},
    {"name": "Radar Protezione Civile", "group": "Radar", "area": "Tutte", "url": "https://mappe.protezionecivile.gov.it/it/mappe-e-dashboard-rischi/piattaforma-radar/"},
    {"name": "INGV terremoti", "group": "Sismica", "area": "Tutte", "url": "https://webservices.ingv.it/fdsnws/event/1/query?starttime=2026-09-19&format=geojson&minlatitude=44&maxlatitude=47.7&minlongitude=8&maxlongitude=14.2"},
    {"name": "Copernicus EMS Mapping", "group": "Copernicus", "area": "Tutte", "url": "https://mapping.emergency.copernicus.eu/activations/"},
    {"name": "Copernicus GFM/EFAS", "group": "Alluvioni", "area": "Tutte", "url": "https://global-flood.emergency.copernicus.eu/"},
    {"name": "Copernicus EFFIS", "group": "Incendi", "area": "Tutte", "url": "https://effis.jrc.ec.europa.eu/"},
]

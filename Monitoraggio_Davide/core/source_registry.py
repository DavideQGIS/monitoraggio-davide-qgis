from typing import Dict, Iterable, List

from .models import SourceDefinition


SOURCES = (
    SourceDefinition("arpa_lombardia_stazioni", "ARPA Lombardia - stazioni", "Meteo/Idro/Neve", "Lombardia", "https://www.dati.lombardia.it/resource/nf78-nj6b.json?$limit=1"),
    SourceDefinition("lombardia_rip_wms", "Regione Lombardia - Reticolo Idrico Principale", "Reticolo idrico", "Lombardia", "https://www.cartografia.servizirl.it/arcgis1/services/territorio/ReticoloIdrografico_RIRU/MapServer/WMSServer?SERVICE=WMS&REQUEST=GetCapabilities", True, "RIRU layer 7; Allegato A D.G.R. XII/3668/2024."),
    SourceDefinition("arpa_lombardia_radar", "ARPA Lombardia - radar", "Radar", "Lombardia", "https://radarlive.arpalombardia.it/CMP/", True, "Composito pubblico GeoTIFF delle ultime 24 ore, aggiornamento nominale ogni 5 minuti."),
    SourceDefinition("lombardia_cfmr", "Regione Lombardia - CFMR", "Sala operativa", "Lombardia", "https://www.regione.lombardia.it/sicurezza-e-protezione-civile/pianificazione-allertamento-e-gestione-emergenze/monitoraggio-e-allertamento/red-monitoraggio-rischi-naturali", False, "Pagina istituzionale del sistema di monitoraggio."),
    SourceDefinition("lombardia_allertalom", "Regione Lombardia - allertaLOM e BMP", "Allerte/Bollettini", "Lombardia", "https://www.allertalom.regione.lombardia.it/", False, "Consultazione pubblica; feed automatico da validare."),
    SourceDefinition("arpa_lombardia_liris", "ARPA Lombardia - LIRIS", "Idro/Nivo/Meteo", "Lombardia", "https://iris.arpalombardia.it/gisINM/login.php", False, "Accesso pubblico guest mediante sessione web."),
    SourceDefinition("lombardia_pvr", "Regione Lombardia - PVR SINERGIE 2.0", "Sala operativa", "Lombardia", "https://www.protezionecivile.servizirl.it/servizi/servizi/dettaglio?id=49", False, "Accesso istituzionale autorizzato."),
    SourceDefinition("arpav_idrometeo", "ARPAV - rete idrometeorologica", "Meteo/Idro/Neve", "Veneto", "https://www.arpa.veneto.it/api/risorse/data-meteo/xml/Ultime48ore.xml"),
    SourceDefinition("meteotrentino_stazioni", "Meteotrentino - stazioni", "Meteo/Idro/Neve", "Trentino", "https://dati.meteotrentino.it/service.asmx/listaStazioniGeoJson"),
    SourceDefinition("aineva_caaml", "AINEVA - bollettino neve e valanghe", "Neve/Valanghe", "Tutte", "https://bollettini.aineva.it/albina_files/latest/it.xml", True, "Open data CAAML; emissione stagionale."),
    SourceDefinition("meteotrentino_campi_neve", "Meteotrentino - campi neve", "Neve/Valanghe", "Trentino", "https://dati.meteotrentino.it/service.asmx/listaCampiNeveJson", True),
    SourceDefinition("arpa_lombardia_sidro_dighe", "ARPA Lombardia SIDRO - grandi dighe", "Dighe/Invasi", "Lombardia", "https://idro.arpalombardia.it/it/map/sidro/", False, "Anagrafica geografica; livelli operativi da feed autorizzati dei gestori/CFD."),
    SourceDefinition("arpa_lombardia_frane", "ARPA Lombardia CRMFD - frane monitorate", "Frane", "Lombardia", "https://www.arpalombardia.it/temi-ambientali/frane-e-dissesti/reti-di-controllo/aree-monitorate/", False, "Dati strumentali di dettaglio non tutti pubblici."),
    SourceDefinition("lombardia_e015_allerte", "Regione Lombardia E015 - allerte", "Allerte", "Lombardia", "https://www.e015.regione.lombardia.it/site/news-detail?id=62", False, "API istituzionale con adesione E015."),
    SourceDefinition("arpae_idrometri", "ARPAE Emilia-Romagna - idrometri e soglie", "Idrometria", "Emilia-Romagna", "https://allertameteo.regione.emilia-romagna.it/o/api/allerta/get-sensor-values-no-time?variabile=254,0,0/1,-,-,-/B13215"),
    SourceDefinition("dpc_radar", "Radar Protezione Civile", "Radar", "Tutte", "https://mappe.protezionecivile.gov.it/it/mappe-e-dashboard-rischi/piattaforma-radar/", False),
    SourceDefinition("ingv_terremoti", "INGV terremoti", "Sismica", "Tutte", "https://webservices.ingv.it/fdsnws/event/1/query", True),
    SourceDefinition("copernicus_ems", "Copernicus EMS Mapping", "Copernicus", "Tutte", "https://mapping.emergency.copernicus.eu/activations/", False),
    SourceDefinition("copernicus_gfm", "Copernicus GFM/EFAS", "Alluvioni", "Tutte", "https://global-flood.emergency.copernicus.eu/", False),
    SourceDefinition("copernicus_effis", "Copernicus EFFIS", "Incendi", "Tutte", "https://effis.jrc.ec.europa.eu/", False),
)


def source_catalog(sources: Iterable[SourceDefinition] = SOURCES) -> List[Dict[str, object]]:
    return [source.as_catalog_row() for source in sources]


def source_by_key(key: str) -> SourceDefinition:
    try:
        return next(source for source in SOURCES if source.key == key)
    except StopIteration as exc:
        raise KeyError("Fonte non registrata: %s" % key) from exc

# Roadmap

## 0.7.x — Fondazioni affidabili

- [x] Registro unico delle fonti con chiavi stabili.
- [x] Contratto comune per i connettori.
- [x] Parser ARPAV separato e testabile.
- [x] Parser ARPAE e INGV separati e testabili senza QGIS.
- [x] Selezione dell'ultima misura ARPAV numerica, ignorando gli intervalli ancora vuoti.
- [x] Gestione rete tramite strumenti QGIS, con proxy, SSL e annullamento.
  - [x] ARPAV trasferito su `QgsBlockingNetworkRequest` thread-safe.
  - [x] ARPA Lombardia, INGV e ARPAE Emilia-Romagna trasferiti sulla rete QGIS.
  - [x] Diagnostica trasferita sulla rete QGIS.
  - [x] Meteotrentino trasferito sulla rete QGIS.
- [ ] Aggiornamento incrementale dei layer senza ricrearli.
- [x] Stato di freschezza del dato e persistenza della diagnostica in SQLite.
- [ ] Indicatore di qualità specifico per ogni rete.
- [ ] Migrazioni SQLite/PostGIS versionate.

## 0.8.x — Radar e serie temporali

- [x] Fonte AINEVA CAAML e scheda neve/valanghe operative.
- [ ] Poligoni GIS delle micro-aree AINEVA tematizzati per grado di pericolo.
- [ ] Campi neve Meteotrentino e dettaglio nivometri regionali.
- [ ] Anagrafica grandi dighe SIDRO e livelli/scarichi tramite feed autorizzati.
- [ ] Aree e reti strumentali CRMFD, distinguendo dati pubblici e riservati.
- layer radar con timestamp, legenda e cache;
- sequenza temporale degli ultimi fotogrammi;
- grafici di pioggia, livello, neve e portata;
- stato `dato recente`, `dato ritardato`, `dato scaduto`;
- soglie e allarmi documentati.

## 0.9.x — Copernicus

- catalogo CEMS Rapid Mapping;
- prodotti flood GFM/EFAS;
- prodotti incendi EFFIS;
- integrazione opzionale con Copernicus Connect/STAC.

## 1.0 — Sala operativa

- PostGIS operativo;
- mezzi autorizzati tramite Traccar;
- eventi e segnalazioni territoriali;
- infrastrutture elettriche e telecomunicazioni;
- ruoli, tracciamento delle modifiche e stato di validazione.

Lo stato in tempo reale di mezzi di soccorso, linee elettriche guaste e celle telefoniche fuori servizio richiede feed autorizzati o una rete propria di dispositivi. La cartografia infrastrutturale pubblica non equivale alla conferma di un guasto.

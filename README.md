# Monitoraggio Davide

Plugin QGIS in Python per il monitoraggio territoriale di sensori ambientali ed eventi, con area predefinita **Lombardia · Brescia** e focus operativo anche su **Veneto · Padova**, Trentino ed Emilia-Romagna.

## Stato del progetto

La versione `0.6.0` costituisce la baseline iniziale del repository. Include:

- stazioni ARPA Lombardia;
- rete ARPAV Veneto;
- stazioni Meteotrentino;
- idrometri e soglie ARPAE Emilia-Romagna;
- terremoti INGV;
- importazione di soglie documentate da CSV;
- rappresentazione georeferenziata dei sensori e delle criticità;
- Google Hybrid come mappa di base;
- diagnostica di raggiungibilità delle fonti;
- compatibilità degli enum Qt tra QGIS 3/PyQt5 e QGIS 4/PyQt6.

Le schede radar, Copernicus, dighe, neve e frane sono ancora parziali o predisposte. La configurazione PostGIS non è ancora operativa.

## Compatibilità prevista

- QGIS 3.22 o successivo;
- QGIS 4.x, da verificare progressivamente durante lo sviluppo;
- Windows e Linux.

## Installazione manuale

1. Scaricare lo ZIP della release.
2. In QGIS aprire **Plugin > Gestisci e installa plugin > Installa da ZIP**.
3. Selezionare lo ZIP senza estrarlo.
4. Attivare **Monitoraggio Davide**.

## Sviluppo

Il codice applicativo si trova in `Monitoraggio_Davide/`. La pianificazione tecnica è descritta in [ROADMAP.md](ROADMAP.md). La serie `0.7.x` separa progressivamente connettori, servizi, database, gestione dei layer e interfaccia.

I dati provenienti da servizi esterni restano soggetti a disponibilità, licenze, condizioni d'uso e formati stabiliti dagli enti titolari. Il plugin deve mostrare sempre fonte, orario del dato e stato di aggiornamento.

## Test locali

```bash
python -m compileall -q Monitoraggio_Davide
python -m unittest discover -s tests -v
```

## Licenza

Codice distribuito secondo GNU General Public License v3.0 o successiva. Dataset, servizi e mappe di terzi mantengono le rispettive licenze.

MONITORAGGIO DAVIDE v0.6.0
=======================

INSTALLAZIONE
1. In QGIS aprire Plugin > Gestisci e installa plugin.
2. Selezionare Installa da ZIP.
3. Indicare Monitoraggio_Davide_v0.6.0.zip.
4. Attivare Monitoraggio Davide.

CONTENUTO DELLA PRIMA VERSIONE
- Interfaccia derivata dallo stile operativo RiSC.
- Selettori Lombardia, Veneto e Trentino.
- Avvio predefinito Lombardia > Brescia.
- Pulsanti rapidi Brescia e Padova; Veneto predefinito su Padova.
- Catalogo di sensori, inclusi nivometrici e nivopluviometrici.
- Schede meteo/radar, fiumi/dighe, neve, frane, sismica, Copernicus ed eventi.
- Primo connettore reale ARPA Lombardia: anagrafica, ultimi dati, tabella e layer QGIS.
- Connettore reale ARPAV: rete idrometeorologica XML, ultimi dati e layer QGIS.
- Connettore reale INGV: eventi degli ultimi 7 giorni, tabella e layer QGIS.
- Connettore reale Meteotrentino: stazioni attive e ultimi dati disponibili.
- Connettore reale ARPAE Emilia-Romagna: idrometri, soglie 1-2-3 e layer QGIS.
- Quadro cartografico automatico con base Google Hybrid.
- Gruppo QGIS dedicato "Monitoraggio Davide", senza cancellare i layer esistenti.
- Sensori tematizzati per famiglia: pioggia, idrologia, neve, temperatura, vento e umidita.
- Etichette in mappa con stazione, tipo sensore, ultimo valore e unita di misura.
- Importazione soglie da CSV con fonte, validita e riferimento ufficiale obbligatorio.
- Stati Regolare, Attenzione, Preallarme, Allarme e Soglia assente direttamente in mappa.
- Simbologia verde, gialla, arancione, rossa e grigia basata sulle soglie caricate.
- Aggiornamento automatico configurabile da 5 a 60 minuti.
- Test di raggiungibilita delle prime fonti pubbliche.
- Diagnostica tecnica locale, senza intelligenza artificiale.
- Configurazione PostGIS e cache SQLite locale dimostrativa.

LIMITI v0.6.0
- Il connettore ARPA carica l'ultimo dato disponibile, non ancora le serie storiche complete.
- Google Hybrid richiede connessione Internet ed e soggetto alle condizioni del fornitore.
- Le soglie CSV e quelle ARPAE sono operative; per le altre reti servono fonti ufficiali documentate.
- PostGIS e previsto, ma la connessione completa verra introdotta nella fase successiva.
- Radar e prodotti Copernicus sono catalogati ma non ancora caricati come layer live.
- Le soglie non vengono dedotte: devono essere importate da un atto o dataset ufficiale.
- Per ARPAE Emilia-Romagna le soglie sono importate automaticamente dal portale ufficiale.
- Il test delle fonti verifica raggiungibilita e autenticazione, non certifica la qualita del dato.

AUTORE
Davide Trentin

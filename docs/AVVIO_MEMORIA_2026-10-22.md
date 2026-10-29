# Avvio della memoria e schermata iniziale — 22 ottobre 2026

Questo documento descrive la build 102545. Il successivo intervento introduce
la [memoria paginata nella build 102546](PAGINAZIONE_MEMORIA_2026-10-22.md),
superando il limite della cronologia interamente trattenuta in RAM descritto qui.

## Modifiche

L'archivio conversazionale viene validato e trasformato in oggetti in una sola
lettura SQLite, all'interno dello stesso snapshot. La validazione completa resta
attiva: una riga non valida in fondo all'archivio non pubblica una cronologia
parziale e non sostituisce lo stato già presente in RAM.

La sincronizzazione iniziale dei messaggi nell'indice usa una sola transazione,
con un generatore progressivo, invece di aprire una connessione per ciascun
messaggio. Le righe già identiche restano invariate; i metadati cambiati vengono
aggiornati, comprese le revoche. Un errore a metà della sincronizzazione annulla
l'intera transazione. I vecchi identificatori di conversazione ambigui fra più
utenti non vengono attribuiti al primo proprietario trovato.

La rappresentazione di ricerca in RAM viene costruita alla prima ricerca,
conservando SQLite come fonte. La costruzione non ritarda più necessariamente
l'apertura dell'app. La prima ricerca può quindi essere più lenta di una ricerca
successiva: la misura sotto include anche questo costo.

## Limiti conservati esplicitamente

La cronologia continua a essere caricata per intero in RAM e verificata per
intero. Non è stato introdotto un limite che nasconde o elimina i vecchi messaggi.
Il costo continua a crescere con la storia, ma sono state eliminate operazioni
ripetute evitabili. Una vera collezione paginata richiede anche di adattare i
lettori dei moduli: non si sostituiscono le liste pubbliche con una finestra
incompleta fingendo che contenga tutta la storia.

La prima migrazione dal JSON e il caricamento dei pesi del modello restano
operazioni distinte; non si dichiara una riduzione del 92% dell'intero avvio.

## Misure locali

Tre aperture per dimensione, mediana; testi sintetici, Mac, nessuna inferenza.
Il confronto precedente usa copie congelate dei tre componenti prima di questo
intervento. Il costo combinato è la mediana delle somme osservate, non la somma
di due mediane indipendenti.

| Messaggi | Avvio prima | Avvio dopo | Prima ricerca prima | Prima ricerca dopo | Avvio + ricerca prima/dopo |
|---|---:|---:|---:|---:|---:|
| 100 | 56,72 ms | 4,29 ms | 1,07 ms | 3,80 ms | 57,76 / 8,09 ms |
| 1.000 | 597,02 ms | 16,91 ms | 4,03 ms | 27,82 ms | 602,67 / 44,62 ms |
| 5.000 | 3.267,24 ms | 79,56 ms | 16,49 ms | 173,01 ms | 3.283,73 / 252,10 ms |

A 5.000 messaggi: circa 97,6% in meno per il caricamento del componente;
92,3% in meno includendo la sua prima ricerca. Non misura batteria, temperatura,
riconoscimento vocale, qualità delle risposte o tempo globale Android.

## Schermata precedente al caricamento Python

La schermata nera «Loading...» con il marchio Kivy era la risorsa predefinita
python-for-android. `buildozer.spec` ora seleziona `assets/android/presplash.png` e
il fondo `#FAF9F5`, coerente con la schermata di caricamento esistente.

La nuova composizione contiene ALLMA, un cerchio sottile e «Preparo il nostro
spazio». È un'immagine statica piccola, visibile prima di Python: non mostra una
percentuale inventata né avvia un altro motore di animazione. Il caricamento
successivo conserva illustrazione e avanzamento esistenti. La composizione è
riproducibile con `tools/render_presplash.py`, usando il font Inter già nel progetto.

`tools/verify_android_apk.py` verifica che la risorsa nativa impacchettata coincida
con quella nuova, oltre ai sorgenti incorporati e agli asset di avvio esistenti.
È stato controllato anche il colore nel contenuto compilato delle risorse Android.

## Evidenze e stato

Build 102545, versione 0.9.1, installata in aggiornamento senza cancellazione dei dati.
Le tre prove iniziali hanno riprodotto 606 decodifiche per 300 messaggi,
303 aperture dell'indice e costruzione anticipata della cache. Dopo la modifica,
le prove mirate di integrazione contano 122 successi.

La diagnostica «Memoria incrementale e avvio» comprende ora 16 scenari: i dieci
precedenti e sei nuovi controlli su lettura singola, connessioni, ricerca differita,
riga finale corrotta, rollback della proiezione e revoca aggiornata all'avvio.

Evidenze: `/Users/erikahu/ALLMA/analisi/2026-10-22/startup-history/`.
Riepiloghi: `measurement-comparison.json`, `integration/summary.json`,
`full-tests/summary.json`, `apk-verification.json`, `native-resources.txt`.
Collaudo finale completato:

- Suite completa Mac: 2.214 casi raccolti, 2.199 superati, 15 saltati, zero fallimenti.
- Android: 16/16 scenari nuovi e precedenti in 0,76 s; 60/60 scenari generali in
  2,65 s. Dati sintetici e modello simulato, senza giudizi sul GGUF.
- Tutti e sette i componenti controllati coincidono con i sorgenti impacchettati.
- Riapertura a freddo effettuata con app libera e senza bozze: tre immagini nei
  primi due secondi mostrano la schermata abituale con l'illustrazione e il
  caricamento. La fase nativa precedente è così breve che le catture iniziano
  già dalla schermata Python; la nuova risorsa è verificata direttamente nell'APK.
  Non si presenta una cattura successiva come prova fotografica della fase nativa.
- Nessun contenuto di conversazione personale è stato copiato; le immagini
  conservate mostrano esclusivamente l'avvio e le barre Android.

Report Android: `android-summary.json`, `android-regression/android-summary.json`,
`android-installation.json`, `android-launch-frames.json` e `android-cold-start.json`.

Modifiche salvate localmente; nessun nuovo commit o aggiornamento GitHub.

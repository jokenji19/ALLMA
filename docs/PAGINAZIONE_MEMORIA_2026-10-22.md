# Memoria paginata — 22 ottobre 2026

L'intervento successivo riguarda la
[verifica iniziale della storia nella build 102547](VALIDAZIONE_AVVIO_2026-10-22.md),
che elimina le riletture per attribuire i vecchi messaggi.

## Risultato

La cronologia operativa usa pagine SQLite da 64 record e una cache di 128 oggetti
per collezione. I messaggi vecchi rimangono nell'archivio e si caricano quando
servono. Non viene sostituita la storia con gli ultimi 128 messaggi.

Build 102546, versione 0.9.1, installata in aggiornamento senza cancellare i dati.
Le impronte dei 14 sorgenti controllati sul telefono coincidono con quelle
dell'APK e dei sorgenti locali. La verifica del pacchetto comprende anche la
schermata nativa di avvio introdotta nella build precedente.

## Integrazione

- `PagedRows` conserva conteggi, posizioni e pagine recenti. Le scansioni complete
  leggono progressivamente lo stesso snapshot SQLite, senza trattenere tutti gli
  oggetti. I riferimenti di tracciamento sono deboli; una riga modificata resta
  invece trattenuta fino al salvataggio, anche quando esce dalla cache.
- Cronologia recente, contesto ordinario del core, API e interfaccia usano lettori
  limitati. Richiamo letterale, prove autobiografiche e revoche continuano a
  consultare l'intero archivio. Il limite del contesto non diventa un limite ai
  ricordi verificabili.
- Il conteggio mostrato dall'interfaccia si aggiorna dopo le transazioni riuscite.
  Non rilegge più tutti i messaggi ogni cinque secondi. Modifiche di proprietario,
  ruolo e cancellazioni aggiornano gli aggregati verificati.
- Identità autobiografica e proattività usano viste filtrate ripetibili. Il recupero
  degli intenti di consegna procede in una transazione, senza una lista completa
  temporanea. La proiezione iniziale nell'indice resta progressiva.
- Una pagina letta dopo l'avvio viene nuovamente validata. Se è danneggiata,
  l'accesso fallisce e le scritture si fermano fino al ripristino e ricaricamento
  esplicito. Un'istanza con generazione vecchia non legge nuove pagine come se
  appartenessero al suo archivio precedente.
- Salvataggi incrementali, rollback, metadati annidati, isolamento degli utenti,
  migrazione e backup mantengono il contratto precedente. La paginazione non
  introduce un altro formato durevole o un secondo archivio autorevole.

Le modifiche strutturali esplicite (ordinamento, inversione, sostituzione di
intervalli e cancellazioni strutturali) possono materializzare la collezione
interessata fino al commit. Dopo il commit tornano alla cache limitata. Anche
un'esportazione completa o un chiamante che conserva tutte le righe può usare
memoria proporzionale alla selezione: non si promette memoria costante per
qualsiasi uso dell'API.

## Misure riproducibili

Mac, archivi sintetici, confronto con i sorgenti congelati dell'APK 102545.
L'indice derivato è già sincronizzato. Le allocazioni sono misurate con
`tracemalloc`, dopo il caricamento; escludono pesi GGUF e memoria nativa.
Le latenze riportano separatamente la mediana di tre aperture senza il tracer.

| Messaggi | Oggetti trattenuti prima/dopo | Allocazioni Python prima/dopo | Avvio del componente prima/dopo |
|---|---:|---:|---:|
| 500 | 500 / 128 | 994.712 / 253.681 byte | 10,65 / 10,56 ms |
| 5.000 | 5.000 / 128 | 10.122.748 / 253.209 byte | 83,04 / 66,41 ms |
| 20.000 | 20.000 / 128 | 40.522.692 / 253.049 byte | 376,69 / 283,07 ms |

A 20.000 messaggi: circa **99,38% di allocazioni Python trattenute in meno**
per questo componente e **24,85% di tempo di caricamento in meno** nel campione.
Dopo una scansione completa rimangono 128 oggetti e circa 263 KB tracciati.
Queste percentuali non misurano RAM totale dell'app, qualità del modello,
temperatura, batteria o tempo complessivo di avvio Android.

La verifica completa dei record all'avvio resta progressiva e proporzionale al
numero di record. Non vengono letti soltanto 128 messaggi dal disco: vengono
trattenuti soltanto gli oggetti recenti. Anche indice di ricerca, dati utente,
record sporchi e riferimenti conservati dai chiamanti hanno costi distinti.

## Verifiche

- Suite completa offline sul Mac: 2.238 casi raccolti, **2.223 superati**, 15
  saltati, zero fallimenti. Cache dei modelli isolata e download disabilitati.
- Prove dedicate: cache limitata anche dopo scansione, accesso ai confini delle
  pagine, modifica di un vecchio oggetto dopo espulsione, salvataggio fallito,
  riordinamenti, contatori, istanza vecchia, recupero letterale, revoca successiva
  e danno a una pagina non ancora letta.
- La prima esecuzione completa ha rilevato due incompatibilità: il lettore API
  di un oggetto compatibile privo di `recent_messages` e una prova che iniettava
  il guasto nel vecchio lettore. L'API usa ora l'adattatore condiviso; la prova
  inietta lo stesso guasto nel lettore effettivamente usato, con le stesse
  asserzioni. I risultati iniziali sono conservati.
- Android: **25/25 scenari memoria, indice, avvio e paginazione**, in 2,16 s;
  **60/60 scenari generali**, in 2,60 s. Archivi temporanei e modello simulato,
  senza modificare o esportare le conversazioni personali. Questi esiti non
  misurano qualità del GGUF, voce o autonomia della batteria.
- Il processo Android resta attivo, senza traceback, segnali fatali o errori di
  inizializzazione dell'interfaccia. I due avvisi di caricamento corrispondono
  ai guasti deliberati dei casi sintetici `backup` (database danneggiato) e
  `invalid_tail` (record non valido): entrambi sono stati rifiutati come previsto.
  Il pannello Android del report è stato chiuso senza condividere contenuti.

Evidenze: `/Users/erikahu/ALLMA/analisi/2026-10-22/paged-history/`.
Riepiloghi: `memory-comparison.json`, `full-final/summary.json`,
`apk-verification.json`, `source-hashes.json` e
`android-source-verification.json`, `android-summary.json`,
`android-regression/android-summary.json` e `android-runtime-final.json`.

Modifiche salvate localmente. Nessun nuovo commit, push o aggiornamento della
release GitHub durante questo intervento.

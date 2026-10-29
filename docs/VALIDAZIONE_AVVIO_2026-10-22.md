# Verifica iniziale della storia — 22 ottobre 2026

## Intervento

La build 102547 mantiene il controllo completo dell'archivio, eliminando un
percorso di rilettura ripetuta dei vecchi messaggi senza proprietario esplicito.
Prima, per ogni identificatore non nella piccola cache, venivano lette e
decodificate tutte le conversazioni alla ricerca del proprietario. Con molti
identificatori il costo cresceva come messaggi × conversazioni.

Ora le conversazioni vengono validate per prime, nello stesso snapshot SQLite
dei messaggi. Una tabella temporanea indicizzata associa identificatori e
proprietari, senza trattenere tutti i testi in Python. La cache dei risultati
resta limitata a 128 identificatori. La tabella è gestita dalla connessione
SQLite e scompare quando viene chiusa: non è un altro archivio persistente.

Due proprietari diversi per lo stesso identificatore producono un risultato
ambiguo, senza assegnarlo al primo utente trovato. Ripetizioni dello stesso
identificatore per lo stesso proprietario restano valide. Il proprietario
esplicito del messaggio mantiene la precedenza. Anche una modifica concorrente
alla proprietà non mescola righe appartenenti a snapshot differenti.

La validazione del singolo record è condivisa fra archivio completo, caricamento
paginato, lettura delle pagine e salvataggio. Si eliminano le costruzioni di
piccoli archivi artificiali per controllare ogni riga. Il formato, i controlli
su contenuto, metadati, ruolo e data e le regole di migrazione restano invariati.
Un vecchio record conversazionale invalido impedisce la pubblicazione del nuovo
stato; la proiezione dell'indice non viene confermata a metà.

## Misure prima e dopo

Mac, archivi sintetici, sorgenti precedenti congelati dall'APK 102546. Tre
aperture per scenario, mediana; indice SQLite già sincronizzato. Nessun modello
linguistico viene eseguito. Sono misure del componente, non dell'intero avvio
Android, della RAM totale, della temperatura o della batteria.

| Messaggi | Conversazioni | Proprietario nei messaggi | Prima | Dopo | Riduzione nel campione |
|---|---:|---|---:|---:|---:|
| 1.000 | 1 | esplicito | 14,99 ms | 13,83 ms | 7,7% |
| 20.000 | 1 | esplicito | 233,83 ms | 217,14 ms | 7,1% |
| 4.000 | 1.000 | esplicito | 50,14 ms | 48,70 ms | 2,9% |
| 2.000 | 200 | da risolvere | 543,72 ms | 28,74 ms | 94,7% |
| 4.000 | 1.000 | da risolvere | 5.147,08 ms | 55,64 ms | 98,9% |

La prova strutturale con 360 messaggi e 180 conversazioni passa da **65.343 a
543 decodifiche JSON**: 360 messaggi, 180 conversazioni e tre sezioni di stato.
Il miglioramento molto elevato riguarda gli archivi che attraversavano il
vecchio percorso di risoluzione. La piccola differenza negli archivi recenti
resta una misura locale su tre aperture, senza garanzia di una percentuale
analoga su altri dispositivi.

Ogni record viene ancora letto e verificato all'avvio. Il costo della verifica
resta proporzionale alla storia, con le ricerche indicizzate aggiuntive per i
proprietari mancanti. Cache dei messaggi e accesso completo alle pagine vecchie
mantengono il contratto della build 102546. Esportazioni e riordinamenti espliciti
possono ancora materializzare la collezione interessata.

## Verifiche e consegna

- Riproduzione iniziale: un test falliva per 65.343 decodifiche al posto di una
  lettura per record; tre test di integrità e attribuzione passavano già.
- Dopo l'intervento: **120/120 test mirati** superati, inclusi backup,
  paginazione, concorrenza e i tre nuovi scenari della diagnostica Android.
- Suite completa offline: **2.231 superati, 15 saltati, zero fallimenti** su
  2.246 casi raccolti; cache dei modelli isolata e rete esterna disabilitata.
- L'APK verificata contiene i sorgenti attuali, il runtime ARM64 e gli asset di
  avvio. Versione 0.9.1, codice build 102547.
- Android: **28/28 scenari di memoria/indice/paginazione/avvio** in 2,02 s e
  **60/60 scenari generali** in 2,48 s. Archivi temporanei, modello simulato,
  conversazioni personali non utilizzate o esportate. I quattro sorgenti
  modificati controllati sul dispositivo coincidono con quelli impacchettati.
- Il processo rimane attivo senza traceback, segnali fatali o errori di avvio
  dell'interfaccia. I tre rifiuti di caricamento sono quelli attesi nei test
  con database danneggiato, messaggio invalido e conversazione invalida.
  Il pannello automatico del report è stato chiuso senza inviare contenuti.

Evidenze: `/Users/erikahu/ALLMA/analisi/2026-10-22/startup-validation/`.
File principali: `before/summary.json`, `decode-after.json`, `comparison.json`,
`targeted-final/summary.json`, `full/summary.json`, `apk-verification.json`,
`source-hashes.json`, `android-source-verification.json`, `android-summary.json`,
`android-regression/android-summary.json` e `android-runtime-final.json`.

Modifiche salvate localmente. Nessun nuovo commit, push o aggiornamento della
release GitHub durante questo intervento.

# Cronologia e indice incrementali — 22 ottobre 2026

Questo documento descrive la build 102544. Gli interventi successivi riguardano
l'[avvio della memoria](AVVIO_MEMORIA_2026-10-22.md) e la
[paginazione della cronologia](PAGINAZIONE_MEMORIA_2026-10-22.md).

## Esito

Build Android 102544, versione 0.9.1, installata in aggiornamento sul dispositivo.
F04 è corretto per l'inserimento ordinario e per l'invalidazione dopo modifiche.
La parte di F03 relativa alla riscrittura integrale per ogni turno è corretta.
Il caricamento iniziale, le liste della cronologia in RAM e varie query di
lettura restano proporzionali alla storia: paginazione e caricamento su richiesta
non fanno parte di questo intervento.

## Cambiamenti

Il core usa `conversation_history.db` come archivio attivo della cronologia.
Il vecchio `allma_memory.json` viene validato, migrato e conservato integro.
Quando il database esiste, anche un lettore compatibile usa quello, evitando
che una vecchia copia JSON diventi una seconda fonte attiva.

Il tracciamento delle modifiche comprende i record, i contenitori JSON annidati,
i dati utente, gli eventi persistenti e i gruppi delle conversazioni. Un nuovo
messaggio scrive una sola riga; una modifica a un vecchio messaggio aggiorna
quella riga. Le modifiche collegate sono confermate in una transazione SQLite.
Un salvataggio senza modifiche non apre una transazione di scrittura.
Riordinamenti e sostituzioni strutturali delle liste restano operazioni più
costose: non vengono presentati come inserimenti costanti.

- Un errore durante la transazione annulla tutte le scritture. Le modifiche
  valide restano disponibili per un nuovo tentativo.
- `store_message` rimuove dalla lista un nuovo messaggio che non è riuscito a
  salvare: non può comparire in un salvataggio successivo per errore.
- Il numero di generazione impedisce a un'istanza con dati vecchi di sovrascrivere
  aggiornamenti di un'altra istanza; serve prima un ricaricamento esplicito.
- Migrazione e coordinamento usano rinomina atomica e `flock`, già compatibili
  con lo spazio privato Android. Il marcatore di inizializzazione impedisce di
  ricreare automaticamente da un JSON vecchio un database successivamente perso.
- Corruzione o versione sconosciuta bloccano le scritture e preservano i file.
  Il caricamento fallito non sostituisce la memoria già presente in RAM.
- Backup, ripristino e regole Android includono il nuovo database e ne verificano
  schema e contenuto. Database e file di coordinamento sono esclusi dall'APK.

L'indice conserva conteggi sparsi dei termini e liste inverse per utente.
Gli inserimenti aggiungono solo le nuove righe; i punteggi TF-IDF usano comunque
le frequenze aggiornate dell'intero corpus. Le prove confrontano punteggi e
ordinamento con un calcolo completo indipendente, a ogni crescita dell'archivio.
Le revisioni SQLite rilevano anche modifiche esterne con lo stesso numero di
record e gli stessi identificatori: il vecchio indice poteva ignorarle.
Revisioni, punteggi e righe restituite condividono lo stesso snapshot di lettura.

Aggiornamenti, cancellazioni, avvio e rilascio della cache possono ancora
richiedere una ricostruzione completa; il percorso frequente di aggiunta non la
richiede. Isolamento degli utenti, revoche e provenienza restano verificati.

## Misure locali

Mac, dati sintetici, cinque cicli per dimensione, mediana. Nessuna generazione
GGUF. Per la cronologia l'indicizzazione è disabilitata; la baseline usa il
salvataggio JSON precedente. Per l'indice la baseline è il componente in HEAD
prima di questo intervento. Non sono misure Android, di temperatura o batteria.

| Messaggi iniziali | Salvataggio JSON | Salvataggio incrementale |
|---|---:|---:|
| 100 | 2,26 ms | 1,74 ms |
| 1.000 | 14,50 ms | 1,25 ms |
| 5.000 | 73,08 ms | 1,06 ms |
| 20.000 | 297,69 ms | 1,47 ms |

A 20.000 messaggi, il tempo di questa singola operazione scende di circa il
99,5%. Le date serializzate per ogni inserimento passano da oltre 20.000 a una.
Non è una percentuale di miglioramento dell'intelligenza o dell'intera app.

| Ricordi iniziali | Aggiunta + ricerca precedente | Aggiunta + ricerca incrementale |
|---|---:|---:|
| 100 | 6,71 ms | 1,46 ms |
| 1.000 | 45,34 ms | 4,99 ms |
| 5.000 | 269,35 ms | 19,96 ms |

A 5.000 ricordi, il tempo misurato scende di circa il 92,6%. In cinque cicli le
ricostruzioni complete passano da cinque a zero. La ricerca continua ad avere un
costo legato ai candidati e ai termini presenti: non è indipendente dalla storia.

## Verifiche

- Suite completa Mac: 2.202 casi raccolti, 2.187 superati, 15 saltati.
  Due gruppi, 128 casi complessivi, sono stati ripetuti fuori dalla sandbox per
  gli arresti OpenMP dovuti alla memoria condivisa; tutti superati a codice e
  controlli invariati. I risultati originari non sono stati rimossi.
- Android: dieci scenari nuovi superati in 2,47 s, con archivi temporanei;
  migrazione, inserimento dopo 1.000 righe, metadati annidati, transazione
  interrotta, istanza vecchia, backup/corruzione, indice incrementale, modifiche
  esterne, revoche e rilascio della cache.
- Android: 60 scenari generali superati in 2,58 s. Usano dati e modello simulati;
  non valutano qualità del GGUF, riconoscimento vocale o autonomia della batteria.
- I dieci sorgenti controllati sul telefono coincidono con quelli impacchettati.
  Nuovo database reale e marcatore presenti, app avviata.
- Il JSON originale resta invariato fra l'avvio nuovo e il completamento della
  migrazione. La versione precedente lo aveva risalvato durante l'aggiornamento:
  l'impronta prima dell'installazione e quella prima della migrazione sono
  distinte e conservate nelle evidenze. Non si attribuisce quella modifica alla
  migrazione nuova. Nessuna conversazione personale è stata copiata sul Mac.

Evidenze: `/Users/erikahu/ALLMA/analisi/2026-10-21/memory-scaling/`.
Report principali: `full-final-summary.json`, `scale-measurements.json`,
`android-summary.json`, `android-regression/android-summary.json`,
`android-migration.json`, `apk-verification.json` e `source-hashes.json`.

Modifiche salvate localmente; nessun nuovo commit, push o modifica alla release
GitHub 0.9.1 pubblicata in precedenza.

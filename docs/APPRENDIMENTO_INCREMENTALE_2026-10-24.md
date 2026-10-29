# Salvataggio incrementale dell'apprendimento — 24 ottobre 2026

## Risultato della build 102552

Il core usa `incremental_cache/knowledge_states.db` come archivio autorevole
dell'apprendimento. Le API aggiungono le nuove unità, i nuovi riscontri e i nuovi
eventi di progresso separatamente, aggiornando soltanto le intestazioni, i
contatori, le varianti e gli insiemi interessati. Non riscrivono un JSON completo
né mantengono una seconda copia JSON aggiornata dopo ogni interazione.

Il cambiamento riguarda la persistenza. Restano le stesse regole di ammissione,
provenienza e confidenza: una risposta generata non diventa automaticamente una
conoscenza verificata. Identità, memoria episodica, personalità e GGUF restano
sottosistemi distinti.

## Formato e transazioni

Le tabelle del database separano:

- `learning_maps`: intestazioni degli argomenti e degli utenti, contatori e varianti;
- `learning_lists`: unità, riscontri e progressi recenti, ciascuno con posizione;
- `learning_sets`: fonti, argomenti degli utenti e aree di miglioramento;
- `learning_meta`: generazione e checkpoint delle consegne.

Una mutazione normale serializza le code aggiunte e le intestazioni interessate.
Le posizioni rendono verificabile l'ordine delle liste. Il checkpoint viene
confermato nella stessa transazione dei dati: la ripresa di una consegna già
applicata non riapprende l'evento.

`BEGIN IMMEDIATE`, controllo della generazione e rollback impediscono a uno
scrittore precedente di sovrascrivere modifiche più recenti. Se una scrittura
fallisce, vengono ripristinate anche le collezioni in RAM del mutatore. Il flush
in pausa attende i commit e verifica la generazione senza riscrivere l'archivio.

`save_state()` fuori da una mutazione resta un salvataggio completo esplicito per
modifiche manuali, compresa la rimozione di voci. I chiamanti che indicano un
percorso `.json` conservano il precedente formato di compatibilità; il core
ordinario sceglie il percorso `.db`.

## Migrazione e recupero

La migrazione legge e valida tutto il JSON precedente, scrive un database
temporaneo, verifica il risultato e lo pubblica con rinomina atomica. Un lock
coordina due inizializzazioni concorrenti. Il JSON originale resta invariato.
Le versioni JSON 1 e 2 conservano unità, stati, fonti, riscontri, varianti,
progressi e checkpoint; il recupero delle unità legacy segue la logica precedente.

Un marcatore locale impedisce di ricreare da un JSON vecchio un database già
migrato ma successivamente scomparso. Un database mancante, danneggiato o con
versione futura blocca il salvataggio: non viene pubblicata una parte dei record
validi ignorando quelli invalidi. Ordine, appartenenza delle liste, riferimenti
degli insiemi, date e tipi sono controllati prima di pubblicare lo stato caricato.

## Backup e trasferimento

Il database è incluso nei file persistenti e nelle regole Android. I backup
verificati dell'app usano la copia SQLite, includendo le righe confermate in WAL,
e validano anche lo schema logico. Quando esiste il database corrente, il JSON
di migrazione non entra nella nuova copia: non è una seconda fonte attuale.
Il file originale resta comunque sul dispositivo.

Una copia precedente che contiene soltanto il JSON resta importabile e viene
migrata al successivo caricamento. L'esportazione cifrata e il ripristino su
un'installazione sintetica separata conservano lo stato corrente e il checkpoint.
Un database scomparso dopo migrazione non permette di certificare un nuovo backup
del solo JSON obsoleto. Le regole del backup di sistema ammettono entrambi i
formati per la compatibilità; il percorso verificato dell'app controlla l'intero
manifest prima del ripristino.

## Verifiche

| Controllo | Esito |
|---|---:|
| Prima integrazione con core e consegne | 191/191 |
| Prove mirate finali di archivio, backup e compatibilità | 149/149 |
| Suite completa offline | 2.379 superati, 15 saltati, zero fallimenti su 2.394 raccolti |
| Android, migrazione e apprendimento | 18/18 |
| Android, regressioni generali | 60/60 |
| Pausa e riavvio reali della 102552 | Salvataggio completato e chat riaperta in un nuovo processo senza errori di caricamento |

I test mirati si sovrappongono alla suite completa; i conteggi non rappresentano
una percentuale universale di affidabilità. I casi comprendono errore dopo le
scritture ma prima del commit, rollback di cinque API, ripetizione delle consegne,
istanza obsoleta, inizializzazione concorrente, dati invalidi, database mancante,
backup correnti e precedenti e trasferimento cifrato su dati sintetici.

Il riavvio eseguito riguarda l'app, non un riavvio di Android: è stata
verificata prima la pausa, poi avviato un nuovo processo di ALLMA. Non sono state
esportate conversazioni né ripristinato l'archivio personale per fare le prove.

Evidenze: `/Users/erikahu/ALLMA/analisi/2026-10-24/learning-incremental/`.
Sono conservati il sorgente precedente del learner, le misure, i report, la
verifica dell'APK e le impronte dei sorgenti. Il primo campione di misura fu
rifiutato dall'asserzione perché condivideva la directory dei formati: il nuovo
archivio importava correttamente il JSON appena prodotto dall'altro campione.
La misura finale usa directory separate, senza cambiare la migrazione del prodotto.

## Misure e costi

Confronto locale sul Mac, 1.000 unità precedenti e tre nuove aggiunte; mediana
dei tre campioni. Non misura il GGUF o la latenza dell'intera app.

| Caso | Salvataggio JSON, ms | Salvataggio incrementale, ms | Caricamento JSON, ms | Caricamento DB, ms |
|---|---:|---:|---:|---:|
| 1.000 argomenti | 23,94 | 1,03 | 6,41 | 15,56 |
| 1.000 unità nello stesso argomento | 12,20 | 1,02 | 3,03 | 7,17 |

La quantità di JSON serializzato nel campione passa da circa 1,10–1,44 MB per
aggiunta a 263–269 byte di record. Questo confronto include il diverso formato
dei record e non equivale ai byte fisici scritti da SQLite, che comprendono
pagine, indici, journal e sincronizzazione.

L'archivio DB del campione occupa circa il 21–30% in più del JSON; durante la
migrazione si conserva anche il JSON originale, quindi lo spazio totale iniziale
è maggiore della sola dimensione del database. Il caricamento iniziale del
componente aggiunge circa 4–9 ms nel campione. Le misure iniziali dei soli salvataggi
sono conservate separatamente in `initial-write-comparison.json`.

## Limiti

Il caricamento valida ancora tutti i record e li materializza in RAM. Gli
algoritmi di aggiornamento conservano le copie delle strutture modificate per il
rollback: con liste lunghe può restare un costo in RAM/CPU. La scrittura è
incrementale; non si dichiara ancora un costo totale costante di ogni operazione
o una cache limitata per tutto l'apprendimento.

Restano i limiti del formato di backup e la necessità di una copia cifrata esterna
per proteggersi dalla perdita del telefono. Batteria, temperatura, qualità del
modello e conservazione per anni non vengono dedotte dai tempi locali. Le
modifiche sono salvate localmente e non pubblicate su GitHub da questo intervento.

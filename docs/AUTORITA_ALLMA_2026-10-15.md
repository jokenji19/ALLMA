# ALLMA governa; i modelli propongono

## Vincolo implementato nel nuovo ciclo agentico

ALLMA possiede il registro persistente degli obiettivi e dei permessi. Qwen e Decider forniscono elaborazioni e proposte. Nessuna risposta testuale o probabilità del modello è un’autorizzazione o una verifica di completamento.

`ALLMACore.action_authority` usa una sezione distinta del `CognitiveStateStore` esistente, accanto alle sezioni cognitive, indipendente dai file dei modelli. Non crea obiettivi alla nascita e non trasforma automaticamente ogni messaggio in un obiettivo permanente.

Il codice chiamante ammette un obiettivo da un evento utente/UI identificato: proprietario, richiesta, priorità, azioni consentite e classi di permesso. Il modello riceve solo la descrizione del contesto e le opzioni ammissibili. Non riceve il registro mutabile o una funzione per assegnarsi permessi.

## Regole

- Un ciclo normale senza autorità rifiuta di eseguire azioni.
- Una richiesta non può usare obiettivi di altri utenti.
- Prima dell’esecuzione, l’autorità verifica nuovamente che l’obiettivo sia attivo e che nome e classe dell’azione siano autorizzati. La revoca avvenuta durante l’inferenza blocca l’azione suggerita.
- L’ammissione e l’esecuzione della singola azione sono serializzate rispetto alla revoca. Un’azione già iniziata deve cooperare con il segnale di cancellazione per fermarsi prima del ritorno.
- `read`, `memory_write`, `state_write`, `external` sono classi distinte. Un permesso di lettura non autorizza scrittura o comunicazioni esterne.
- Gli argomenti e la verifica degli strumenti appartengono al codice. Il modello seleziona soltanto un nome.
- La modalità diagnostica esplicita senza obiettivo autorizza solo callback di lettura registrate dal codice. Non può ampliare i permessi alle scritture.
- `stop`, astensione, esaurimento del budget e verifica di una singola azione non completano automaticamente l’obiettivo. Il completamento richiede una verifica del codice chiamante su evidenze appropriate.
- Ripetere lo stesso evento non riapre un obiettivo revocato e non amplia i suoi permessi.
- Obiettivi e priorità persistono dopo riavvio e sostituzione del motore; il registro non contiene nomi di modelli o loro pesi.
- Il registro è limitato a 256 obiettivi: oltre il limite rifiuta nuove ammissioni, senza cancellare di nascosto obiettivi esistenti. Gestione dell’archivio e interfaccia degli obiettivi non introdotte in questa modifica.

## Correzione dell’apprendimento esistente

`IncrementalLearner.learn_from_interaction` considerava verificata anche una risposta priva di `response_verified=False`. Ora soltanto il valore booleano esplicito `True`, impostato dal codice chiamante dopo una verifica, ammette il contenuto della risposta nel percorso verificato. Valore assente, false, stringhe e interi restano non verificati.

In questi casi viene conservata la dichiarazione dell’utente con provenienza `user_statement` e `knowledge_verified=False`; il testo inventato dal modello non viene promosso a conoscenza. Il percorso chat aveva già un `False` esplicito: il cambiamento protegge gli altri chiamanti e quelli futuri. I vecchi record non vengono riscritti o ricertificati.

La conversazione può conservare ciò che il modello ha detto come messaggio dell’assistente: questo non rende vera la frase e non la trasforma in un episodio vissuto dall’utente.

## Confini e limiti

Questa è una barriera applicativa per modelli che restituiscono dati. I callback degli strumenti e i chiamanti Python sono codice fidato; non è una sandbox contro codice Python arbitrario o un file di stato manomesso deliberatamente. La marcatura `response_verified=True` è un’asserzione del chiamante fidato: non deve essere deserializzata da output del modello né derivare dalla sola sua autovalutazione.

Il nuovo registro governa il nuovo `ActionCycle`. Non sostituisce tutti i percorsi storici di memoria, sogni, sensori, notifiche e crescita emotiva. Questi mantengono le proprie verifiche. Non è quindi una certificazione di ogni modifica di stato nell’intera architettura.

Decider resta diagnostico, senza inferenze aggiunte alle chat. Nessuna nuova curiosità autonoma, notifica o scrittura viene attivata. La nuova infrastruttura prepara un’integrazione successiva governata da ALLMA.

## Verifiche

Test dedicati: assenza di autorità, separazione utenti, escalation, revoca durante inferenza, replay, completamento non autoattribuito, persistenza, priorità, sostituzione del motore, snapshot non mutabili, errore disco, record malformati, e risposta inventata non appresa senza verifica.

La selezione e la disponibilità nativa del modello Decider su Android erano già verificate nella build 102480. Questa modifica non pretende di migliorare la qualità del suo caso memoria ancora non riuscito.

### Esito dei test sul Mac

- Verifica ampia: 176 test passati in 233,50 s (autorità, decisore, apprendimento, persistenza cognitiva, ciclo di vita, core, cambio modello e crescita emotiva).
- Verifica mirata sull’ultima versione: 38 test passati, inclusa la modalità diagnostica esplicita e gli asset/bridge del benchmark.
- Binding dei modelli: 12 test passati.
- Totale distinto nelle selezioni: 191 casi, senza sommare più volte quelli ripetuti.

Il test precedente poteva usare una classe di permesso generica `write`: il nuovo registro la rifiuta e richiede `memory_write`, `state_write` oppure `external`. I test di escalation ora usano la classe corretta. Nessun fallimento ignorato.

### Distribuzione Android

APK build 102481 installata con `adb install -r` (Success), package `org.allma.allma_prime`, versione 0.9.0.0. Payload confrontato con i sorgenti e runtime ARM64 verificato. SHA256 APK `14918366d106cfdbc9bd2ab2eec7a921188d080be1a64ea64f1b72b1d5a38ba6`. Processo avviato dopo installazione: 7314. Le prove dei nuovi vincoli sono state eseguite sul Mac; non si dichiara un nuovo collaudo end-to-end Android del ciclo agentico.

Avvio nativo confermato nei log del processo 7314: `Llama Init Success`, `Model loaded successfully`, motore collegato al reasoning engine e TTS collegato. Non è una nuova misura di qualità o velocità.

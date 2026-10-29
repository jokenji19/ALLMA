# Decider: ricaricamento e continuità della conversazione

Build Android **102557**, versione pubblica **0.9.1**. Installata sul Galaxy S25 Ultra, senza cancellare i dati dell'app.

## Problemi riscontrati

Nella conversazione esaminata Decider funzionava sulla NPU: i turni a modello già caricato richiedevano 82–97 ms. Dopo la pausa dell'app, però, il contesto nativo veniva rilasciato e il caricamento successivo ripeteva anche la lettura SHA-256 dell'intero file da 529.297.504 byte. Tre instradamenti con caricamento richiedevano 6.261, 6.878 e 6.167 ms.

Le risposte mostravano inoltre confusione fra identità ALLMA e modello collegato, richiamo della prima domanda invece di quella precedente ed errori di conoscenza generale. L'ultima risposta era stata trattenuta con `subject_mismatch`. Il candidato privato trattenuto non era disponibile: non è possibile stabilire da quel solo avviso se il controllo fosse un falso positivo. Non è stato disabilitato.

## Modifiche

- Verificatore di integrità condiviso fra download e inferenza, senza dipendenze grafiche. Il primo accesso verifica tutti i byte; la cache dura solo nel processo e dipende da dispositivo, inode, dimensione, mtime, ctime e SHA atteso. File modificati, sostituiti o cambiati durante la verifica non vengono certificati. I controlli concorrenti dello stesso percorso condividono una sola lettura.
- Tempi separati per verifica, preparazione backend, caricamento nativo e tokenizzazione delle etichette, registrati senza contenuti personali.
- Richiamo letterale delle domande recenti della chat corrente: domanda precedente, domanda prima/dopo una citazione esatta e seguito del riferimento. L'utente e la conversazione sono delimitati esplicitamente; i riferimenti conservano timestamp e hash del messaggio. Citazioni duplicate richiedono chiarimento; dati fuori dalla finestra disponibile non diventano affermazioni di assenza nell'intero archivio.
- Descrizione del nome ALLMA dal nucleo identitario, distinta dal componente linguistico e senza inventare un'espansione dell'acronimo.

Il rilascio del contesto Decider in background resta attivo: questa ottimizzazione non trattiene la NPU per evitare il ricaricamento. Modello, soglie di accettazione, budget di ragionamento e isolamento CPU/GPU/NPU restano quelli della 102556.

## Risultati sul telefono

| Misura | Risultato osservato |
|---|---|
| Caricamento nativo Decider, tre avvii con file già verificato | 1.296,1 / 1.289,3 / 1.125,5 ms |
| Verifica durante questi caricamenti | 0–0,3 ms |
| Instradamento operativo con caricamento, prima/dopo pausa | 1.395 / 1.232 ms |
| Diagnostica Decider | 8 casi completati: 6 scelte accettate corrette, 2 astensioni, 0 scelte accettate errate |
| Cinque risposte ospitate dal sistema | 627–639 ms da invio a risposta rilevata dalla sonda UI |
| Richiami letterali e nome | 4 confronti esatti superati; descrizione dell'identità verificata separatamente |
| Pausa e ritorno | Stato salvato, stesso processo 13522, ricaricamento NPU riuscito |
| Marcatori di operazione incompleta | Nessuno per GPU o NPU al termine |

La mediana osservata dell'instradamento con ricaricamento passa da 6.261 a 1.313,5 ms, circa **−79%**. Le richieste prima e dopo sono diverse: è una misura dell'attesa di ricaricamento osservata, non un confronto randomizzato della latenza totale. Il primo controllo completo in un nuovo processo resta necessario.

Qwen è confermato su OpenCL e Decider su Hexagon. Le due generazioni sintetiche completano in 4,70 e 7,57 secondi, con TTFT 1,42 e 1,52 secondi e stato termico `ok`. La seconda spiegazione è semanticamente imprecisa: la qualità generale non è risolta dai percorsi letterali. Nessuna percentuale di risparmio energetico è stata misurata.

## Validazione e tracciabilità

- **2.447 test superati, 15 saltati**: 2.444 nella suite ordinaria e tre casi di recupero dopo arresto eseguiti separatamente fuori sandbox per il supporto OpenMP.
- APK verificata contro i sorgenti incorporati, risorse di avvio, ABI e backend nativi.
- SHA-256 APK: `5387a8e62edecb3627ced9ea3930e438e5fa6a46e4bc29991c4ffaec498feb7d`.
- Evidenze locali: `analisi/2026-10-24/decider-avvio/` nella directory che contiene il progetto. `summary.json`, `android-chat-flow.json`, `android-load-1.txt`, `android-generation.txt` e i risultati pytest contengono misure e conversazione sintetica. La conversazione personale non è stata esportata come archivio.
- Spegnimento automatico dello schermo ripristinato a 60.000 ms al termine delle prove.

Rimangono da affrontare la correttezza delle risposte generali del modello, il costo del primo controllo completo, la crescita del prefill con conversazioni lunghe e la misura energetica controllata.

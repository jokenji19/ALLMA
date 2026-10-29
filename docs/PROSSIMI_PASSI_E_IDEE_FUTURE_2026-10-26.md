# Prossimi passi e idee future — 26 ottobre 2026

Documento di priorità, non attestazione di interventi completati. Il controllo di oggi comprende lettura di sorgenti e rapporti recenti e otto sonde locali su percezione ed emozioni; non costituisce una nuova verifica completa di tutti i moduli o un collaudo Android.

## Idea rinviata su indicazione dell'utente

**ALLMA-LM v0.1: progetto futuro, non avviato e senza data programmata.**

L'idea è specializzare un modello aperto per collaborare con ALLMA, iniziando eventualmente da Qwen3.5-2B già integrato. Un successivo esperimento di distillazione è distinto dal primo fine-tuning. Identità, ricordi, obiettivi e sviluppo personale rimangono nell'architettura persistente di ALLMA.

Per l'eventuale ripresa: dati autorizzati o sintetici, separazione fra addestramento/validazione/test, controllo del ragionamento e delle regressioni, confronto prima e dopo quantizzazione, GGUF e profilo GPU verificati, rapporto Android e ritorno alla base precedente. La discussione non autorizza spese o servizi di addestramento. Non sono stati creati dati di training, adattatori o nuovi modelli.

## Correzioni confermate da controlli locali

1. **Urgenza nel componente percettivo.** `PerceptionSystemLite._detect_urgency` ricerca frammenti senza confini di parola e senza gestire la negazione. `Descrivi un fiore colorato` produce urgenza media; `Non è urgente e non serve rispondere subito` produce urgenza alta. Il controllo positivo `Ho bisogno di una risposta urgente, subito` produce correttamente urgenza alta. Questo è un risultato del componente: non prova da solo che la pipeline cambi effettivamente il budget della chat in questi tre casi. Correggere rilevazione, ambito, negazioni e citazioni prima di estenderne l'influenza.

2. **Copertura emotiva multilingue.** `Sono molto felice` e `I am very happy` restituiscono gioia. `Estoy muy feliz`, `Je suis heureux` e `Ich bin glücklich` non producono sfumature riconosciute e restituiscono `analysis.uncertain=true`. L'incertezza è corretta; manca la copertura positiva equivalente. Ampliare insieme lessico, negazioni, attribuzione, tempo ed esempi fuori ambito, preservando la distinzione fra assenza di evidenza e neutralità certa. Non è una misura della comprensione linguistica del GGUF.

Evidenza: [controlli-componenti.json](/Users/erikahu/ALLMA/analisi/2026-10-26/priorita-future/controlli-componenti.json).

## Interventi proposti, ancora da attuare o misurare

| Priorità | Intervento | Motivo e verifica |
|---|---|---|
| Alta | Correggere la percezione descritta sopra | Difetti riproducibili; verificare anche frasi legittime, negazioni e soggetti differenti |
| Alta | Confrontare finestre del modello da 2.048, 4.096 e 8.192 token | Il wrapper attuale usa 2.048. Confrontare stessi dialoghi e modello, quantità utile di storia/ricordi, attesa iniziale e RAM; nessun aumento indiscriminato |
| Alta | Collaudo prolungato CPU/GPU/NPU e voce | Le prove brevi già passate non misurano sessioni di 20–30 minuti. Rilevare latenza mediana e casi lenti, memoria, temperatura, decadimento delle prestazioni, cancellazione e rientro |
| Alta | Consolidare il lavoro locale in un punto Git verificabile | Il checkout contiene molte modifiche non committate. Rivedere contenuti, escludere dati personali e artefatti non necessari, conservare sorgenti e corrispondenza con APK; nessun commit/push eseguito da questa nota |
| Media | Limitare la memoria residente dell'apprendimento su archivi grandi | La scrittura è incrementale, ma `LearningStore.load` ricostruisce ancora tutte le strutture. Misurare crescita e valutare lettura per argomento/cache limitata, mantenendo integrità e recupero |
| Media | Misurare trasferimento dell'apprendimento a formulazioni nuove | Richiamo esatto, associazioni confermate e apprendimento dei piani esistono già. Usare domande e contesti nuovi, correzioni e revoche per verificare quale beneficio si trasferisce senza consolidare errori |
| Media | Curiosità collegata alle questioni rimaste aperte | Proposte utili e poche, derivate da obiettivi e conversazioni esistenti; collegare fonte e stato, rispettare consenso e chiusura dell'argomento. Evitare un secondo archivio concorrente dei medesimi fatti |
| Media | Test di coerenza fra memoria, risposte apprese, personalità e piani | Una correzione deve essere rispettata nei diversi consumatori; documentare casi già coperti e trovare collegamenti ancora scoperti |
| Media | Stato del backup e prove su archivi grandi | I backup verificati esistono. Rendere visibili ultima copia, verifica, destinazione e vicinanza ai limiti; una copia esterna cifrata serve alla perdita del telefono. Il formato attuale impone 512 MiB per file e 2 GiB complessivi |
| Dopo consolidamento | Foto su richiesta | `VisionSystem.analyze_image` non esegue ancora inferenza VLM. Partire da una foto nella chat corrente con provenienza e limiti espliciti; profondità e percezione continua sono interventi successivi |

Un eventuale adattamento dello sforzo e delle risorse deve estendere le politiche esistenti, non aggiungere un secondo controllore in conflitto. Il fatto che una risposta sia breve non prova che sia corretta; i risparmi vanno misurati sul telefono.

## Idee di prodotto da valutare

- Una vista semplice che spieghi da dove proviene una risposta: calcolo, ricordo, informazione riferita dall'utente o generazione del modello, usando i metadati effettivi.
- Un riepilogo dell'evoluzione che mostri esempi verificabili di preferenze corrette, informazioni apprese e strategie riutilizzate; separare le dichiarazioni dell'utente dalle verifiche esterne.
- Un quadro dei progressi con indicatori separati: correttezza su casi nuovi, rispetto delle correzioni, recupero dei ricordi, tempi, RAM e stabilità. Nessuna percentuale unica di perfezione ricavata dai test software.

## Ordine operativo suggerito

Prima percezione e copertura emotiva; poi confronto del contesto con lo stesso Qwen. Eseguire successivamente un collaudo prolungato, usando quei risultati per intervenire sulle risorse e sul caricamento dell'apprendimento. Curiosità, coerenza fra moduli e visione si valutano su una base consolidata. La conservazione del codice e dei dati accompagna il percorso. ALLMA-LM rimane rinviato.

Riferimenti: [audit aggiornato](AUDIT_AGGIORNATO_2026-10-22.md), [apprendimento incrementale](APPRENDIMENTO_INCREMENTALE_2026-10-24.md), [continuità del dialogo](CONTINUITA_E_PERTINENZA_2026-10-26.md), [esito finale GPU](RIPRISTINO_GPU_E_AGGIORNAMENTI_2026-10-26.md), [verifica dei piani](VERIFICA_PIANI_E_COLLEGAMENTI_2026-10-25.md).

## Avanzamento successivo

Le correzioni di urgenza e copertura emotiva sono ora implementate; dettagli e limiti nel [rapporto di intervento](PERCEZIONE_E_CONTESTO_2026-10-26.md). Aggiunto il confronto preliminare della storia conservata con 2K/4K/8K, usando il tokenizer nativo senza cambiare la finestra operativa. Il confronto di inferenza, RAM e temperatura rimane separato e ancora da eseguire. Le priorità sopra descrivono la situazione prima di questo intervento.


Aggiornamento successivo: il [confronto di inferenza reale, build 102574](CONFRONTO_CONTESTO_REALE_102574.md) è completato. Dodici richieste su Android, configurazione originale 2K ripristinata. L’aumento del contesto non ha migliorato i casi di qualità provati e la produzione resta a 2K.


27 ottobre: [diagnosi del ragionamento, build 102577](DIAGNOSI_RAGIONAMENTO_2026-10-27.md), con CPU/GPU, budget, penalità, stato, casi nuovi e correzione del motivo di arresto. La configurazione generale resta invariata; il profilo 128/neutro va valutato selettivamente attraverso la pipeline.

### Punti 4–8 — 27 ottobre 2026

Implementati lettura a pagine dell’apprendimento, recupero per proprietario senza indice TF-IDF duplicato, focus di curiosità documentati e pagina «Cosa imparo» con origine delle risposte. Aggiunta una batteria di 50 scenari e una sessione Android reale di 25 minuti; gli esiti e i limiti sono nel [rapporto dei punti 4–8](PUNTI_4_8_2026-10-27.md). Conservare separati i progressi software dalla qualità del modello e dal consumo energetico misurato.

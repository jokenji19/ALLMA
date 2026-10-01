# Nucleo identitario e provenienza dell’esperienza

## Requisito

ALLMA nasce con un solo dato autobiografico originario: il nome ALLMA. La conoscenza generale del modello e le capacità strutturali dell’app non sono ricordi personali. La storia si costruisce tramite eventi attribuiti e persistenti. Lo stesso GGUF può sostenere stati personali diversi nel tempo.

## Implementazione

- OriginIdentity è un valore immutabile fuori dal VectorMemoryEngine e dagli archivi evolutivi. Non vengono assegnati età, preferenze, esperienze o un passato iniziale. Rimossa la conoscenza Python inserita artificialmente nel learner alla creazione del core; il modello mantiene la conoscenza generale nei propri pesi. Gli archivi esistenti non vengono azzerati.
- Le domande personali supportate passano per grounded_reply: nome proprio, nome dell’utente, preferenze non documentate e verifica delle conversazioni su un argomento. Nome utente solo da dichiarazioni esplicite attribuite o profilo dello stesso utente. Una correzione successiva prevale; le dichiarazioni rimangono in cronologia.
- I riferimenti a conversazioni citano un evento e il suo autore. Il fatto che un messaggio sia stato scritto è documentabile; il contenuto del messaggio non diventa per questo un fatto vero. Ricerca lessicale conservativa: l’assenza di corrispondenze è espressa come mancato ritrovamento, non certezza di non averne mai parlato.
- Prompt ripulito dalle istruzioni che imponevano coscienza biologico-digitale, REM notturna ed esperienze di sonno. Meccanismi cognitivi e conoscenza generale restano utilizzabili; non vengono presentati come una biografia.
- Le risposte del modello sono trattenute fino ai controlli su identità e alcune categorie di affermazioni personali. Una risposta respinta non viene mostrata né appresa; viene fornita una spiegazione prudente, marcata non valida ai fini dell’apprendimento. I pensieri restano separati.
- Le vecchie risposte restano nella cronologia visibile, ma senza l’attuale versione della policy non vengono reinserite nel prompt come contesto attendibile. Gli indici preesistenti non sono cancellati: il richiamo destinato al prompt filtra i record per fonte utente prima del limite dei risultati. Il learner riceve dichiarazioni dell’utente a bassa confidenza, con fonte esplicita; le risposte LLM non verificate non sono promosse a conoscenza.
- Rimossi i filtri predefiniti che eliminavano nomi di tecnologie o auto-presentazioni anche dentro citazioni e racconti. L’identità è controllata separatamente, non riscritta mediante sostituzioni globali.
- I turni brevi conservano il contesto ammissibile. Saluti e richieste personali supportate non richiedono inferenza. Il riconoscimento della complessità usa confini di parola: “capitale” non attiva più “tale”. Generazioni normali limitate a 384 token; complesse a 768, con ulteriori limiti termici preesistenti.
- L’ambiguità osservata “Mi piace la storia” produce una richiesta di chiarimento fra disciplina storica e racconti.

## Collaudo e limiti

La prima build di questo intervento ha verificato sul telefono nome, nome utente sconosciuto, preferenza assente, ricordo assente e capitale d’Italia. Il nome ha impiegato 0,23 s secondo l’interfaccia. Il modello ha però prodotto ragionamento non separato e un’antologia personale inventata nel test sull’ambiguità di “storia”: quella build intermedia non è considerata conclusiva.

È stato ripristinato il prefisso di pensiero aperto già verificato, mantenendo il bypass per le domande brevi supportate; aggiunti controlli per affermazioni personali senza fonte e chiarimento del caso ambiguo. La policy è stata incrementata per escludere dal contesto anche le risposte della build intermedia.

Le regole personali e i controlli linguistici sono conservativi e non costituiscono un verificatore semantico universale. Il riconoscimento delle parafrasi, delle dichiarazioni articolate e dei temi dei ricordi può ancora essere ampliato. Non è stato implementato un nuovo motore autonomo di formazione delle preferenze personali: in assenza di preferenze documentate l’app riconosce di non averne. La qualità generale del GGUF, le lunghe conversazioni e le richieste creative richiedono collaudo continuativo.

Modifiche salvate localmente; nessun commit o push. Artefatti in analisi/2026-09-30/nucleo-identitario nella cartella superiore al repository.

## Risultati del collaudo ripreso

Suite aggiornata: **336 passati, 15 saltati, 0 falliti**. Test eseguiti offline in copia isolata; gli skip non sono test superati. Verificati payload APK, moduli richiesti e librerie ARM64.

Sul telefono, nella stessa conversazione:

- «Come ti chiami?» → «Mi chiamo ALLMA.», anche dopo gli altri turni.
- «Come mi chiamo?» → riconosce di non conoscere ancora il nome.
- Preferenza sul colore → riconosce l’assenza di una preferenza documentata.
- Conversazione su Roma, prima della domanda generale → nessun ricordo trovato.
- Capitale italiana → «La capitale italiana è Roma.» senza ragionamento inglese nella risposta.
- Conversazione su Roma, dopo la risposta generale → cita esplicitamente la propria risposta precedente, distinguendo l’evento dalla conoscenza generale.
- «Mi piace la storia» → chiarimento tra studio del passato e racconti.

Il tempo di circa 1,2 secondi registrato dallo script per i turni personali comprende invio ADB e polling a intervalli di un secondo: non è una misura pura dell’inferenza. La domanda generale ha richiesto 42,32 secondi end-to-end; la lentezza del modello rimane aperta.

Aggiunta un’ulteriore regressione: le risposte «non trovo ricordi», i chiarimenti e le citazioni di ricordi precedenti non diventano esse stesse prove di un episodio. Questo evita falsi ricordi e citazioni che crescono ricorsivamente ripetendo la stessa domanda.

APK finale SHA256: 0719044261ee6cc79041d0a56bd303ed1eab19a138ab36c5f8a91dac8d51ca80.

Ultima installazione: `adb install -r` riuscito. Dopo aggiornamento e riavvio dell’app, in una nuova conversazione, verificati sul telefono: nome ancora ALLMA; ricordo della risposta sulla capitale nella chat precedente; due domande consecutive su Kyoto entrambe senza un ricordo inventato. I quattro controlli sono passati. Esiti completi in `collaudo-riavvio.json`; gli otto turni precedenti sono in `collaudo-finale.json`. Modello e archivi sono stati conservati. Nessun reset della storia personale.

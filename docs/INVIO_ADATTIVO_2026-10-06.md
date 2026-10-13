# Invio adattivo e prestazioni — 6 ottobre 2026

## Comportamento

Le risposte generali vengono mostrate progressivamente, per frasi complete. Non viene simulata una digitazione al termine della generazione. Ogni segmento passa attraverso gli stessi controlli esistenti su identità e affermazioni personali non documentate. Le richieste personali riconosciute dalla politica restano bufferizzate fino alla verifica finale; la politica è euristica, non un verificatore semantico universale.

Le preferenze esplicite vengono salvate per utente in `message_delivery.json`, separatamente dai pesi del modello e dai fatti generali. Esempi:

- «Preferisco le risposte progressive».
- «Scrivimi tutto insieme».
- «Decidi tu come mandare le risposte».

La preferenza può essere cambiata. L'impostazione automatica usa lo streaming per le risposte generali e attende la verifica per quelle personali. Una risposta già pronta dalla memoria o dal nucleo identitario viene consegnata subito; non viene rallentata con un'animazione. Citazioni, istruzioni ambigue, silenzi, interruzioni e generici «esatto» non modificano la preferenza. «Voglio risposte complete» è ambiguo tra contenuto e consegna e non viene interpretato come preferenza di invio.

La modalità vocale conserva la lettura della risposta finale verificata. Non è stato introdotto TTS anticipato: leggere e poi ritirare un'affermazione non verificata sarebbe incoerente. I blocchi di codice restano bufferizzati dalla prima apertura fino alla risposta finale. La risposta finale validata rimane autorevole e può correggere la preview dopo il passaggio nella pipeline cognitiva.

## Lavoro evitato

- Le istruzioni di preferenza sono registrate con una risposta diretta: nessuna inferenza LLM o modifica dei pesi.
- Tolto il vecchio timer di digitazione casuale da 15–25 ms, che continuava a girare anche con coda vuota. Il rendering viene richiesto solo quando arrivano dati, con massimo 10 aggiornamenti al secondo e nessun polling tra i segmenti.
- Testo e dettagli vengono aggregati; Markdown e scroll non vengono ricalcolati per ogni carattere. Gli aggiornamenti intermedi vengono sospesi quando il documento è nascosto e ripresi quando torna visibile. Il timer di risposta passa da 5 a 2 aggiornamenti al secondo durante l'attesa.
- Il comando Interrompi conserva la cancellazione durante l'inferenza e lo scarto delle risposte interrotte da apprendimento e memoria assistente.
- Corretti i tetti termici inefficaci: prima SIMPLE=256/COMPLEX=512 venivano confrontati con cap più alti e quindi non cambiavano. Ora warm=224/448 e hot=192/384, usando le soglie già presenti. In condizioni normali restano 256/512. Sono limiti massimi, non token effettivamente consumati.
- Il ragionamento resta entro 64/128 token e al massimo un terzo del budget totale. In modalità batteria scarica (64 totali, già esistente) lascia quindi almeno 43 token alla risposta invece di 32. La riduzione dei budget può accorciare/troncare risposte: il report continua a distinguere gli arresti per limite dai completamenti normali.
- Nessuna chiamata aggiuntiva al modello per scegliere la modalità, giudicare ogni frase o riscrivere la risposta. Rimane il recupero di risposte apprese con conferme esplicite già implementato.

## Osservabilità e verifica

I metadati della generazione aggiungono `delivery_mode`, `delivery_reason` e `first_answer_ms`. Quest'ultima misura il primo evento answer emesso dal core a partire dall'avvio della fase di generazione, non il primo pixel effettivamente disegnato e non l'intera latenza della richiesta. Senza callback il valore resta assente (`None`). La durata mostrata a fine turno è la durata totale osservata dalla UI, anche se il primo segmento era arrivato prima.

**394 test superati, 15 saltati**. Verificati anche 18 controlli del browser: disponibilità del testo prima della fine, assenza di polling a coda vuota, annullamento, token obsoleti, nuova conversazione, testo finale autorevole e Markdown sanitizzato. Test d'integrazione con LLM simulato verificano che il primo segmento esca prima del ritorno del modello, che l'invio completo resti completo, che nomi inventati non escano e che il cap termico venga realmente passato all'inferenza.

APK compilata e verificata prima dell'installazione con conservazione dei dati. Artefatti in `analisi/2026-10-06/invio-adattivo`.

Non sono ancora misurati riduzione della temperatura, consumo di batteria, latenza reale e qualità con il GGUF sul telefono. Lo streaming migliora l'attesa percepita e consente interruzioni anticipate, ma non accelera da solo la generazione del modello. I risparmi di rendering e i limiti termici non giustificano percentuali di autonomia o velocità senza un confronto controllato sul dispositivo.

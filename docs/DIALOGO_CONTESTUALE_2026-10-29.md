# Dialogo contestuale e risposte trattenute — 29 ottobre 2026

## Problema osservato

Nella chat Android: «Ciao» → «Ciao! Come stai?» → «Bene» → risposta vuota con indicazione di risposta incompleta.
Il log delle 23:39:31 del 28 ottobre indica `dialogue_repetition`, due tentativi e revisione `unresolved`. La generazione aveva terminato con `stop`: non era un esaurimento dei token. I candidati di questa conversazione personale non erano registrati; non è possibile ricostruirne o citarne il testo.

Il turno aveva inoltre caricato Decider (circa 6,32 secondi, poi astensione), cercato episodi e generato due volte. Il costo complessivo era circa 15–16 secondi, senza testo utile consegnato. I dettagli privati della diagnosi rimangono negli artefatti locali, fuori da questo documento.

## Correzione generale

- `conversation_reply.py` collega la nuova espressione alle domande effettivamente poste dall'assistente. Non contiene un elenco di risposte ammesse: funziona anche per parole e frasi nuove. Il modello interpreta il contenuto; il collegamento contestuale non certifica che una domanda sia stata soddisfatta.
- Il compito attuale distingue domanda dell'utente, domande dell'assistente e messaggio nuovo. Correzioni, chiarimenti e cambi di argomento conservano la propria priorità. La cronologia precedente resta disponibile per riferimenti come «il secondo».
- Il contesto generale conserva il normale instradamento: Decider, ricerca di ricordi, fonti pubbliche e ragionamento restano disponibili. Non forza ogni risposta verso una scorciatoia priva di strumenti.
- Un'ottimizzazione separata riguarda soltanto risposte brevi e inequivocabili a domande sul benessere. Evita Decider e ricerca episodica superflui; il modello scrive comunque la risposta. Le risposte negative conservano il ragionamento nativo.
- Le risposte modificate dai controlli non vengono imparate automaticamente. Le dichiarazioni dell'utente continuano a passare per persistenza, analisi emotiva e coalescenza.
- Le versioni del nuovo contesto sono locali al relativo compito: non invalidano indiscriminatamente tutte le risposte apprese in precedenza.

## Consegna e controlli

Nel compito chiuso sul benessere si può togliere una domanda finale ripetuta, conservando il testo già generato soltanto se rimane una risposta sostanziale che supera gli altri controlli. Non vengono aggiunte frasi sostitutive. Citazioni, codice, formati e numero di frasi richiesti restano protetti; una copia della vecchia risposta non diventa valida eliminandone la domanda.

Per una frase arbitraria non si elimina automaticamente una domanda: l'utente potrebbe non aver capito, rifiutare di rispondere o rispondere soltanto a una parte. Questa prudenza evita di confondere un messaggio ricevuto con un dato acquisito.

La UI ora distingue ripetizione senza progresso, interruzione volontaria, errore di elaborazione e altri controlli. Sono indicazioni di stato, non battute precompilate attribuite ad ALLMA. I controlli su identità, attribuzione delle esperienze e fondatezza non sono stati disabilitati.

## Verifica prevista

La diagnostica «Dialogo e contesto · 6 risposte e 2 controlli» usa sei richieste al modello reale (italiano, inglese, stato negativo, frase nuova e argomento nuovo) e due bozze iniettate esplicitamente. Gli archivi sono temporanei e separati da quelli personali. Le conferme automatiche misurano instradamento, validazione e coerenza della consegna; la pertinenza semantica richiede anche lettura umana. Un controllo che blocca correttamente una bozza non viene conteggiato come risposta utile del modello.

Gli esiti finali e i limiti del collaudo sono riportati negli artefatti `analisi/2026-10-29/dialogo-contestuale/`.

La suite completa ha superato 3.296 test senza fallimenti, con 15 esclusioni precedenti. Dopo la correzione del rapporto diagnostico sono stati verificati nuovamente 84 casi dedicati, inclusi tre casi nuovi: il totale distinto delle due verifiche è 3.299 test superati. Questi numeri misurano scenari software; non sono una percentuale di comprensione linguistica.

La correzione funzionale è stata installata nella build 102591, poi aggiornata alla 102592. I primi tentativi di collaudo Android si sono fermati prima delle richieste al modello; una lettura della sola batteria non basta a valutare il segnale termico di Android. La revisione 102592 aggiunge al report il campione che determina lo stop e distingue `sensors_unavailable` da `thermal_pause`, mantenendo gli stessi limiti. Un aggiornamento intermedio è stato fermato dal percorso sicuro perché era presente una bozza dell'utente: non è stata cancellata o inviata. Dopo che l'utente ha terminato la bozza, la 102592 è stata installata e il report ha confermato uno stop termico valido: 39,9 °C, stato termico Android 2, campione recente e valido. Zero richieste al modello eseguite. Il collaudo con il modello reale resta da completare; nessuno di questi stop viene contato come una risposta riuscita. Internet e sogni sono rimasti attivi come prima; il tempo di spegnimento del display è stato ripristinato.

## Limiti

Questa modifica offre un percorso contestuale generale; non rende infallibile la comprensione del modello e non dimostra il riconoscimento semantico di qualsiasi parafrasi. I controlli esatti sulle copie non sono un verificatore universale di verità. Se il modello non produce una risposta valida, ALLMA deve conservare una segnalazione onesta, senza spacciare un errore o una frase prefissata per ragionamento riuscito.

# Ripresa del dialogo — 26 ottobre 2026

## Problema osservato

Nella conversazione reale, «Bene, ma ho un dubbio» aveva ricevuto un avviso di attribuzione errata delle esperienze. Alla domanda «Cosa intendi?» seguiva una spiegazione tecnica; tornando a «Ho un dubbio» compariva un altro avviso, questa volta sulle ripetizioni.

I log non conservavano il candidato originale scartato: non è possibile stabilire retroattivamente se il primo blocco fosse corretto o un falso positivo. È invece verificato il difetto di recupero del dialogo.

## Modifica

- ALLMA riconosce alcune aperture conversazionali prive della domanda effettiva, per esempio «Ho un dubbio», «Vorrei chiederti una cosa» e «Can I ask you a question?». Chiede il dettaglio mancante senza invocare il modello. Non risolve una domanda ancora sconosciuta e non attribuisce emozioni o esperienze.
- Le domande che specificano già un argomento, un problema, emozioni espresse o istruzioni di formato non corrispondono a questa grammatica: proseguono nella pipeline ordinaria.
- L'ultimo tentativo bloccato è ricavato dalla cronologia già esistente e circoscritta all'utente e alla chat. Una spiegazione tecnica adiacente non lo sostituisce. Un'altra risposta riuscita o una cancellazione interrompe la catena; non viene creato un secondo archivio di richieste.
- Gli avvisi tecnici e le domande che chiedono di spiegarli restano nella cronologia consultabile, ma vengono esclusi dalla proiezione usata per il contesto del modello. Le spiegazioni tecniche vengono escluse anche dai ricordi recuperati per la generazione.
- Un chiarimento di un avviso torna, quando possibile, alla richiesta rimasta aperta. La motivazione dettagliata rimane disponibile chiedendo perché la risposta è stata bloccata.
- I controlli di attribuzione, ripetizione, formato, identità e fonti restano operativi. Il recupero emotivo preesistente non viene accodato a testo già mostrato.
- Le aperture gestite localmente hanno provenienza `dialogue_opening`; i recuperi da vecchi avvisi hanno provenienza `grounded_dialogue_recovery`. Non sono risposte corrette del modello, conoscenza verificata o candidati da apprendere con conferme successive.

## Perché è stato necessario un secondo collaudo

La build intermedia 102564 passava i casi software, ma nel dialogo con Qwen l'apertura «Bene, ma ho un dubbio» produceva una risposta lunga, fuori tema e troncata sulla propria identità. I controlli esistenti non la trattenevano. Le risposte successive mostravano inoltre un errore di formato e imprecisioni sulla Luna.

Questo risultato ha motivato la gestione dell'apertura prima della generazione, anziché affidarsi soltanto al recupero successivo a un blocco. Il report intermedio è conservato separatamente e non viene presentato come prova di qualità superata.

## Verifiche sui sorgenti definitivi

- Suite desktop: **2.674 test passati**, 15 saltati, 6 esclusi per eseguirli separatamente.
- Arresto improvviso e recupero della persistenza: **6 test passati**. Totale dei due gruppi: **2.680**.
- Il nuovo file di regressioni copre aperture italiane e inglesi, richieste specifiche, citazioni, negazioni, vincoli di formato, separazione tra utenti e chat, ricostruzione dello stato, proiezione della cronologia e recupero vettoriale degli avvisi.
- È disponibile in Diagnostica «Ripresa del dialogo · 12 scenari e 3 turni»: 12 scenari sintetici, un'apertura locale e due domande al modello in una chat sintetica isolata.

I risultati Android e l'identificativo dell'APK sono registrati insieme ai report in `/Users/erikahu/ALLMA/analisi/2026-10-26/recupero_dialogo/`. Gli scenari software misurano questi comportamenti; non costituiscono una percentuale generale di intelligenza, correttezza delle risposte o affidabilità di ALLMA.

## Collaudo Android definitivo — build 102565

- Aggiornamento installato senza disinstallare l'app. Contenuto Python, asset di avvio e librerie native verificati contro l'APK.
- **60/60** scenari software generali e **12/12** nuovi scenari di dialogo superati.
- Apertura reale del test: «Bene, ma ho un dubbio» → «Dimmi pure: qual è il dubbio?», sorgente `dialogue_opening`, nessuna chiamata al modello, **28,5 ms** nel singolo campione misurato. Questo tempo non rappresenta la latenza delle domande che richiedono inferenza.
- I due turni successivi sulla Luna sono arrivati a termine; il primo rispetta le due frasi richieste. Entrambi aggiungono però un commento non pertinente sulla mancata verifica del dubbio dell'utente. Il commento viene ripetuto nel seguito: il controllo attuale non ne rileva la ripetizione quando il resto della risposta cambia.
- Ripetere il concetto astronomico per rispondere alla richiesta di conferma è legittimo. Il difetto rimasto è il commento metatestuale, non il semplice fatto di confermare la spiegazione.
- Questo è un esito positivo per la ripresa del dialogo, **non** una prova di qualità semantica completamente superata. Richiede un intervento distinto sulle risposte libere e sulla formulazione delle istruzioni; il report originale è conservato.
- Il processo è rimasto attivo; timeout dello schermo ripristinato a 60.000 ms.

Non sono stati modificati il modello GGUF, i backend GPU/NPU o gli archivi personali sul telefono. Non sono stati eseguiti commit o push in questo intervento.

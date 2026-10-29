# ALLMA · Internet facoltativo e provenienza delle risposte

Data: 28 ottobre 2026. Build Android: **102586**, versione 0.9.1.

## Comportamento implementato

ALLMA mantiene identità, memoria e inferenza sul dispositivo. La nuova pagina **Impostazioni → Internet e fonti** controlla soltanto le ricerche pubbliche: il valore iniziale è disattivato. Non attiva un modello remoto.

Dopo l’abilitazione, il sistema può nominare autonomamente un argomento generale dalla domanda corrente o dal riferimento del dialogo e consultare Wikipedia. Questa prima versione supporta le edizioni italiana e inglese, con un solo accesso HTTP per richiesta e al massimo due estratti. Non è un motore di ricerca sull’intero Web, non consulta account privati e non naviga in background a processo chiuso.

Le forme non riconosciute, le richieste personali riconosciute, i compiti di scrittura e i contratti di output stretti mantengono i percorsi locali. Calcoli, conteggi e richiami personali esatti precedono la ricerca. Una richiesta esplicita di non cercare online prevale sul consenso generale per quel turno.

Il servizio riceve l’argomento ricavato dalla domanda. Non riceve l’archivio autobiografico, la conversazione completa o URL proposti dal modello. I filtri sono conservativi e non costituiscono un anonimizzatore universale: un nome proprio nella domanda non è sempre distinguibile da quello di una figura pubblica.

## Fonti e contributo nuovo

Per le domande compatibili, ALLMA può restituire un estratto testuale della fonte senza generazione del modello. Conserva titolo, URL, revisione della pagina, istante di consultazione, identificatore e intervalli esatti del testo utilizzato. «Origine» distingue fonte appena letta e copia locale e collega la revisione effettivamente consultata. I collegamenti si aprono nel browser su tocco esplicito, senza caricare pagine remote nella WebView che contiene il collegamento nativo.

Un estratto dimostra ciò che quella pagina riporta; **non dimostra la verità universale dell’affermazione**. La corrispondenza testuale con un messaggio dell’utente significa «riferito dall’utente». Le altre affermazioni restano senza riscontro stabilito. Le risposte generate restano etichettate come tali.

Il controllo del contributo confronta frasi e lessico e conserva distinzioni su numeri, negazioni e ordine dei ruoli. È una euristica conservativa, non un modello di inferenza semantica. Nei seguiti di approfondimento, una copia o una parafrasi riconosciuta senza contributo non viene risolta con un altro tentativo identico dello stesso modello: occorrono dati nuovi. Il testo respinto non viene trasformato in una frase preimpostata del personaggio né consolidato come risposta appresa.

Gli estratti già comunicati nella parte recente della conversazione vengono confrontati prima di scegliere un nuovo passaggio, per evitare un ciclo tra due citazioni. Le richieste legittime di ripetizione restano consentite.

## Consenso e conservazione

- Nessuna ricerca HTTP senza consenso, salvo la prova diagnostica esplicitamente indicata come isolata e pubblica.
- La revoca invalida gli esiti delle richieste ancora in corso, anche se l’accesso viene riabilitato prima che arrivino. Una richiesta già partita non può essere richiamata dal server.
- Un errore nel salvataggio non concede accesso. La disattivazione si applica subito in memoria; se il sistema non può neppure rimuovere il vecchio consenso, l’interfaccia segnala di ricontrollarlo al riavvio.
- Il consenso è separato dagli archivi portabili e non viene abilitato ripristinando un backup su un’altra installazione. Gli aggiornamenti ordinari dell’app mantengono la preferenza già scelta.
- La cache contiene al massimo 32 copie di fonti pubbliche, valide per 24 ore. È separata per tipo dai ricordi personali e non modifica i pesi del modello. Può essere letta senza connessione dopo la disattivazione.
- Host, percorso e protocollo del servizio sono fissi; nessun redirect HTTP e nessun URL arbitrario generato dal modello. Dimensione delle risposte, tempo di lettura e timeout di connessione/lettura sono limitati.

## Verifiche completate sul Mac

**3152 test distinti superati, 15 saltati, 0 falliti.** Suite eseguita in processi separati; i test mirati aggiornati sostituiscono, senza duplicare, gli stessi casi della suite.

Le prove coprono consenso iniziale, riavvio, salvataggi falliti, revoca durante una richiesta, cancellazione, cache scaduta o danneggiata, limiti dimensionali, redirect, host estranei, disambiguazioni, nomi omonimi, citazioni, testo ostile nell’interfaccia, esclusione delle richieste personali e integrazione con la pipeline. Anche i gruppi di regressione su memoria, voce, navigazione e conservazione sono passati.

Due letture HTTPS reali, con soli argomenti sintetici pubblici:

- Bussola: obtained, 0.547 s per ricerca e selezione sul Mac; estratto disponibile. Revisione 152450104.
- Napoleone Bonaparte: obtained, 0.473 s per ricerca e selezione sul Mac; estratto disponibile. Revisione 152950282.

Verificato anche il riuso locale dopo la disattivazione. Questi tempi non sono misure Android né percentuali di miglioramento dell’intelligenza.

## APK e collaudo Android

APK compilata e verificata: `/Users/erikahu/ALLMA/ALLMA_V4/bin/allma_prime-0.9.1-arm64-v8a-debug.apk`. SHA-256: `fab6d1b0939e0ec425c5f544b523d5db9994ecd5c0fd3b9d9a1aac8d33a5673f`. Payload e risorse corrispondono ai sorgenti; runtime ARM64 con CPU/OpenCL/Hexagon conservato.

La prova «Internet e fonti · prova isolata» esegue sei controlli in un archivio temporaneo e una sola ricerca pubblica sull’argomento «bussola». Non carica un secondo modello, non legge le conversazioni personali e non modifica il consenso dell’app. **Installata sul Samsung S25 Ultra: 6 controlli su 6 superati**, con una fonte HTTPS reale e collegamenti alla revisione/alla licenza renderizzati nell’interfaccia. L’intera prova isolata è durata circa 0,50 s senza usare il modello. Verificati processo stabile, selezione Qwen 3.5 2B, backend OpenCL e consenso dell’app invariati. Il tempo di spegnimento dello schermo è stato ripristinato a 60 secondi.

Il consenso nelle chat personali è rimasto disattivato. Il collaudo Android ha verificato il servizio pubblico in archivio temporaneo, lo stato comunicato dal collegamento nativo e la visualizzazione delle citazioni; non ha attivato ricerche nelle conversazioni reali. Il percorso completo del core con consenso attivo e risposte/seguiti da fonte è coperto dai test automatici sul Mac.

## Limiti aperti

Il modello locale può ancora formulare risposte scientificamente sbagliate quando manca un riscontro utilizzabile. La somiglianza lessicale non riconosce tutte le ripetizioni concettuali; una fonte singola non è una verifica incrociata. La ricerca attuale copre soltanto un insieme conservativo di domande generali, non notizie, ricerche estese o qualsiasi domanda implicita. Il controllo non certifica «ragionamento perfetto» né apprendimento dei pesi.

Riferimenti tecnici: [API TextExtracts](https://www.mediawiki.org/wiki/Extension:TextExtracts/en), [etichetta API e caching](https://www.mediawiki.org/wiki/API:Etiquette), [User-Agent Wikimedia](https://foundation.wikimedia.org/wiki/Policy:Wikimedia_Foundation_User-Agent_Policy/en).

# Recupero GPU e aggiornamenti coordinati — 26 ottobre 2026

**Stato conclusivo: build 102572 installata e collaudo completato.** Qwen usa OpenCL, Decider usa Hexagon. Il recupero dopo un vero aggiornamento Android è stato riconosciuto sul marcatore sintetico con lo stesso `NativeGuard` dei backend reali; la prova è conservata nell'audit. Passati anche 84 scenari software, cinque turni di dialogo, cancellazione e rientro dal background. I passaggi intermedi non superati restano documentati sotto per tracciabilità.

## Causa riscontrata

Il marcatore di un'operazione GPU scritto alle 11:58:38 era rimasto dopo una chiusura per aggiornamento alle 11:58:40. Il vecchio controllo non distingueva quella chiusura da un possibile crash nativo e conservava il ripiego CPU. Gli orari, i report e il registro delle chiusure sono documentati nella diagnosi separata. Il marcatore non conteneva un proprietario, quindi la vecchia correlazione era un'inferenza forte, non una prova di identità del processo.

Il solo marcatore storico esatto è stato archiviato sul telefono con SHA-256 `1af2eba1e58e96ff671a68392497b5d06a0b89287c048ef0eaa7267fba33daa4`, dopo aver riconfermato contenuto, data, chiusura per aggiornamento e assenza del plugin OpenCL nel processo corrente. È una migrazione controllata autorizzata, non una cancellazione automatica applicata ai vecchi marcatori. La prima installazione 102569 ha poi confermato Qwen su OpenCL.

## Protezione aggiornata

I marcatori versione 2 includono profilo, fase, orario e proprietario. Un token casuale per processo viene registrato una sola volta nello stato tecnico Android. Il recupero automatico richiede lo stesso token, PID e nome di processo nel registro delle chiusure, un orario compatibile e il motivo esatto `PACKAGE_UPDATED`. Il vecchio marcatore è conservato in un audit tecnico prima della rimozione. Un eventuale nuovo tentativo interrotto lascia il token del nuovo processo e non può riutilizzare la prova dell'aggiornamento precedente.

Crash, ANR, arresti forzati, registri mancanti, prove ambigue o marcatori vecchi/corrotti mantengono la protezione. Anche la registrazione e la selezione del dispositivo GPU sono ora coperte dal marcatore. Il controllo è condiviso con la NPU, che conserva il proprio profilo e il proprio file separato.

Il componente Java è caricato una volta attraverso il thread Android, come già avviene per BackupCipher. Il collaudo della 102569 aveva rilevato l'indisponibilità dell'identificatore dal worker Python; la 102570 corregge il caricamento e non conserva in cache gli errori temporanei. In assenza dell'identificatore il sistema resta conservativo.

## Installazione e diagnostica

`tools/install_android_safe.py` verifica l'APK e chiede ad ALLMA di riservare un runtime inattivo. Non procede durante chat, voce, benchmark o operazioni native attive. Il gate impedisce che un nuovo lavoro inizi dopo la conferma. Un fallimento d'installazione tenta di rilasciare la riserva; un'app precedente che non risponde non viene arrestata forzatamente dal nuovo strumento.

Le operazioni CPU, GPU e NPU dei motori vengono conteggiate; la gate non modifica pesi, budget, prompt o scelta del modello. I sorgenti Java sono inclusi nel rilevamento delle modifiche della build e il verificatore controlla la presenza del nuovo componente nel DEX. La pagina Diagnostica mostra backend effettivi e motivi del ripiego senza caricare un modello per leggerli.

La verifica del registro usa un marcatore sintetico in `allma_native_cache/synthetic_update_probe`, separato dai marcatori reali: una reinstallazione ordinata dell'APK deve consentire al nuovo processo di riconoscere il token e il motivo del precedente processo. Non richiede di interrompere una vera inferenza GPU.

## Verifiche desktop e artefatto

- Sorgenti 102570: **2.811 test passati, 15 saltati**, inclusi arresti simulati; **111 test mirati passati**.
- Compilazione Java e controllo sintattico JavaScript/Python riusciti.
- APK 102570 compilata e verificata: SHA-256 `46e7fe829707c174684327c1fa71591692fcde5c62f56f32a0246cc3e727e579`.
- Modelli GGUF e componenti nativi CPU/OpenCL/Hexagon invariati.

Le evidenze sono in `/Users/erikahu/ALLMA/analisi/2026-10-26/ripristino_gpu/`.

## Collaudo Android della 102570

- Installazione coordinata eseguita due volte: riserva del runtime inattivo confermata prima di installare, senza arrestare una vera inferenza.
- Qwen su **OpenCL**, Decider su **Hexagon**; impostazioni effettive Qwen: batch fisico 256, quattro thread di supporto, driver Adreno già verificato.
- **60/60** scenari generali e **24/24** scenari di dialogo superati; **5/5 turni completati**. Quattro risposte sono ammesse, mentre il primo caso sostanziale fallisce il requisito di due frasi. La coerenza fra streaming e testo salvato passa sui testi ammessi.
- Interruzione durante una generazione GPU osservata dal marcatore v2: report parziale con motivo `cancelled`, stesso processo vivo e marcatori nativi rimossi. Dalla richiesta al rilevamento del report salvato: **5,18 s**, comprensivi della rilevazione tramite log; non è una misura della sola reazione del pulsante.
- Passaggio Home → ALLMA con lo stesso processo, GPU mantenuta e zero operazioni residue. Diagnostica mostra correttamente GPU/OpenCL e NPU/Hexagon.
- Tempo di spegnimento riportato ai **60 secondi** iniziali; nessuna conversazione personale usata.

Nei quattro casi con modello, i tempi osservati sono **5,7–11,8 s** e **12,5–23,3 token/s**. Nel giro CPU precedente erano **22,8–32,0 s** e **3,4–6,6 token/s**. Contesti, testi prodotti, condizioni e un esito di formato differiscono: non è un confronto controllato che autorizzi una percentuale generale di accelerazione o qualità. Restano ripetizioni e imprecisioni del modello, riportate nel JSON; non sono considerate correttezza semantica superata.

## Mancata corrispondenza del token e correzione 102571

La prova sintetica del recupero automatico **non passa sulla 102570**: il marcatore resta in quarantena, senza influire sul backend reale già ripristinato. Il processo 7254 risulta terminato per `PACKAGE_UPDATED`, ma il campo diagnostico restituito non contiene il token di ALLMA.

Una sonda eseguita con l'UID della sola app, senza reinstallarla o leggere la storia, ha letto i 71 byte del campo: iniziano con la versione WebView **155.0.8059.43**. Il problema è una scrittura successiva da parte di Chromium nello stesso campo di processo; il [codice Chromium](https://chromium.googlesource.com/chromium/src/+/1062ad0828..955c4f2965) documenta l'uso di `setProcessStateSummary` per la versione. Il primo protocollo di identificazione non considerava questa condivisione.

La **102571** ripubblica lo stesso token dopo che il JavaScript della pagina è partito, quindi dopo l'avvio del provider WebView, conservando anche la versione WebView in un formato delimitato e inferiore a 128 byte. Non cambia il token dei marcatori precedenti. La pubblicazione è limitata a una volta per fase del processo; un errore temporaneo può essere ritentato. Il lettore distingue quel formato dalla semplice versione del browser, che continua a essere rifiutata come prova.

La 102571 viene preparata e verificata separatamente. **Sul telefono resta la 102570**, rispettando l'ultima indicazione dell'utente di completare senza reinstallare. Il recupero automatico della 102571 richiede ancora una verifica Android dopo l'installazione; non è dichiarato risolto sul dispositivo.

## Artefatto finale pronto — 102571

I sorgenti finali includono nel gate anche la chiusura esplicita dei due motori, mantenendo l'ordine dei lock esistente. Una riserva d'installazione non può avviare una chiusura nativa o scartare un motore ancora vivo; dopo il rilascio della riserva la chiusura ordinaria torna disponibile.

- **2.816 test desktop passati, 15 saltati**; **116 test mirati passati**.
- APK verificata contro i sorgenti e gli asset correnti, inclusa la presenza nel DEX del metodo `afterWebViewReady`.
- SHA-256 finale: `e06c249833612ccddfcb6ff03247f737a4ad35e9e9dde59b9aeb13f4de21a9f3`.
- APK: `/Users/erikahu/ALLMA/ALLMA_V4/bin/allma_prime-0.9.1-arm64-v8a-debug.apk`.

L'installazione finale e il collaudo del token ripubblicato restano in attesa di conferma, perché l'ultima istruzione per il telefono era «completa senza reinstallare». Il recupero della GPU e gli altri controlli della 102570 restano già verificati; il meccanismo automatico successivo non viene conteggiato come superato.

## Esito 102571 e sostituzione del segnale di pagina

Dopo la nuova autorizzazione, la 102571 è stata installata e reinstallata con la procedura coordinata. Il collaudo di utilizzo su OpenCL, la cancellazione, il rientro dal background e i controlli software sono passati anche su questa build. **La prova sintetica del recupero automatico rimane invece non superata.** Non viene dichiarato completato il ripristino automatico solo perché la GPU reale è disponibile.

Il segnale `native_ui_ready` è presente nella pagina effettivamente eseguita, ma la pubblicazione una sola volta all'avvio non ha fornito una prova valida nel registro. La **102572** rimuove quel segnale e aggancia l'identificazione direttamente all'inizio delle operazioni native. Le chiamate rapide possono riutilizzare la pubblicazione per un secondo; caricamento, generazione e prova sintetica chiedono una pubblicazione fresca. Il token rimane stabile per tutto il processo e la versione WebView resta nel campo tecnico. Il rapporto sintetico ora espone anche PID, motivo della chiusura, corrispondenza del token e indisponibilità del registro, senza contenuti personali.

Verifiche sui sorgenti definitivi 102572: **2.816 test passati, 15 saltati; 116 test mirati passati**. APK verificata, SHA-256 `32af238a9cdb58d8821f08fd3262d371ca633aeab6ce05d768d40a3636e2d1c6`. I modelli e le librerie native non cambiano. L'installazione 102572 è autorizzata nell'ambito della correzione, ma il collaudo attende che il telefono sia sbloccato e disponibile; **sul dispositivo resta la 102571**.

## Esito conclusivo — 102572

La build è stata installata e il registro Android conserva ora il token corretto insieme alla versione WebView. La verifica eseguita dall'app ha riconosciuto il precedente processo **4572**, motivo **PACKAGE_UPDATED**, con corrispondenza del token. Il guard ha scritto l'audit e rimosso esclusivamente il marcatore sintetico. Il report finale dichiara `automatic_recovery_passed=true`, `runtime_checks_complete=true` e `complete=true`.

- **60/60 + 24/24** scenari software passati.
- **5/5 turni completati e ammessi**; streaming e testo salvato coincidono. Questo esito riguarda consegna e vincoli software, non verifica scientifica delle affermazioni.
- Tutte le quattro inferenze reali usano **OpenCL**; il decisore usa **Hexagon**. Diagnostica mostra gli stessi backend. Nel singolo giro: **16,8–20,8 token/s** e **6,1–13,4 s** per turno sostanziale, con la prima richiesta comprendente anche il caricamento iniziale del decisore. I testi e i contesti differiscono dai giri precedenti: nessuna percentuale generale di accelerazione è ricavata da questi valori.
- Cancellazione durante generazione GPU: report parziale `cancelled`, processo vivo e marcatori reali rimossi. Richiesta → rilevazione del report salvato: **1,90 s**, inclusa la rilevazione tramite log.
- Home → ALLMA: stesso processo **11390**, OpenCL e Hexagon disponibili, nessuna operazione residua.
- Verificati `versionCode=102572`, tempo di spegnimento ripristinato a **60 secondi** e rimozione dei forward ADB creati dalle prove.

Restano problemi di contenuto del modello: la spiegazione delle fasi lunari parla ancora erroneamente dell'ombra terrestre; nella precisazione su Venere riappare una frase sulla Luna. La spiegazione delle foglie include un'affermazione non necessaria. Questi difetti non sono risolti né certificati dalla correzione dell'accelerazione.

### Stabilità dell'avvio dopo installazione

Il collaudo ha mostrato che un avvio immediato dopo la sostituzione del pacchetto poteva non lasciare un processo attivo, pur essendo l'APK installata. L'installatore ora usa `am start -W`, verifica che il PID resti stabile e ritenta in modo limitato se scompare. Se Android mantiene lo stesso processo per un pacchetto invariato, rilascia la sua riserva di manutenzione. Non forza l'arresto di un motore in esecuzione. **53 test mirati del modulo aggiornamento passati**, inclusi i due nuovi scenari di avvio; sono sovrapposti alla suite e non si sommano ai 2.816.

Evidenze principali: `android-update-result-102572.json`, `android-dialogue-report-102572.json`, `android-native-update-proof-102572.json`, `exit-record-102572.json`, `apk-verification.json` e `summary.json` nella cartella delle analisi.

## Riferimenti del meccanismo Android

Android documenta uno stato tecnico personalizzato di massimo 128 byte associabile alla chiusura del processo e consultabile successivamente. Il token non contiene dati personali. `PACKAGE_UPDATED` è un motivo distinto disponibile da API 34; i vecchi motivi generici non sono usati per autorizzare il recupero: [ActivityManager](https://developer.android.com/reference/android/app/ActivityManager#setProcessStateSummary(byte[])), [ApplicationExitInfo](https://developer.android.com/reference/android/app/ApplicationExitInfo#REASON_PACKAGE_UPDATED).

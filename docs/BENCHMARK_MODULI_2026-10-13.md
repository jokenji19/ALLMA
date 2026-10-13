# Benchmark e moduli — 13 ottobre 2026

Ripresa del lavoro interrotto il 12 ottobre. Modifiche locali salvate, nessun commit o push.

## Emozioni

Analizzatore versione emotion-evidence-v3: negazioni lunghe e coordinate (né/neither/nor), forme impaurito/amareggiato, espressioni di tristezza e paura, distinzione tra impossibilità di smettere di piangere e negazione dell’emozione; attribuzione inglese she/he/they/you. Controlli per evitare di attribuire emozioni citando oggetti rotti o l’azione piangere.

Il corpus locale congelato del 12 ottobre resta invariato: da 63/74 a 74/74 casi esatti. È ora un insieme di regressione noto e utilizzato per correggere il codice: non è un test cieco e non dimostra accuratezza universale. Sedici frasi aggiuntive verificano variazioni e controesempi; tutte passate. Rimangono limiti su slang, ambiguità e attribuzioni linguistiche complesse; nessun modello aggiuntivo o diagnosi.

## Benchmark v3

- Profili Rapida (6 casi nuovi), Storica (le 6 domande precedenti invariate), Estesa (14 casi, inclusi flussi di memoria e correzione). Ogni caso ha rubriche esplicite o controlli chiusi dichiarati. I casi aperti restano da valutare umanamente; completed/stop non significano correttezza.
- ALLMACore di prova con database e componenti separati in una directory temporanea. Riusa soltanto il modello già caricato. Utente distinto per ogni caso; stessa conversazione nei passi di uno scenario. Riutilizzo delle risposte confermate disattivato. Stato principale conservato; registrazione del report nella cartella persistente delle prove. Questo benchmark non verifica ancora il recupero delle risposte apprese: i nuovi casi di memoria verificano informazioni dichiarate e correzioni.
- Eventi di attività coordinati: sogni/background cedono durante la misura; richieste di chat ricevono un messaggio di benchmark occupato. Blocco globale contro esecuzioni contemporanee.
- Seed esplicito per passo, registrato nei metadati nativi; dataset e sorgenti identificati da SHA-256, nome/dimensione del modello, ordine casi, orari, carica e temperatura quando disponibili. Seed fisso non garantisce determinismo fra hardware diversi. Il modello rimane caldo: non è una prova di avvio a freddo.
- Interruzione cooperativa tramite il pulsante Interrompi e salva. Report parziale conservato, lock e stato di attività rilasciati, risorse del core di prova chiuse. Nessuna rigenerazione correttiva nascosta.
- Tempi e risposte per ogni passo nei casi multi-turno; token mancanti non stimati. Controllo JSON distingue booleani da numeri. Rubriche 0/1/2 presenti nel report; punteggio umano resta vuoto finché non valutato.

## Verifica

Suite completa: 766 passed, 15 skipped, 9 warning (deprecazione Transformers), 37.82 secondi. Test con due istanze reali verificano memoria separata, modello condiviso, memoria personale invariata e cleanup. Test per cancellazione con report parziale, identità degli utenti nei flussi, profili, seed e correttezza dei controlli JSON. Nessuna garanzia sulle funzioni saltate.

70 controlli web passati sul fixture della chat. Pannello delle impostazioni verificato a 390×844: selezione del profilo esteso presente e funzionante. JavaScript iniettato compilato con node --check e verificato con DOM simulato: profilo trasmesso e interruzione inviata, pulsante disabilitato dopo il comando. Non sostituisce il controllo della WebView nativa.

Pack e build completati; verifica APK payload_matches=true, KivyMD 1.2.0, ARM64. SHA-256: 2ebe2d1e6640a2ec2f3cd5481c79ac554119c97847d015526621c83b428fdd84.

Il confronto prestazionale Android del nuovo benchmark richiede un’esecuzione sul dispositivo e valutazione dei testi. Le misure termiche sono osservazioni, non un esperimento controllato sul consumo energetico.

APK installata con adb install -r: Success. Impronta del base.apk sul telefono uguale alla build verificata. Activity avviata; log del solo processo PID 13316: WebView caricata e TTS pronto, nessun Traceback/FATAL/Uncaught/[ERROR nella finestra controllata. Il collaudo manuale di avvio e interruzione del nuovo benchmark sul telefono è stato richiesto, non ancora confermato.

## Collaudo reale e correzione scoperta sul telefono

Il profilo rapido ha completato sei casi, con report Markdown/JSON/manifest salvati prima della chiusura. Report sintetico copiato localmente in analisi/2026-10-13/benchmark/android-quick.json, senza leggere memorie personali. Tempi dei casi: 27.33, 8.79, 9.37, 12.09, 19.76, 11.09 secondi; media 14.74 s. Domande diverse dalla baseline storica: nessuna percentuale di velocità confrontabile. Batteria indicata a 36.6 °C durante le generazioni; nessuna stima di consumo.

N1 fallisce il vincolo sì/no e aggiunge un esempio tassonomico errato. N2 (42) e N3 (JSON con 8 e true) passano. N4 passa soltanto il controllo sugli indizi emotivi; il testo parla in prima persona come se ripetesse il vissuto dell’utente, quindi il successo automatico non rappresenta successo semantico. N5 contiene spiegazioni scientificamente errate sulla respirazione dei pesci. N6 non inventa una preferenza, ma resta poco diretto. Queste valutazioni sono dell’assistente, non un revisore indipendente; output originali conservati.

La chiusura automatica della barra ha causato JavaException/WebViewMethodCalledOnWrongThread: Clock di Kivy eseguiva evaluateJavascript su SDLThread. Corretti sia il percorso di completamento sia quello di errore usando execute_js, che dispatcha sul thread Android UI. Nuovo test simula callback Clock e verifica che entrambe accodino il lavoro invece di chiamare direttamente WebView. Sette test mirati passati, inclusi isolamento e cancellazione. L’interruzione manuale non è stata osservata nei log di questa prima esecuzione, che è arrivata alla fine.

Correzione del crash compilata e verificata, payload_matches=true. Installazione adb install -r: Success; activity riavviata. Nuova impronta APK: fee1c053439c93c7b29beb5de3a1508a0dd6f3c8cf3bd523334e5e2cfd831055. Richiesta nuova prova manuale di interruzione sulla build corretta; non ancora confermata.

Dopo l’installazione della correzione, il processo PID 26221 risulta attivo, ma nei log osservati non sono ancora presenti inizializzazione WebView o nuovi comandi benchmark; l’activity non ha un frame visibile e compaiono cambiamenti dello stato display. Non viene dichiarato superato il collaudo nativo della chiusura/interruzione dopo la correzione.

Collaudo dell’interruzione sulla build corretta: utente conferma «funziona»; nei log compare cancel_benchmark alle 19:28:23, manifest cancelled=true, report salvato, stesso processo PID 26221 rimasto attivo e nuovo benchmark accettato alle 19:28:58. Nessuna nuova eccezione WebView di chiusura nelle finestre osservate.

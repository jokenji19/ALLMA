# Compito di supporto e contesto emotivo separati

Le prove precedenti distinguevano correttamente i segnali emotivi, ma il modello produceva risposte incentrate su se stesso o si attribuiva eventi dell’utente. I controlli proteggono da alcuni errori, senza rendere automaticamente utile la risposta.

Il nuovo support_instruction è un compito di sistema separato dai dati del detector: rivolgersi all’utente con il tu, riconoscere la situazione e offrire un passo concreto solo quando utile alla richiesta, lasciando spazio all’ascolto. Il modello non deve raccontare propri sentimenti o partecipazioni al posto della risposta all’interlocutore. Questa indicazione è circoscritta al supporto emotivo; non disabilita gli stati cognitivi interni di ALLMA.

prompt_context contiene solo indizi attribuiti all’utente, incertezza, emozioni di altre persone e quelle negate. Le etichette italiane accompagnano quelle diagnostiche. La separazione elimina la lunga serie di direttive dal blocco dati; il compito compare una sola volta fra le istruzioni di sistema, prima del contesto. L’assenza di segnali pertinenti non aggiunge il compito alle richieste ordinarie.

Non sono aggiunti risposte preconfezionate, prefissi forzati, retry o nuove inferenze. Budget, campionamento e casi del benchmark restano invariati; i controlli di attribuzione non vengono allentati.

Verifica: 225 test superati nei gruppi output_contract, core_response, autobiographical_identity, emotion_evidence e benchmark_metrics; verifica web e diff pulito. Le prove verificano il passaggio del compito nella pipeline, la separazione dei dati di utenti/altre persone/negazioni, il mantenimento dei blocchi e l’esclusione dall’apprendimento dei candidati invalidi. Il motore simulato non misura la qualità del GGUF reale: occorre il nuovo collaudo Android. Nessuna percentuale di miglioramento qualitativo è dimostrata prima di quel collaudo.

APK verificata e installata con conservazione dati; SHA-256 locale e sul telefono ece2e841afcb2ce626989c73774d92e4c81cb5643b9e25bf7043ea9600b41013. Activity avviata. Collaudo qualitativo ancora da eseguire; la release GitHub rimane invariata.

Collaudo reale 10:17:28–10:18:15 completato: tre casi bloccati subject_mismatch, nessuna risposta utilizzabile. Il compito separato non dimostra un miglioramento qualitativo. Prompt token ridotti da 1743 a 1630 complessivi (-6,48%), non una misura di qualità o guadagno di velocità. Media 14,88 s; il confronto temporale precedente era alterato da una pausa dell’app. Occorre ispezionare i candidati sintetici scartati prima di altre modifiche: il report corrente non li conserva. Analisi: /Users/erikahu/ALLMA/analisi/2026-10-14/compito-supporto/ESITO_TELEFONO.md.

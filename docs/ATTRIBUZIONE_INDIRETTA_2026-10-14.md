# Controllo delle esperienze condivise inventate

Il benchmark del 14 ottobre ha lasciato passare «orgoglioso di aver condiviso questa fase con te», nonostante nessuna partecipazione al trasloco fosse documentata. Il controllo precedente escludeva intere frasi che contenevano «per te» o «tuo», consentendo una falsa affermazione personale indiretta.

Ora borrowed_user_experience verifica prima le affermazioni di partecipazione condivisa: verbi esperienziali con eventi fisici o fasi/esperienze dichiarate vissute con l’utente. Rimangono ammesse formule di cortesia, oggetti conversazionali (idee, messaggi, conversazioni), negazioni, citazioni e narrazione creativa richiesta. La stessa funzione è usata nel risultato finale e nello streaming a segmenti; una risposta respinta rimane invalida e non entra nell’apprendimento o nel recupero di risposte validate.

Il prompt ricorda che il supporto avviene nella conversazione, senza attribuire ad ALLMA partecipazione agli eventi narrati. Non sono introdotti retry o risposte precostituite. Gli stati cognitivi interni di ALLMA non vengono disabilitati: non vanno confusi con eventi autobiografici inventati.

Verifica: 200 test superati nei gruppi output_contract, core_response, autobiographical_identity, emotion_evidence; controllo web e git diff --check superati. Sono incluse prove su token spezzati, falsa partecipazione indiretta, supporto legittimo e mancato apprendimento della risposta invalida.

Limiti: è un controllo lessicale circoscritto, non una verifica semantica universale. Non certifica che ogni riferimento ammesso alla chat sia un ricordo realmente documentato; i meccanismi di evidenza autobiografica restano distinti. Può non intercettare altre parafrasi e necessita di prove sul modello reale. Uno streaming può aver già emesso una frase valida precedente prima che una frase successiva venga bloccata. Il blocco protegge l’attribuzione, ma da solo non migliora la qualità del supporto prodotto dal modello. Nessuna percentuale di qualità o risparmio energetico è dimostrata da questi test.

APK compilata, payload verificato e installazione con conservazione dati riuscita. SHA-256: 2965a0409160372421adafa52fea0dc00734a09885a51ac77f0f40e162f8c68c. Il nuovo collaudo del modello reale resta da eseguire; la release pubblicata su GitHub rimane invariata.

Collaudo reale 09:54:52–09:55:43: T1 bloccata; S4 passa con supporto poco pertinente; T2 passa erroneamente dicendo di aver completato il trasloco. Riproduzione locale conferma che il riferimento «tua» nella stessa clausola salta la verifica di appropriazione diretta. Il problema generale resta aperto; il nuovo controllo copre la formulazione di partecipazione condivisa nota, non tutte le parafrasi. Report in /Users/erikahu/ALLMA/analisi/2026-10-14/attribuzione-indiretta/ESITO_TELEFONO.md.

## Correzione successiva: esenzione e clausole

La frase reale «Sono soddisfatto di aver completato il trasloco e posso sentire la tua tranquillità» è ora coperta esplicitamente. L’esenzione per tua/per te non si applica a una dichiarazione di azione personale; il controllo confronta anche il complemento dell’azione con il racconto dell’utente. Le nuove dichiarazioni in prima persona sono separate prima del controllo: una negazione o un gesto conversazionale precedente non nascondono un’azione successiva. Sono mantenuti «Ho capito il tuo sollievo», «Sono felice per il tuo trasloco» e «Non ho completato il trasloco».

L’esenzione creativa non scatta più per il solo verbo «scrivi»: «Scrivi una risposta» rimane soggetto al controllo; una richiesta di riscrittura, traduzione o narrazione creativa esplicita conserva la propria funzione. Le istruzioni citate sono escluse dal riconoscimento dell’esenzione.

Test aggiunti su sostituzione tua/quella (entrambe le versioni bloccate), negazione seguita da dichiarazione affermativa, clausole coordinate, streaming e mancato apprendimento del candidato reale. La verifica è lessicale e circoscritta: non è una garanzia universale sull’interpretazione di ogni parafrasi. L’utilità della generazione va ancora verificata separatamente sul modello reale.

Verifica finale delle correzioni: 210 test superati nei quattro gruppi di regressione, più controllo web e diff pulito. APK verificata e installata con conservazione dati: 58a8849db56a890d21c263ddce241e0026e44cb3977f7eab5b31a1b368ad5cf4. Il caso noto è corretto nei test; la qualità effettiva del prossimo benchmark reale non è ancora misurata. Nessuna modifica alla release GitHub.

Collaudo delle esenzioni corrette completato 10:10:58: T2 ora bloccato subject_mismatch, T1 ancora bloccato, S4 stesso testo poco pertinente. Correzione del caso noto confermata nei test ed esito sul telefono coerente; qualità della generazione ancora insufficiente. Tempi non confrontabili: l’app va in pausa e lo schermo si spegne durante T2. Report: /Users/erikahu/ALLMA/analisi/2026-10-14/esenzioni-corrette/ESITO_TELEFONO.md.

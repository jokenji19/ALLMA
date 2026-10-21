# Candidati sintetici ispezionabili

L’ultimo benchmark di supporto ha bloccato tutti e tre i casi, senza conservare i candidati scartati. Non era quindi possibile distinguere un errore di formulazione del modello da un falso positivo del controllo.

Solo il core isolato creato per il profilo support abilita la cattura temporanea. ALLMACore richiede anche user_id sintetico BENCHMARK_, seed diagnostico intero e recupero risposte disabilitato. Il candidato è la risposta dopo CognitivePipeline e prima dei controlli di output, non il ragionamento interno. Il record riporta request_id, testo, stadio e risultati dei controlli di attribuzione, esperienza condivisa inventata, formato e ripetizioni; per ogni frase è riportato il controllo di attribuzione. Le verifiche esistenti non vengono modificate.

Il record è trasferito al passo del report JSON/Markdown, separato dalla risposta validata e dai suoi metadati. Non viene aggiunto ai metadati delle memorie. La cattura viene pulita prima/dopo il passo e alla chiusura del core temporaneo. I candidati invalidi restano esclusi dall’apprendimento. La risposta è limitata a 16000 caratteri, con troncamento dichiarato; dettaglio per massimo 20 frasi. Il report include anche l’impronta del codice dei controlli output_contract.

È uno strumento per analizzare i soli casi sintetici autorizzati, non un miglioramento di qualità già dimostrato. Non cambia input, prompt, seed, budget o campionamento e non aggiunge inferenze. Il record per frase spiega dove scatta il controllo lessicale, ma non dimostra da solo che quel controllo sia semanticamente corretto.

Verifica finale: 106 test superati (core_response, benchmark_metrics, output_contract), controllo web e diff pulito. APK con payload verificato e installazione conservando i dati riuscita. SHA-256 locale e sul telefono: d897d281e1a9bcc059ba57cf0bcbadf0e9e2ed3d6110bb4d27763f91f1a8716c. Activity avviata; raccolta e revisione dei candidati reali del benchmark ancora da eseguire. Release GitHub invariata.

Collaudo reale completato: candidati sintetici catturati e associati ai tre request_id, senza troncamento. Revisione umana: tre blocchi giustificati (corso/esame/trasloco appropriati), nessuna risposta utile. T2 inventa anche solitudine e risata; questi dettagli non sono tutti coperti dal controllo di attribuzione. Media 9,63 s non attribuibile causalmente alla diagnostica. Analisi completa: /Users/erikahu/ALLMA/analisi/2026-10-14/candidati-diagnostici/ESITO_TELEFONO.md.

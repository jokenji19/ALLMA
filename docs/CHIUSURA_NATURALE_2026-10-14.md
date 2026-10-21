# Prova del confine ragionamento / risposta

Diagnostica → Supporto · chiusura naturale confronta lo stesso caso noto S4 con prompt nativo minimo, seed 20261312, modello e campionamento invariati. Due richieste con cap totale 384 token. Primo braccio: bounded, 128 ragionamento e 256 riservati alla risposta, chiusura forzata al limite. Secondo: naturale, thought_budget=None sul wrapper e una sola generazione senza chiusura inserita da ALLMA. La chiusura </think> viene osservata in modo incrementale, anche se spezzata fra token, senza salvare il ragionamento.

Nel ramo naturale il budget è condiviso: nessuna riserva garantita per la risposta. Il modello può non chiudere entro 384 token e quindi non produrre risposta; questa possibilità è dichiarata nel manifest e nei metadati, non trasformata in successo. La prova isola due strategie al medesimo cap totale, non due partizioni perfettamente equivalenti. Ordine fisso, cache e frequenze non controllate: nessuna inferenza causale generale né misura di energia.

Il confronto non usa memoria personale o CognitivePipeline. Il wrapper mantiene i controlli su cancellazione e ripetizioni; può quindi interrompere una generazione ripetitiva. Il benchmark mantiene l’arresto termico prima della richiesta successiva. Non altera il ragionamento della chat ordinaria e non disabilita la capacità del modello di ragionare.

72 test superati (support_roles, core_response, benchmark_metrics); controllo web e diff pulito. Le prove verificano la scelta del ramo naturale, l’osservazione della chiusura spezzata, budget/input/seed dichiarati e l’isolamento delle memorie. I testi del modello reale restano da verificare sul dispositivo.

APK con payload verificato e installazione preservando i dati riuscita. SHA-256 locale e sul telefono: 06a1b58d5b0a5605b8271dace235a011b13472563f90c8fce7dfb4c62f6afaaf. Activity avviata; collaudo reale ancora da eseguire. Release GitHub invariata.

Collaudo reale completato: forzata 10,74 s con risposta errata (appropriazione del corso); naturale 19,73 s, limite 384 esaurito, nessuna chiusura osservata e nessuna risposta finale. La naturale non viene adottata nella chat. Non consente di giudicare la qualità dopo una chiusura spontanea mai avvenuta. Report: /Users/erikahu/ALLMA/analisi/2026-10-14/chiusura-naturale/ESITO_TELEFONO.md.

# Prompt pertinente e budget di ragionamento — 13 ottobre 2026

Il primo confronto telefonico aveva mostrato prompt da 592/611/788 token nella pipeline contro 70/83/82 nel probe, e limiti di 48 token di ragionamento esauriti in ogni generazione. I risultati non dimostravano che ogni errore dipendesse esclusivamente dal modello.

## Modifiche

- Contratto identitario compattato da 897 a 465 caratteri (−48,2%). Restano nome originario, separazione modello/identità, memoria documentata, attribuzione utente/ALLMA, incertezza e distinzione dati/istruzioni. I controlli del codice su autobiografia e storia restano attivi.
- Compattate le istruzioni generali e di ragionamento; eliminate costruzioni duplicate del contesto nel core. Ricordi recuperati, ipotesi oniriche revisionate, correzioni e cronologia continuano a seguire i percorsi precedenti.
- Ora e batteria vengono recuperate soltanto per domande pertinenti. Non si aggiungono dati volatili del dispositivo a deduzioni, calcoli, spiegazioni o supporto emotivo soltanto perché la frase è lunga o contiene un punto interrogativo. Il monitoraggio termico e i limiti di risorse continuano a funzionare separatamente dal testo del prompt.
- Indizi emotivi più compatti: rimangono ipotesi sull’utente, seconda persona, emozioni coesistenti, negazioni e incertezza.

## Confronto progressivo

Prima ripetere **ALLMA / modello · 4 coppie**, con gli stessi input, seed e budget di 48 token del primo giro. Confrontare qualità, token del prompt e TTFT, ricordando che cache e calore non sono controllati completamente.

Poi **Ragionamento 96 / 128 · 4 coppie**: stessi due problemi di deduzione e JSON numerico, ciascuno eseguito in pipeline e probe per i due budget. Totali 240/272 token, riserva risposta fissa 144. Stesso seed per lo stesso problema, ordine alternato tra budget e bracci. L’allocazione ampia è consentita soltanto nel contesto diagnostico esplicito; i limiti termici ed energetici restano prioritari. Un budget ridotto dal sistema viene registrato come differenza, non considerato una prova equivalente. Non si aggiungono risposte ad hoc nel core e non si modifica il corpus per nascondere gli errori già osservati.

I nuovi budget non sono applicati indiscriminatamente alle conversazioni normali: più ragionamento può aumentare tempo, calore e consumo senza garantire correttezza. Le nuove misure decidono l’intervento successivo.

## Verifica in corso

Primo gruppo: 216 test superati, un controllo richiedeva la frase sulla riduzione delle ripetizioni nel ragionamento; la frase è stata conservata nella formulazione compatta. Suite completa: **874 superati, 15 saltati, 6 warning**, 162,05 s. Dopo l’allineamento del seed del medesimo problema tra i profili, **25 controlli finali superati**, 6,15 s. Controlli JavaScript della chat completati. APK finale compilata e payload verificato: SHA256 `37023807f6cf8332502543684d481f51d4df401fb883cd021d592757f925c558`. Installata con `-r`, conservando i dati. Nessuna modifica alla release pubblicata. Collaudo di qualità e tempi in attesa del nuovo avvio manuale del confronto da 48 token, poi del profilo 96/128 dopo raffreddamento. Nessuna nuova percentuale di velocità, qualità o consumo dedotta dalla riduzione in caratteri.

## Primo collaudo dopo la modifica

Confronto a 48 token completato: 4 coppie. Media dei tre casi generativi 21,67 → 12,70 s (−41,4% osservato), token prompt medi 663,67 → 373,33 (−43,7%). JSON numerico ora corretto, deduzione ancora errata, supporto emotivo ancora parziale. Condizioni e cache non completamente controllate; nessun miglioramento globale o energetico dedotto. Dettagli in `analisi/2026-10-13/prompt-ragionamento/ESITO_PROMPT_RIDOTTO.md`, esterno al repository. Confronto 96/128 ancora da eseguire.

## Confronto 96/128 parziale

Tre richieste su otto prima di thermal_pause a 42,1 °C: S2 errato con pipeline e probe a 96, errato nel solo probe a 128. Pipeline 128 e casi JSON non eseguiti. Su S2 pipeline 96: 20,57 s contro 12,30 s a 48 (+67,3% osservato), senza guadagno di correttezza. Nessun aumento indiscriminato dei budget normali. Esiti e limiti in `analisi/2026-10-13/prompt-ragionamento/ESITO_RAGIONAMENTO_PARZIALE.md`, esterno al repository.

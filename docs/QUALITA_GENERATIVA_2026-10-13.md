# Qualità generativa — 13 ottobre 2026

Intervento successivo alle ripetizioni della conversazione e ai fallimenti del benchmark Rapida. Obiettivo: migliorare le condizioni della generazione, mantenendo identità originaria, memoria attribuita, ragionamento e controlli già esistenti.

## Cambiamenti

- Per modelli il cui nome identifica Qwen3, campionamento thinking: temperature=0.6, top_p=0.95, top_k=20, min_p=0.0. Parametri indicati nella [scheda ufficiale Qwen3-1.7B](https://huggingface.co/Qwen/Qwen3-1.7B). Per altri modelli resta il profilo precedente. Non è una prova che il profilo consigliato sia migliore con i budget ridotti di ALLMA.
- Istruzioni più dirette: ragionamento breve sul punto decisivo, verifica della conclusione, passaggio alla risposta, evitando la parafrasi della domanda e il discorso su come si vorrebbe rispondere. Rimosso il target generico 3–5 frasi/80 parole. Restano indicazioni su contraddizioni, ipotesi e incertezza. Budget di ragionamento e risposta invariati.
- Il contesto emotivo richiede seconda persona, accoglienza delle emozioni che coesistono, assenza di minimizzazione e rassicurazioni assolute. Nessuna emozione predefinita o risposta del benchmark inserita.
- Controllo conservativo del numero di frasi per richieste esplicite da una a cinque frasi. Una risposta riconoscibilmente fuori formato è invalida, non viene tagliata o riscritta e non viene appresa. Viene verificata prima della visualizzazione. Citazioni, codice, elenchi e abbreviazioni ambigue restano non misurati: non si forza un conteggio ipotetico.
- Lo stesso controllo protegge recupero e osservazione delle risposte apprese, comprese vecchie risposte confermate. Il benchmark registra numero di frasi richieste/osservate nei metadati di generazione, insieme ai parametri reali del sampler.

Nessun nuovo retry o ciclo di revisione col modello. Resta il percorso esistente con ragionamento e risposta a budget separati. Nessuna modifica dei pesi GGUF. I controlli non verificano la verità scientifica di ogni proposizione e non garantiscono che il modello segua le istruzioni.

## Verifica in corso

140 test mirati superati sulla prima revisione, inclusi emozioni, pipeline e ragionamento. Ulteriori 11 test di policy superati, incluso recupero di una risposta confermata con numero di frasi errato. Suite completa offline: **816 superati, 15 saltati, 5 warning**, 166,54 s. Il test sul vecchio recupero è stato aggiunto dopo la raccolta della suite e verificato nella successiva esecuzione dedicata. Diff verificato.

APK compilata e verificata: payload_matches=true, arm64-v8a; SHA256 `b49a2f2b5b83ba46e60e5584bea0c895cd84a1a07600af2fa091413a619f6487`.

Il telefono ha temperatura batteria rilevata di 41,2 °C prima della prova, alimentazione USB e livello Android 97%. Il confronto di velocità e consumi richiede di registrare condizioni reali e mantenere l'app in primo piano; non è ancora possibile quantificare miglioramenti.

Installazione `adb install -r` riuscita mantenendo i dati, hash dell'APK sul telefono identico; app avviata, processo 29348. Benchmark di qualità sul dispositivo in attesa dell'avvio manuale autorizzato.

Verifica finale: impedita anche l'aggiunta di riflessioni emotive dopo una risposta con numero di frasi vincolato. 41 test mirati finali superati, incluso il caso con milestone forzata. Questa modifica è successiva alla suite completa sopra riportata; nessun nuovo cambiamento del sampler. APK finale verificata e installata: SHA256 `d58d30265676ad0f25a55a2554b399ca2169b3c6586e0f8d0fe4ceb9acd8fdf5`, hash sul telefono identico, processo 30902.

## Risultato del collaudo reale

Benchmark Rapida completo, sessione `aaaf504bf38a4cb489a3b48c9087fd15`, 20:48:54–20:50:36. Modello caricato; nessun traceback/errore di generazione nei log esaminati; app in primo piano durante la prova, pausa dopo il completamento. Parametri reali verificati nel report: 0.6 / 0.95 / 20 / 0.0. Dataset e seed corrispondono al confronto precedente.

| Caso | Tempo | Esito |
|---|---:|---|
| N1 | 19,08 s | `no`, corretto e formato rispettato. |
| N2 | 6,55 s | `42`, corretto e formato rispettato. |
| N3 | 13,88 s | JSON corretto con totale 8 e pari true. |
| N4 | 16,89 s | subject_mismatch; una frase invece delle due richieste. Risposta rifiutata, non soddisfacente. |
| N5 | 25,01 s | format_mismatch; una frase invece delle tre richieste. Report finale contiene l'avviso, non il testo rifiutato: la correttezza scientifica non è valutabile integralmente da questo report. |
| N6 | 13,68 s | Non inventa il colore, ma risposta ancora generica, italiano imperfetto e descrizione poco appropriata delle capacità personali del sistema. |

Media 15,85 s, TTFT medio 6,24 s, 752 token compreso ragionamento. Confronto precedente: 18,48 s e 659 token, con app in background negli ultimi casi. Il calo osservato dei tempi non dimostra un miglioramento stabile né può compensare due risposte rifiutate. Batteria rilevata 40,0→42,5 °C, alimentazione USB, livello 96%: nessuna misura affidabile dell'autonomia. Non vengono lanciate altre prove pesanti in questo intervento.

Tutti i ragionamenti raggiungono ancora il limite; le nuove istruzioni non hanno prodotto una conclusione spontanea entro il budget nei sei casi. Il controllo sul formato e sulla prospettiva è verificato, mentre il miglioramento della qualità generativa **non è dimostrato**. Restano necessarie prove controllate su budget/model capabilities, con risposte rifiutate conservate soltanto nelle diagnostiche isolate per valutazione umana. Questo è un limite del report attuale, non una richiesta di inserire risposte di riferimento nel codice.

Report e manifest locali: `/Users/erikahu/ALLMA/analisi/2026-10-13/qualita-generativa/android-quick.*`.

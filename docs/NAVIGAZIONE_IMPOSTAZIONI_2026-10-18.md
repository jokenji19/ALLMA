# Schermate interne e impostazioni · 18 ottobre 2026

Richiesta: ordinare le impostazioni e aprire le destinazioni della sidebar come pagine interne.

## Modifiche

- Navigazione unica tra chat, memoria, diario dei sogni, voce, profilo, impostazioni e diagnostica. Le destinazioni della sidebar non usano più contenitori modali.
- Impostazioni organizzate in sette voci: profilo, modello, aspetto e chat, notifiche, sogni e iniziativa, dati e backup, diagnostica e prestazioni.
- Modello, notifiche, sogni, aspetto e dati hanno sottopagine distinte. Decider e controlli tecnici restano disponibili. Tutti i 26 benchmark sono conservati, raggruppati per argomento; Rapida resta la selezione iniziale.
- Intestazione comune e ritorno al livello precedente. Il DOM della chat resta montato, conservando bozza e aggiornamenti. La posizione di scorrimento delle pagine viene ripristinata.
- Indietro chiude prima la vista del cervello o il menu, poi risale le pagine. Alla radice porta l’app in background. Gestori nativi per tasto Back e callback Android 13+, con priorità standard che lascia precedenza alla tastiera.
- Uscire dalla voce disattiva microfono, riproduzione ed effetti tramite il percorso esistente. Uscire dai dati svuota il campo password del backup.
- Letture di modello, notifiche e backup richieste solo entrando nella pagina pertinente. Monitor diagnostici sospesi fuori dalla diagnostica e quando il documento è nascosto. Sidebar chiusa esclusa dalla navigazione accessibile.
- Stile Paper chiaro/scuro, nessuna nuova dipendenza grafica o animazione continua. Benchmark a tutta larghezza anche a 320 px; stati diagnostici italiani e contrasto coerente.

## Verifiche

- 24 test Python passati: navigazione/Back nativo con API simulate 24, 32, 33 e 36; integrazione asset offline; controlli esistenti di chat, benchmark, backup e confezionamento.
- 52 controlli reali nel browser sulla navigazione e 70 su chat, voce e sogni, tutti passati. Le prove usano dati sintetici. Non sono misure di qualità cognitiva.
- Controllo visivo a 390 × 844 e 320 × 568, temi chiaro e scuro. Nessuna larghezza oltre il viewport rilevata nelle pagine controllate.
- APK ricompilata dal payload aggiornato; verificati runtime ARM64/Qwen 3.5, risorse backup e attributo enableOnBackInvokedCallback nel manifest finale. Gli asset del nuovo layout corrispondono al payload incorporato.
- Installazione con aggiornamento riuscita sul telefono collegato, senza cancellare i dati.

Build: **102515**, versione **0.9.0.0**.
SHA-256 APK: `88410a3332eac5e1b5620cc0373032625c484aae8ef1c99b36ebe062296de307`.

## Collaudo Android

Collaudo manuale confermato dall’utente sulla build 102515: «Sì, pagine e Indietro funzionano». La prova comprende Modello → Indietro → Impostazioni → Indietro → Chat e apertura Memoria dalla sidebar come pagina intera. Questa conferma riguarda questi percorsi, non costituisce una verifica di tutte le funzioni Android.

Il cervello aperto dal titolo ALLMA mantiene il proprio dialogo esistente: non è una destinazione della sidebar. I selettori di file di sistema e l’eventuale permesso notifiche continuano a usare le interfacce native Android.

Artefatti: `../../analisi/2026-10-17/navigazione-impostazioni/` (report browser, XML test, log compilazione e anteprime sintetiche). Nessuna schermata del telefono o memoria personale è stata copiata per questa verifica.

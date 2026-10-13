# Intro e animazioni mirate — 12 ottobre 2026

## Cambiamenti

Intro nativa coerente con lo stile azzurro ghiaccio: scheda chiara, titolo Uno spazio per pensare insieme, fase corrente, indicatore di attività e traccia Verifica · Modello · Chat. Anche il bootstrap prima dell’estrazione e la breve apertura della WebView usano lo stesso linguaggio visivo. Nessun logo aggiunto.

La verifica del file GGUF resta su un worker. L’inizializzazione del core è stata spostata dal thread Kivy a un worker; inoltre il caricamento nativo del GGUF, prima rinviato al primo messaggio, viene ora eseguito su quel worker nell’intro. La chat viene aperta dopo _llm_ready=True. Gli errori non mostrano un falso stato pronto; vengono presentati senza percentuali inventate. Un core pronto dopo la chiusura dell’app viene chiuso senza aprire la chat. Rimossa l’attesa artificiale di 1,5 secondi dopo la verifica.

L’attesa del modello è anticipata all’avvio: questa modifica non dimostra una riduzione del tempo totale di caricamento e non cambia il modello. Le percentuali restano disponibili solo per download con dimensione nota. Durante verifica e inizializzazione c’è un indicatore indeterminato.

Animazioni web: comparsa delle schede in 180–200 ms, feedback al tocco, pulsazione piccola del microfono in ascolto/riproduzione e anello lento durante elaborazione. Nessun moto continuo a riposo. Animazioni sospese quando la pagina è nascosta; prefers-reduced-motion disabilita il movimento. Indicatore nativo aggiornato a 10 Hz con elementi grafici persistenti; bootstrap a 2,5 Hz. Il movimento nativo rispetta animator_duration_scale su Android quando disponibile. Non sono state misurate nuove percentuali di risparmio energetico.

## Difetti trovati durante verifica

Il ProgressBar standard interferiva con il rendering dell’anteprima nativa: sostituito con un Widget minimale dotato di value/max e indicatore indeterminato, conservando il contratto usato dai download. Grafica aggiornata tramite elementi persistenti, senza ricreare il canvas ogni frame. Il rendering nativo finale mostra tutte le etichette; la prova verifica avvio e arresto del timer. Screenshot prodotto dal widget reale con una fase di prova, non catturato dal telefono.

L’ispezione della finestra Mac tramite Computer Use è stata bloccata dai permessi dell’app; non aggirata. La verifica prosegue con rendering locale, regressioni e log Android.

## Test

Suite finale: **626 passed, 15 skipped, 11 warnings in 38.85s**, offline e con parallelismo limitato. Nessun fallimento. I warning sono deprecazioni transformers. Otto regressioni aggiunte: UI libera durante inizializzazione, consegna sul Clock, errore, chiusura durante caricamento, chiusura tra worker e callback, assenza di attesa artificiale, arresto dell’indicatore e mancata apertura in caso di GGUF non pronto.

**67 controlli web superati**, inclusi moto solo negli stati attivi, arresto a riposo, pausa quando nascosto, preferenza movimento ridotto e mantenimento di tutte le funzioni chat/voce/revisioni. Rendering nativo a 390×844 verificato due volte, con animation_was_active=true e stopped=true. Costruzione effettiva di SetupView verificata separatamente, senza avviare download o modificare memorie.

## Android

APK compilata, payload_matches=true, KivyMD 1.2.0, arm64-v8a. SHA-256: 1c8b56b535e28f0538e05b84193121513479aeb5f0f7996c4782c8f62639ca51. Installazione finale adb install -r: Success, dati conservati. Impronta del base.apk sul telefono uguale alla build locale.

Processo Samsung SM_S938B PID 29588. Nei log del solo processo:

- 18:26:48.696: verifica terminata e transizione verso la chat.
- 18:26:48.711: ChatView avvia l’inizializzazione.
- 18:26:49.023: caricamento GGUF sul thread 29862, distinto dal thread Kivy 29731.
- 18:26:50.110: motore attivato, circa 1,09 secondi dopo l’inizio del caricamento nativo.
- 18:26:50.482: WebView caricata.

Nessun errore di inizializzazione trovato nella finestra di log controllata. Questi tempi non includono l’intero bootstrap e la verifica SHA del file. Non misurati frame rate reale, temperature, autonomia o latenza della prima risposta. Non eseguita una nuova prova vocale con parlato umano. Il collaudo visivo del telefono richiede osservazione umana, perché non è disponibile un controllo diretto della sua schermata.

Modifiche salvate localmente, nessun commit o push. Artefatti: /Users/erikahu/ALLMA/analisi/2026-10-12/intro-animazioni.

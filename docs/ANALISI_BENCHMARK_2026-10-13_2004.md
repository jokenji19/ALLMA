# Benchmark Rapida — 13 ottobre 2026, 20:04

Sessione `993a0009a2b04e35b4624386c13494f1`, report `report_a93438cf0b6f4b0b8137f2794a584f2c`. Esecuzione 20:04:49–20:06:46, sei casi completi, nessuna cancellazione. Analisi dei log limitata al processo ALLMA 7065, ancora presente dopo il completamento. Nei log esaminati non risultano traceback o errori di inferenza.

| Caso | Tempo | Valutazione del contenuto |
|---|---:|---|
| N1, implicazione gatti/mammiferi | 12,54 s | `no`: corretto e formato rispettato. |
| N2, 23 + 19 | 4,13 s | `42`: corretto e formato rispettato. |
| N3, JSON somma/parità | 14,06 s | Totale 8 e pari true: corretto, JSON valido. |
| N4, emozioni miste | 14,99 s | «Sono felice per il tuo nuovo lavoro» non si appropria della biografia dell'utente, ma segue «ti prego di non paura»: italiano errato, preoccupazione minimizzata, una frase anziché due. |
| N5, pesci fuori dall'acqua | 35,37 s | Usa «glii» invece di branchie e attribuisce cause infondate a dispersione del calore e movimento su terra. Fallimento della qualità scientifica. |
| N6, colore preferito sconosciuto | 29,79 s | Non inventa il colore, ma aggiunge spiegazioni generiche e un'offerta poco pertinente. |

Il controllo automatico delle famiglie emotive passa N4 perché riconosce gioia e paura nei metadati. Non misura la qualità della risposta né il rispetto delle due frasi; il report mantiene human_review_required. Quattro righe risultano automaticamente passed, ma questo non equivale a quattro risposte semanticamente soddisfacenti.

## Prestazioni e limiti

Media 18,48 s; attesa del primo token media 8,37 s; 659 token generati complessivi, incluso il ragionamento. Il TTFT è il primo token di generazione, non necessariamente la prima parola mostrata all'utente. first_answer_ms è assente: il benchmark non passa un callback di visualizzazione. stream=True nel wrapper serve anche alla cancellazione e non dimostra streaming visibile nell'interfaccia.

Attesa lock inferenza inferiore a 0,005 ms, preparazione prompt 7,5–22,8 ms. Queste misure non spiegano i ritardi di secondi; il collo di bottiglia misurato è all'interno della generazione nativa. Non è stata misurata separatamente la valutazione iniziale dei token del prompt.

Alle 20:05:53 l'attività Android va in pausa durante N5, mentre il benchmark continua fino alla fine. N6 ha un TTFT di 22,40 s. Il passaggio in background può avere influito su scheduling e tempi, ma non è una causa dimostrata dai log.

La prova precedente con la stessa pipeline aveva media 13,10 s; il confronto più vecchio aveva 19,28 s. Questa esecuzione non conferma un miglioramento robusto e non consente di attribuire la differenza alla sola modifica del codice. Dataset, seed e hash dei tre sorgenti registrati corrispondono alla prova completa immediatamente precedente; nonostante ciò N4 e N5 hanno testi diversi. Il solo seed non rende l'esecuzione nativa perfettamente deterministica.

Temperatura batteria rilevata iniziale e finale 40,5 °C, dispositivo in carica. Massimo CPU fra i campioni di inizio/fine generazione: 69,1 °C; non è una misura continua del picco. Non ci sono dati validi per stimare consumi o autonomia. Il campo battery_level=100 deriva attualmente dallo stato energetico interno, non da una lettura diretta della percentuale Android: va corretto o rinominato nella telemetria.

Tutti i sei ragionamenti raggiungono il budget e terminano con length; le risposte finali terminano con stop. Il budget preserva una fase di ragionamento, ma il ragionamento non arriva spontaneamente alla conclusione prima del taglio. Non prova da solo la causa degli errori; richiede un confronto controllato fra budget, qualità e tempi.

## Priorità emerse

1. Verificare la qualità generativa su casi nuovi: prospettiva, accoglienza delle emozioni, italiano e fatti. Le protezioni attuali non correggono l'errore scientifico.
2. Misurare separatamente il tempo di elaborazione del prompt e la prima risposta visibile, registrando pause/background e condizioni reali.
3. Valutare i budget di ragionamento su più casi, senza inserire risposte del benchmark o aumentare indiscriminatamente token e consumi.
4. Correggere la provenienza del livello batteria e tenere distinti stato interno e sensori Android.

Analisi soltanto: nessuna modifica al modello o alla pipeline effettuata durante questa prova. Report e manifest salvati in `/Users/erikahu/ALLMA/analisi/2026-10-13/qualita-risposte/latest-quick.*`.

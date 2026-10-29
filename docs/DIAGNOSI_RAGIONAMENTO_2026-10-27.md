# Diagnosi del ragionamento — 27 ottobre 2026

**Build finale 102577 installata e verificata.** Completate 40 richieste native sintetiche su Android in tre batterie, con ripristino finale del modello originale su OpenCL e contesto 2K. Corretto un difetto reale nelle metriche di arresto dello streaming. La configurazione generale delle risposte non è stata cambiata sulla base di pochi esempi.

## Domande della verifica

1. L'errore dipende soltanto dalla GPU?
2. Il pensiero viene interrotto troppo presto?
3. Il prompt o la tokenizzazione alterano la domanda?
4. Penalità e passaggio fra pensiero e risposta influenzano il risultato?
5. Un miglioramento osservato si trasferisce a domande nuove?

Stesso Qwen3.5-2B Q4_K_M, contesto 2.048, template nativo, seed fissati per caso, azzeramento della sequenza e nessun riutilizzo della cache fra i casi. Le prove interrogano il motore direttamente: non applicano gli strumenti esatti, i ricordi o i controlli finali della chat di ALLMA. Nessuna modifica ai suoi dati personali o alle preferenze salvate del modello.

## CPU e GPU; budget del ragionamento

Tre casi esplorativi: sette meno due; undici meno quattro; copia di un codice sintetico in JSON.

| Configurazione | Corrette e nel formato / 3 | Prima risposta, mediana |
|---|---:|---:|
| GPU, 48 token, penalità 1,10 | 1 | 1,86 s |
| CPU, 48 token, penalità 1,10 | 2 | 5,08 s |
| GPU, 128 token, penalità 1,10 | 1 | 5,66 s |
| GPU, chiusura naturale, massimo 272 token | 0 | nessun testo finale |

CPU e GPU hanno ricevuto gli stessi prompt tokenizzati e gli stessi seed. La CPU è stata selezionata esplicitamente con lista dispositivi vuota e offload disabilitato, senza disattivare globalmente i componenti GPU/NPU. Thread e batch fisico del controllo sono allineati a quattro e 256.

La CPU ha risposto `2` a sette meno due; la GPU `4`. Entrambe sbagliano questo caso. Non è dimostrato un difetto esclusivo della GPU: differenze numeriche e campionamento possono far divergere le sequenze. Questa prova non confronta la quantizzazione con pesi a precisione piena.

Gli audit confermano domanda presente una volta, nessuna storia rimossa, ricostruzione esatta da token a testo e prompt identici per caso fra le configurazioni. Il template effettivo del GGUF è conservato nei metadati locali.

## Penalità e riutilizzo dello stato

Seconda batteria sugli stessi tre casi:

| Configurazione GPU | Corrette e nel formato / 3 |
|---|---:|
| Baseline 48 token, penalità 1,10 | 1 |
| 48 token, penalità neutra 1,00 | 1 |
| 48 token, stato ricalcolato prima della risposta | 1 |
| 128 token, penalità neutra 1,00 | 3 |
| Modalità nativa diretta, senza pensiero esplicito | 3 |

Il ricalcolo dello stato produce gli stessi tre testi della baseline e costa più tempo: non c'è evidenza, su questi casi, di un errore risolto azzerando lo stato. La sola riduzione della penalità a 48 token cambia alcuni numeri generati ma non migliora il punteggio. La combinazione di 128 token e penalità neutra merita invece una verifica distinta su casi nuovi.

La modalità diretta è un controllo del motore linguistico. Non cancella i moduli cognitivi di ALLMA e non è stata imposta globalmente all'app.

## Verifica su quattro casi nuovi

Calcolo con due operazioni, deduzione con categorie inventate, JSON a due campi, posizione di una lettera. Configurazioni e criteri fissati prima dell'esecuzione, nessun retry o correzione delle risposte.

| Configurazione | Corrette e nel formato / 4 | Prima risposta, mediana |
|---|---:|---:|
| 48 token, penalità 1,10 | 0 | 3,26 s |
| 128 token, penalità 1,00 | 3 | 7,15 s |
| Modalità nativa diretta | 3 | 0,37 s |

Il calcolo `14 − 6 + 3` resta errato: le due configurazioni migliori rispondono `8`, anziché `11`. La baseline fallisce anche deduzione e posizione della lettera; nel JSON conserva i valori giusti ma aggiunge un blocco Markdown vietato dal formato richiesto. Il punteggio comprende quindi sia contenuto sia conformità, non misura soltanto conoscenza.

Su questi quattro casi il passaggio 0/4 → 3/4 equivale a **+75 punti percentuali**. Non è un miglioramento del 75% dell'intero progetto: quattro casi, seed fissati e nessuna valutazione ampia su conversazione libera, emozioni o sicurezza. Il costo di 128 token non è giustificato automaticamente per i compiti semplici, dato il risultato equivalente del controllo diretto.

## Bug corretto: motivo di arresto dello streaming

Il wrapper ignorava `finish_reason` nell'ultimo elemento dello stream e ricavava «stop»/«max_tokens» dalla lunghezza del testo ritokenizzato. Quel conteggio può essere inferiore ai token effettivamente generati.

Riproduzione reale: il caso naturale arriva al limite di 272 token, ma il testo ricostruito ne conta 270. Prima il wrapper scriveva `stop`; nella build 102577 conserva **`length` dal runtime nativo**, con `finish_reason_source=native_stream` e `token_count_source=retokenized`. La generazione non aveva concluso il pensiero entro il limite: non era una conclusione normale.

La correzione:

- conserva il motivo nativo di arresto senza sovrascriverlo con il conteggio ricostruito;
- distingue lo stop imposto dal controllo locale delle ripetizioni;
- etichetta esplicitamente il ripiego euristico quando il runtime non fornisce il motivo;
- lascia il tempo del primo token assente se lo stream contiene soltanto un elemento finale vuoto.

La pipeline riconosce già `length` e `max_tokens`: riceve ora un segnale corretto per classificare le risposte interrotte e gestirne consegna e apprendimento.

## Riferimento del produttore

La [scheda ufficiale Qwen3.5-2B](https://huggingface.co/Qwen/Qwen3.5-2B#thinking-mode) documenta modalità diretta e con pensiero, segnala possibili cicli di pensiero nel 2B e raccomanda penalità di ripetizione neutra nelle impostazioni indicate. Sono indicazioni del produttore, non una garanzia per questa quantizzazione sul telefono. I confronti qui mantengono il resto del campionamento dell'app per isolare le variabili.

## Decisione e stato finale

- Contesto **2K** e **GPU OpenCL** ripristinati; nessuna preferenza CPU persistita.
- Nessun aumento generalizzato del budget e nessuna disattivazione generalizzata del ragionamento.
- La configurazione 128/neutra è una candidata per i compiti che richiedono ragionamento; prima di trasformarla in una politica generale serve un confronto attraverso l'intera pipeline su casi più ampi. Riutilizzare `reasoning_budget` e la distinzione `dialogue_task` già esistenti, evitando un secondo controllore.
- Gli strumenti verificati di ALLMA restano fondamentali per i calcoli esatti; queste prove non li usano e non indicano che abbiano restituito gli errori del modello nativo.
- Batterie reali completate **12 + 15 + 13 = 40 richieste**, senza contaminare l'apprendimento personale.
- Desktop finale: **2.976 test superati e 15 saltati**, più **6/6 prove di uscita improvvisa** eseguite separatamente fuori dalla restrizione OpenMP: **2.982 superati** complessivi.
- Processo Android rimasto vivo; motore e collegamenti ripristinati, nessuna operazione nativa residua, tempo di spegnimento originale dello schermo ripristinato. Temperatura della batteria osservata nelle prove: 35,5–38,6 °C; nessuna misura di consumo energetico o temperatura del chip.

Evidenze: [riepilogo aggregato](/Users/erikahu/ALLMA/analisi/2026-10-27/diagnosi-generazione/summary.json), [prima batteria](/Users/erikahu/ALLMA/analisi/2026-10-27/diagnosi-generazione/android-reasoning-report.json), [penalità e stato](/Users/erikahu/ALLMA/analisi/2026-10-27/diagnosi-generazione/followup/android-reasoning-report.json), [domande nuove e arresto nativo](/Users/erikahu/ALLMA/analisi/2026-10-27/diagnosi-generazione/validation/android-reasoning-report.json), [verifica APK finale](/Users/erikahu/ALLMA/analisi/2026-10-27/diagnosi-generazione/validation/apk-verification.json).

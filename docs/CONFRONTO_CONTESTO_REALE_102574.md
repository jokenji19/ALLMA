# Confronto reale del contesto — build 102574

La build 102574 è compilata, verificata e installata. Sul Samsung SM-S938B sono state completate 12 richieste reali con Qwen3.5-2B Q4_K_M su OpenCL, poi è stato ripristinato il contesto originale di 2.048 token. La scelta resta **2K**: questa prova non mostra un beneficio di qualità che giustifichi l'aumento automatico.

## Metodo

Due casi sintetici, ripetuti con gli stessi seed e budget per ciascuna configurazione:

1. Domanda breve: sette palline meno due, con richiesta di un solo numero.
2. Dialogo lungo di 60 coppie, con un codice nelle note iniziale, centrale e recente; richiesta di un JSON con tre stringhe o `null` per le note assenti dal prompt conservato.

Ordini 2K → 4K → 8K e 8K → 4K → 2K. Una sola copia nativa di Qwen alla volta, caricata nuovamente per ogni configurazione. Cache della conversazione disattivata e stato di sequenza azzerato prima di ciascun caso. Stessi seed, temperatura, penalità e budget: **192 token totali, 48 di ragionamento e 144 riservati alla risposta**. Nessun retry, correzione o grammatica che forzi il JSON.

Si misura il percorso nativo con il template GGUF; non l'intera pipeline della chat con strumenti, memoria persistente e controlli di ALLMA. I dati personali non sono stati usati né esportati. Nessun file di preferenza del modello è stato modificato.

## Latenza osservata

Mediane di **due sole repliche per caso e configurazione**. Il primo testo della risposta è distinto dal primo token di ragionamento.

| Contesto | Primo testo: caso breve | Primo testo: storia lunga | Risposta lunga completa | Token effettivi del prompt lungo |
|---|---:|---:|---:|---:|
| 2K | 2,80 s | 10,53 s | 16,81 s | 1.824 |
| 4K | 2,37 s | 17,17 s | 21,34 s | 3.840 |
| 8K | 2,34 s | 17,82 s | 23,95 s | 4.116 |

Nel caso lungo, il primo testo arriva **63,1% più tardi a 4K** e **69,3% più tardi a 8K**, rispetto a 2K. Le configurazioni maggiori elaborano più storia: non è una misura del costo della sola allocazione di una finestra più grande, a prompt identico. I tempi brevi non mostrano un rallentamento monotono con la dimensione della finestra. Due repliche non consentono conclusioni statistiche generali.

La finestra 8K qui ospita circa 4,1K token di input; non è una prova con 8K token di prompt.

## Qualità osservata

- Domanda breve: **0/2 risposte corrette per configurazione**. Il percorso nativo ha risposto `4` a sette meno due in tutte e sei le richieste, anziché `5`.
- Richiamo lungo: **0/2 JSON conformi per configurazione**, con errori anche nei codici e nella struttura, non soltanto nell'uso di blocchi Markdown. A 8K la risposta si allunga in una struttura non richiesta e raggiunge il limite della risposta.
- La verifica distingue la risposta fondata sulle note effettivamente rimaste nel prompt dal recupero di tutti e tre i codici del dialogo originale. La semplice assenza di una nota rimossa non viene classificata come allucinazione.

Questi risultati non sono uno 0% di affidabilità di ALLMA. I calcoli esatti di ALLMA passano per il suo percorso verificato; qui si è interrogato direttamente il motore linguistico. La prova non separa ancora le cause fra modello, quantizzazione, backend e chiusura forzata del ragionamento a 48 token. Non autorizza ad attribuire tutti gli errori ai soli pesi del modello. Dimostra che aumentare il contesto non risolve questi casi nella modalità provata.

## Memoria e temperatura

Il runtime nativo conferma finestre realmente allocate di 2.048, 4.096 e 8.192 token:

| Contesto | Buffer KV su OpenCL | Stato ricorrente su OpenCL | RSS del processo dopo i casi | PSS del processo dopo i casi |
|---|---:|---:|---:|---:|
| 2K | 24 MiB | 19,27 MiB | 685–758 MiB | 605–659 MiB |
| 4K | 48 MiB | 19,27 MiB | 685–743 MiB | 604–656 MiB |
| 8K | 96 MiB | 19,27 MiB | 694–724 MiB | 612–637 MiB |

RSS/PSS misurano la residenza del processo; non rappresentano tutta la memoria GPU o del telefono. Driver e allocatore conservano stato tra i caricamenti: non si deduce che 8K consumi meno RAM dai valori RSS più bassi. Il buffer KV aumenta invece in modo esplicito di **72 MiB da 2K a 8K**. Queste colonne non vanno sommate per ottenere una RAM totale.

Temperatura **della batteria** osservata: **36,0–39,7 °C**, telefono alimentato via USB. Non misura la temperatura del chip, il costo energetico o la tenuta per sessioni lunghe. La prova interrompe il lavoro opzionale a 40,5 °C, in background, con sensori indisponibili, su cancellazione o timeout della richiesta.

## Ripristino e verifiche

Il percorso rilascia il motore precedente prima di caricarne un altro. Anche in caso di cancellazione o errore tenta il ripristino della configurazione originale e aggiorna i collegamenti del motore a ragionamento e sogni. Un errore di ripristino viene mostrato; non è dichiarato successo. I casi completati sono salvati progressivamente.

Sul dispositivo:

- 12/12 richieste completate; stesso budget e backend in tutti i casi;
- contesto originale 2K ripristinato e Qwen ancora su OpenCL;
- processo rimasto vivo, zero operazioni native residue, prenotazione di aggiornamento rilasciata;
- tempo di spegnimento dello schermo ripristinato a 60 secondi;
- Decider/NPU non usato o ricollaudato in questa prova.

Desktop: **2.957 test superati, 15 saltati**, più **6/6 test di uscita improvvisa** eseguiti separatamente fuori dalla restrizione OpenMP: **2.963 superati complessivi**. I test includono una sola allocazione alla volta, ripristino dei collegamenti, cancellazione nelle diverse fasi, errore di caricamento/generazione, cambio inatteso del backend, sensori mancanti, background e chiusura dell'app.

## Decisione

Nessun aumento del contesto predefinito. La nuova Diagnostica contiene «Contesto 2K / 4K / 8K · 12 risposte reali», per ripetere il confronto. Il prossimo controllo utile è isolare l'effetto della chiusura del ragionamento sui casi falliti, mantenendo gli strumenti verificati e il recupero mirato già presenti in ALLMA.

Evidenze: [misure aggregate](/Users/erikahu/ALLMA/analisi/2026-10-26/contesto-inferenza/measurements.json), [risposte sintetiche e metriche native](/Users/erikahu/ALLMA/analisi/2026-10-26/contesto-inferenza/android-context-report.json), [esito del dispositivo](/Users/erikahu/ALLMA/analisi/2026-10-26/contesto-inferenza/android-result.json), [allocazioni native osservate](/Users/erikahu/ALLMA/analisi/2026-10-26/contesto-inferenza/native-memory-lines.txt), [verifica APK](/Users/erikahu/ALLMA/analisi/2026-10-26/contesto-inferenza/apk-verification.json).


Seguito: [diagnosi del ragionamento e correzione delle metriche, build 102577](DIAGNOSI_RAGIONAMENTO_2026-10-27.md). I motivi di arresto dello streaming naturale nelle versioni precedenti potevano essere ricavati euristicamente; la nuova prova conserva il motivo restituito dal runtime.

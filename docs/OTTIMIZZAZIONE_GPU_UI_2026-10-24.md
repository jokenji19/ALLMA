# GPU e fluidità dell’interfaccia — build 102555

## Esito sul telefono

**102555 installata e collaudata** sul Samsung SM-S938B, SM8750 / Adreno 830,
con Qwen 3.5 2B Q4_K_M e ragionamento attivo. Restano assegnati **25/25 livelli
alla GPU**. La CPU gestisce coordinamento, memoria, Decider e operazioni di
supporto; la NPU resta disattivata.

Il profilo finale preserva gran parte della velocità GPU eliminando le lunghe
pause osservate nel campione grafico. È stato scelto dopo aver misurato una
prima variante fluida ma più lenta, non soltanto dopo aver compilato il codice.

## Confronto misurato

Stessi sei casi sintetici Rapida, stesso GGUF, stessi seed e prompt.
Quattro casi richiedono Qwen; due sono risolti da ALLMA senza modello.
Tutte le risposte visibili coincidono esattamente fra le tre configurazioni.
I quattro casi del modello generano rispettivamente 33, 142, 101 e 213 token.

| Configurazione | 102553, riferimento | 102554, prima variante | 102555, finale |
|---|---:|---:|---:|
| Microbatch fisico | 512 | 128 | 256 |
| Priorità OpenCL | Predefinita | Bassa | Bassa |
| Richiesta display durante inferenza | Predefinita | Predefinita | 60 Hz |
| Pausa massima rAF WebView | 750 ms | 41,6 ms | **25 ms** |
| Pause rAF oltre 100 ms | 13 | 0 | **0** |
| Somma durate dei quattro casi LLM | 37,46 s | 51,23 s | **40,74 s** |
| Batteria iniziale / finale | 37,5 / 38,6 °C | 38,4 / 39,7 °C | 36,3 / 37,1 °C |

Nel confronto descrittivo, la pausa massima dell’animazione scende del **96,7%**.
Il profilo finale richiede **8,7% di tempo in più** rispetto alla GPU grezza,
e **20,5% in meno** rispetto alla prima variante fluida. Il costo principale
rimasto è il caso JSON; non viene dichiarato che ogni risposta sia più veloce.

| Caso | Riferimento | Finale | Esito visibile |
|---|---:|---:|---|
| N1, sì/no | 8,96 s | 9,55 s | Stessa risposta corretta |
| N3, JSON | 7,96 s | 10,36 s | Stesso JSON valido |
| N4, emozioni miste | 8,13 s | 8,43 s | Stesso testo |
| N5, spiegazione | 12,41 s | 12,39 s | Stesso testo |

Nella configurazione finale sono stati raccolti 3914 intervalli rAF e 2529
frame Android validi: nessuno oltre 100 ms. Il massimo Android misurato è
19,26 ms. Durante le quattro operazioni GPU, 1709 campioni rAF selezionati
fra richiesta e ripristino del display hanno mediana **16,6 ms** e p95
**16,7 ms**, coerenti con la cadenza richiesta di 60 Hz.

### Limiti delle percentuali

Un giro per configurazione e quattro richieste al modello non certificano
ogni possibile conversazione. Le temperature iniziali differiscono e il
telefono era alimentato; non si deducono risparmi di energia o batteria.
Le riserve massime di token di alcuni casi variano con la pipeline adattiva,
ma prompt e token realmente prodotti coincidono e nessuna risposta è tagliata.
La policy dei budget e i pesi del modello non sono stati modificati.

Il primo parser dei frame Android non riconosceva la nuova colonna
FrameTimelineVsyncId: per la 102553 i framestats completi non sono disponibili.
Restano disponibili il confronto rAF comune alle tre prove e i log HWUI del
riferimento, che registrano sei frame lenti, fino a 1506 ms. Il parser è stato
corretto per le prove successive; non sono stati inventati valori mancanti.

## Organizzazione del lavoro GPU e CPU

- `native_backend.py` centralizza il profilo: microbatch GPU 256, batch logico
  512, quattro helper CPU del batch. Contesto 2048 e policy del ragionamento
  restano invariati; Decider conserva due thread CPU e nessun offload.
- Il profilo GPU resta limitato al modello verificato, al SoC SM8750 e al driver
  Qualcomm già misurato. Altri modelli o driver continuano sulla CPU.
- La patch nativa richiede un contesto OpenCL a priorità bassa soltanto con
  opt-in e dopo il controllo di cl_qcom_priority_hint. Se la proprietà viene
  rifiutata, riprova il contesto predefinito. Il ripiego CPU resta disponibile.
- `gpu_render_budget` richiede 60 Hz soltanto alla finestra Android di ALLMA
  durante la generazione GPU. La richiesta precedente viene ripristinata
  anche in caso di cancellazione. Sono rispettati una preferenza già più
  bassa e un modo display esplicito; non cambiano le impostazioni globali.
- Le richieste e i ripristini passano sul thread UI Android senza attese
  sincrone fra quel thread e il worker del modello. Sono state osservate
  quattro coppie richiesta/ripristino nella Rapida finale, più quelle dei
  controlli successivi, tutte concluse con ripristino a 0,0, il valore originale.

Le costanti di priorità sono state verificate nell’SDK ufficiale Qualcomm
Adreno OpenCL 2.3.2. Un piccolo APK isolato ha creato il contesto a priorità
bassa, riletto la proprietà e verificato **256/256 risultati**, poi è stato
rimosso. Non sono incorporati driver o header proprietari nell’APK ALLMA.
La guida Qualcomm descrive priorità e interferenza fra calcolo e grafica;
la selezione finale è basata sulle misure qui sopra.
[Guida Qualcomm, sezioni 3.3 e 9.1.2](https://docs.qualcomm.com/doc/80-NB295-11/80-NB295-11_REV_C_Qualcomm_Snapdragon_Mobile_Platform_Opencl_General_Programming_and_Optimization.pdf),
[API Android per la preferenza della finestra](https://developer.android.com/reference/android/view/WindowManager.LayoutParams#preferredRefreshRate).

## Aggiornamenti della WebView

`StreamDelivery` accorpa i frammenti fino a 80 ms, preservando Unicode,
ordine pensiero/risposta e identificatore del turno. La fine risposta svuota
il buffer immediatamente prima di endStream. Nuova conversazione e pausa
scartano gli aggiornamenti pendenti del turno precedente; eventi tardivi non
entrano in un altro turno.

Una sola richiesta di polling può restare pendente nella WebView. Il pensiero
chiuso riceve testo senza richiedere lo scorrimento della chat ad ogni frammento.
Risposte e pensiero aperto continuano a scorrere. I puntini mantengono lo stesso
stile; il limite di 80 ms riguarda la consegna intermedia, non un effetto di
scrittura artificiale della risposta finale.

Le misure grafiche usano tre puntini CSS temporanei sulla UI del benchmark:
isolano la convivenza con l’inferenza. Non costituiscono una prova di tutte le
possibili schermate 3D, della voce o di ogni ritmo di streaming nella chat.

## Stabilità verificata

- **2413 test desktop passati, 15 saltati, zero fallimenti**, offline.
- Contratti di consegna: ordine, Unicode, flush finale, cambio conversazione,
  eventi tardivi, pausa e assenza di backlog di richieste WebView.
- Contratti display: attivazione solo Android/GPU, ripristino anche dopo
  errore/cancellazione e rispetto di un modo display già scelto.
- Sei casi Rapida completati sulla 102555, quattro generazioni reali OpenCL.
- Cancellazione richiesta mentre esisteva il marcatore di operazione GPU attiva:
  report parziale salvato, app aperta, marcatore rimosso e display ripristinato.
  Il ripristino compare nei log circa 0,31 s dopo la richiesta del test;
  il report è stato rilevato dopo circa 2,29 s, con campionamento ogni due secondi.
- Nuova richiesta dopo cancellazione: N1 completato con risposta corretta
  “no” via OpenCL; N2 calcolato correttamente come 42. Il test è poi fermato
  intenzionalmente per evitare altre generazioni inutili.
- Pausa, salvataggio e rientro nello stesso processo verificati sulla 102555,
  senza traceback, crash nativi o errore di salvataggio nei controlli.
- Sorgenti estratti sul telefono uguali a quelli locali, incluso render_budget.
  Qwen 3.5 e ragionamento sono rimasti selezionati; nessuna conversazione
  personale è stata esportata per le prove.
- Interfaccia dei test rimossa e timeout dello schermo ripristinato al valore
  originale di 60000 ms. La preferenza temporanea a 60 Hz è rimossa a fine inferenza.

Il primo giro desktop della 102554 aveva un solo fallimento nel fixture del
test di pausa, che non costruiva il nuovo componente: fixture aggiornato e
intera suite ripetuta con esito pulito. Non è stato silenziato un errore applicativo.

## Compilazione ed evidenze

Runtime allma-cpu-opencl-v2, stessa sorgente fissata di llama-cpp-python
0.3.36. Patch conservata nella ricetta, con SHA-256 verificato nei metadati
anche dal controllo APK. Cache di compilazione con patch obsoleta rifiutata.
Sono conservate copie delle 102553 e 102554 per confronto e rollback.

APK finale: `bin/allma_prime-0.9.1-arm64-v8a-debug.apk`.
SHA-256: `2dfa20b7acc0f39bc168669e7d8809d8eef9a0b6d1e7f705541e83db1c8fc4ba`.
Versione pubblica 0.9.1, build Android **102555**.

Evidenze locali: `analisi/2026-10-24/fluidita-gpu/`, in particolare
comparison-final.json, render-budget-verification.json, installed-final-verification.json,
full-102555.xml, final-summary.json e le cartelle baseline / interactive /
interactive60 / cancel / recovery. I sorgenti sono salvati nel progetto.
Restano da valutare sessioni lunghe e consumi con protocollo energetico dedicato;
non sono condizioni bloccanti emerse nel collaudo breve concluso.

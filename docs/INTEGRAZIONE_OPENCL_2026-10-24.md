# Integrazione OpenCL — build 102553, 24 ottobre 2026

> Seguito: [ottimizzazione di GPU e interfaccia, build 102555](OTTIMIZZAZIONE_GPU_UI_2026-10-24.md).
> La nuova APK è installata e il collaudo breve di fluidità, cancellazione e rientro è concluso.

## Configurazione verificata

ALLMA 0.9.1 contiene ora un runtime CPU con plugin OpenCL facoltativo.
Sul Samsung SM-S938B verificato, Qwen 3.5 2B Q4_K_M assegna realmente
**25/25 livelli alla GPU Adreno 830**. Il ragionamento, la memoria persistente,
l'identità e la pipeline di ALLMA restano quelli applicativi.

L'attivazione automatica richiede contemporaneamente:

- SoC SM8750 e dispositivo OpenCL `QUALCOMM Adreno(TM) 830`;
- driver `OpenCL 3.0 QUALCOMM build: 0800.64.8 Compiler E031.47.18.56`;
- file del catalogo `qwen3.5-2b-q4_k_m.gguf`, con verifica del checksum;
- runtime e plugin coerenti, compilati dalla stessa sorgente fissata di
  llama-cpp-python 0.3.36.

Altri modelli, telefoni o driver continuano sulla CPU finché non vengono
misurati. Questa build non attiva Vulkan o NPU. Decider rimane sulla CPU
con due thread e con offload delle operazioni e KQV esplicitamente disattivato.

Il GGUF verificato pesa 1.280.835.840 byte e ha SHA-256
`aaf42c8b7c3cab2bf3d69c355048d4a0ee9973d48f16c731c0520ee914699223`.

## Caricamento e recupero

`native_backend.py` registra prima la CPU e aggiunge il plugin OpenCL soltanto
per il profilo misurato. Il manifest dichiara `libOpenCL.so` facoltativa:
l'APK usa il driver Android, senza incorporare un proxy o un driver vendor.
Il loader Khronos e gli header sono dipendenze di compilazione fissate e
verificate; il loader non entra nell'APK.

Il nucleo CPU non dipende dal plugin OpenCL. Se manca il driver, il dispositivo
non è approvato o la registrazione del plugin fallisce, resta disponibile la
CPU. Se l'inizializzazione GPU restituisce un'eccezione ordinaria, il wrapper
effettua un solo tentativo CPU dopo aver liberato lo scope del tentativo fallito.
È stata rimossa la vecchia ricerca di librerie e il percorso che poteva
costruire due volte il modello.

Un piccolo marcatore tecnico accompagna caricamento e generazione GPU. Si
cancella all'uscita normale, comprese eccezioni Python e cancellazioni. Una
morte nativa del processo lascia il marcatore: al successivo avvio lo stesso
profilo usa la CPU. Questo protegge dal ciclo di crash al riavvio; non recupera
un SIGABRT all'interno del processo già terminato. Anche un arresto forzato
durante l'inferenza può lasciare il marcatore e richiedere un controllo prima
di riabilitare quel profilo.

Cache dei kernel e marcatore stanno in `files/allma_native_cache`, separati
dalla storia e dai backup personali. I test di confronto modificano soltanto
un marcatore tecnico con proprietario identificato, poi lo rimuovono dopo
averne verificato l'identità. Non modificano il modello selezionato o i ricordi.

## Prestazioni native misurate

Prototipo separato, stesso GGUF e sorgente nativa, contesto 2048, batch 512,
flash attention disattivata, CPU con quattro thread per decode e batch.
Continuazione guidata di 64 token identici per confrontare lo stesso lavoro.
I tempi includono prompt e generazione, escludono caricamento del modello
e pipeline Python di ALLMA.

| Caso | Ripetizioni per backend | CPU mediana | GPU mediana | Riduzione del tempo |
|---|---:|---:|---:|---:|
| Prompt 128 token + 64 token | 3 | 9,079 s | 2,207 s | 75,7% |
| Prompt 512 token + 64 token | 2 | 27,878 s | 3,053 s | 89,1% |

Nel caso breve il decode misura circa 12–17 token/s CPU e 33–34 token/s GPU.
Il prototipo fissa anche i thread batch a quattro; il wrapper applicativo
conserva il default nativo per il batch. Le misure native non vengono
presentate come percentuale di accelerazione dell'intera chat.

I 248.320 logits di ciascun punto controllato sono finiti. Le cosine CPU/GPU
osservate vanno da 0,998628 a 0,999687, con stessa scelta top-1 nei punti
confrontati. Il calcolo GPU non è identico bit per bit alla CPU: le risposte
libere possono divergere. Questi controlli numerici non certificano la qualità
semantica di tutte le risposte.

## Costo di avvio

Il primo caricamento GPU nel prototipo, senza cache, ha richiesto circa
40,9 secondi per compilare i kernel. Con cache conservata, i caricamenti
osservati scendono a circa 6,4–8 secondi; la CPU carica il modello in circa
0,8–1,4 secondi. Sono tempi del modello nativo, non dell'intero avvio ALLMA.
La cache prodotta nell'app contiene 197 file e viene conservata tra i riavvii.

Questo costo è il principale compromesso dell'integrazione. Non è stata
ridotta la riserva di ragionamento per far apparire la GPU più veloce.
Non sono disponibili percentuali attendibili di risparmio batteria o calore:
il telefono era alimentato durante le prove.

## Verifiche software e Android

- Suite desktop offline: **2400 passati, 15 saltati, 0 fallimenti**
  su 2415 casi raccolti.
- Selezione backend, fallback, marcatore dopo morte nativa e concorrenza:
  controlli dedicati inclusi nella suite.
- Android: **60/60 scenari software sintetici**, comprese integrazione,
  recupero, isolamento, ciclo di vita, controlli di uscita e persistenza.
  Questi scenari usano un modello simulato; sono distinti dall'inferenza reale.
- Prima Rapida reale sulla GPU: sei casi completati; quattro generazioni
  Qwen registrano `backend=opencl`, due casi sono risolti da ALLMA senza LLM.
  Risposta sì/no e JSON validi. Le risposte aperte conservano limiti del
  modello e richiedono valutazione umana.
- APK verificato: payload, asset, manifest facoltativo, architettura ARM64,
  metadati CPU/OpenCL, assenza di un driver OpenCL incorporato.

## Confronto nella pipeline e arresto termico

La prima Rapida GPU è terminata con batteria da 38,0 a 39,2 °C, durante la
carica. Durate complete dei quattro casi che richiedono il modello:

| Caso | Durata completa GPU | Token generati | Esito |
|---|---:|---:|---|
| N1, sì/no | 11,69 s | 33 | `no`, corretto |
| N3, JSON | 10,33 s | 142 | Oggetto valido e valori corretti |
| N4, emozioni miste | 8,93 s | 101 | Due frasi, attribuzione corretta; revisione umana necessaria |
| N5, spiegazione | 11,22 s | 213 | Tre frasi; spiegazione incompleta, revisione umana necessaria |

N2, calcolo `42`, e N6, assenza di memoria personale, non usano il modello e
richiedono rispettivamente circa 0,083 e 0,075 secondi. Non vengono sommati
alle prestazioni dell'inferenza GPU.

Un secondo avvio, con marcatore sintetico di operazione incompleta, ha
selezionato realmente `backend=cpu`, motivo
`previous_gpu_operation_incomplete`. Sì/no e JSON restano corretti, mentre
la risposta libera N4 non rispetta il vincolo di due frasi: la pipeline
intercetta l'errore. Questi esiti confermano il funzionamento del fallback;
non dimostrano equivalenza semantica CPU/GPU.

Durante il giro CPU la batteria reale ha raggiunto 44,3 °C. Il benchmark è
stato interrotto, il report parziale salvato e l'app messa in pausa dopo il
salvataggio dello stato. Il limite preventivo di 40,5 °C era definito per il
prototipo separato; il successivo confronto applicativo non disponeva dello
stesso controllo esterno prima dell'avvio. Questa lacuna del protocollo è
registrata: un eventuale nuovo confronto deve verificare la temperatura
reale **prima** di partire e durante ogni caso, interrompendosi oltre soglia.
I due helper esterni di confronto ora rifiutano l'avvio sopra 40,5 °C;
con `--start --watch` controllano inoltre la batteria ogni due secondi e
richiedono cancellazione e salvataggio oltre soglia. Il watchdog non cambia
il comportamento della chat ordinaria. Questa modifica al protocollo non
richiede un nuovo APK e non rende retroattivamente valido il giro caldo.

I tempi di quel giro CPU non sono usati per una percentuale end-to-end:
condizioni termiche diverse alterano il confronto. Non è stato avviato un
ulteriore benchmark GPU a telefono caldo. Il marcatore di test è stato
rimosso dopo verifica della sua proprietà; configurazione GPU ripristinata.
Android ha poi bloccato lo schermo, sospendendo il completamento dell'ultimo
avvio. Il controllo successivo, nello stesso processo 18111 dopo lo sblocco,
conferma nuovamente `backend=opencl` e 25/25 livelli GPU. Due generazioni
reali della chat sono terminate rispettivamente in 8,29 e 18,02 secondi.

In queste interazioni HWUI registra però frame da 799 a 2565 ms e fino a
170 fotogrammi saltati. Le pause coincidono con l'inferenza: la contesa tra
OpenCL e composizione della WebView è il principale indiziato, da isolare
con una traccia simultanea prima di attribuirle ogni pausa. La coda OpenCL
usa la priorità predefinita e il microbatch fisico è 512. L'animazione dei
puntini usa già transform e opacity CSS; non è alimentata dai singoli token.
Serve ottimizzare anche la fluidità, non soltanto i token/s. Il telefono
era ancora caldo (42,7 °C alla lettura dei log); non sono state avviate
nuove inferenze pesanti per questa analisi. Evidenze in
`analisi/2026-10-24/animazione-pensiero/diagnosis.json`.

L'interruzione e il salvataggio del report parziale sono riusciti senza
chiusura dell'app. Alla chiusura della 102553 restavano da misurare confronto della pipeline,
cancellazione GPU reale e sessioni lunghe. Il seguito sulla 102555 documenta
fluidità, confronto breve, cancellazione e rientro; restano le sessioni lunghe. Il risultato dei test fissi non è una
percentuale di affidabilità universale.

## Evidenze e riproducibilità

Directory locale: `analisi/2026-10-24/accelerazione-opencl`, esterna alla
cartella del repository. Contiene criteri di accettazione, sorgenti del
prototipo, report e logits sintetici, JUnit desktop, rapporti Android,
verifiche dell'APK e confronto della pipeline.

L'APK precedente 102552 è conservato per un eventuale rollback. L'APK 102553
ha SHA-256 `c3de618ff732ddbcd5bc6368d55f3120e1f0a19206e4af366d5cbeb459685db2`.
Il pubblico numero di versione resta 0.9.1. Questa attività non crea commit,
push o release GitHub.

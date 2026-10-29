# Accelerazione GPU e NPU: analisi e prove — 24 ottobre 2026

> Documento storico: fotografa l'analisi iniziale sulla build 102552.
> L'inferenza Qwen è stata successivamente misurata e OpenCL integrato nella
> build 102553. Per configurazione, risultati e limiti attuali vedere
> [Integrazione OpenCL](INTEGRAZIONE_OPENCL_2026-10-24.md).
> L'inferenza Hexagon è stata successivamente eseguita in un prototipo separato:
> [Prova reale NPU](PROVA_NPU_HEXAGON_2026-10-24.md).

## Esito

La GPU del telefono è utilizzabile da un'app Android ordinaria: una prova
isolata ha eseguito correttamente calcoli reali sia con OpenCL sia con Vulkan.
È stato inoltre riprodotto e rimosso, nella sola app diagnostica, un ostacolo
di accesso alle librerie del produttore presente nel percorso storico di ALLMA.

Questo dimostra la fattibilità dell'accesso e di un kernel semplice. Non è
ancora una dimostrazione di inferenza Qwen accelerata o di un guadagno di
velocità dell'intera app. La NPU ha un percorso nativo concreto, ma qui sono
state verificate soltanto le librerie di accesso e i sorgenti: nessuna sessione
Hexagon o inferenza NPU è stata eseguita.

ALLMA rimane alla build **102552**, versione **0.9.1**, con motore CPU. Non sono
stati cambiati codice applicativo, impostazioni, modelli o dati personali.
Gli APK diagnostici sono stati rimossi e il processo ALLMA è rimasto invariato.

## Telefono e stack osservati

| Voce | Riscontro |
|---|---|
| Dispositivo | Samsung SM-S938B |
| SoC / piattaforma | Qualcomm SM8750 / sun |
| GPU | Adreno 830 |
| Vulkan del driver | 1.3.284 |
| OpenCL | 3.0, driver Qualcomm 0800.64.8 |
| Android riportato dal dispositivo | 17, API 37 |
| Target dell'app | API 34; minimo API 24; ARM64 |
| Motore ALLMA | llama-cpp-python 0.3.36 e librerie native dalla stessa sorgente fissata |
| Modello nel catalogo | Qwen 3 1.7B Q8_0, circa 1,83 GB |
| Secondo modello nel catalogo | Qwen 3.5 2B Q4_K_M, circa 1,28 GB |

Le librerie `libOpenCL.so`, `libcdsprpc.so` e `libadsprpc.so` sono presenti
nell'elenco pubblico del produttore. L'assenza di `libQnnHtp.so` dal percorso
vendor controllato non dimostra assenza della NPU: quella libreria appartiene
a un diverso percorso di distribuzione del runtime e può essere fornita
insieme all'app.

I valori sono conservati in `device-summary.json`, `vulkan.json` e negli
elenchi delle librerie della cartella di evidenza. La lettura della batteria
avveniva durante la carica USB: non viene usata per stimare consumi o vantaggi
termici.

## Perché oggi ALLMA usa la CPU

La ricetta `libs/recipes/llamacpp_android/__init__.py` compila esplicitamente
senza OpenCL e Vulkan; il backend Hexagon risulta disabilitato nel CMakeCache
effettivo. Il wrapper imposta `n_gpu_layers=0` e nasconde i dispositivi Vulkan.
Anche Decider è configurato sulla CPU.

Non basta quindi cambiare un numero nell'interfaccia: mancano i backend
compilati e la configurazione di accesso e selezione del dispositivo. Il
manifest verificato dell'APK non dichiara nessuna `uses-native-library`.

La compilazione CPU osservata usa realmente `-O3` e la base ARMv8-A. KleidiAI
è disattivato; i thread ordinari sono quattro su Android, con un ramo a sei
subordinato allo stato energetico. Non si conclude che aumentare i thread o
compilare indiscriminatamente per il processore più recente migliori il risultato:
compatibilità, carico della UI e prestazioni sostenute richiedono misure.
Le vecchie percentuali di accelerazione scritte nei commenti del wrapper e
di buildozer non costituiscono benchmark verificati.

## Vecchi insuccessi: cause distinte

### Compilazione Vulkan

I log conservati mostrano mancanza di `glslc`, intestazioni Vulkan mancanti o
incoerenti, simboli non risolti come `vkResetQueryPool`, e confusione fra strumenti
host e Android. Sono errori della catena di compilazione, non prove che il
telefono non sappia eseguire calcoli GPU. Sono stati catalogati separatamente
in `historical-build-errors.json`; i numerosi errori di packaging e dei file di
test inclusi nei vecchi log non vengono attribuiti tutti al driver.

### Accesso OpenCL

Il vecchio `android_logs.txt`, righe 4076–4092, registra la libreria presente
ma non accessibile dal namespace dell'app. Android richiede la dichiarazione
delle librerie native del produttore alle app con target API 31 o superiore.
La dichiarazione facoltativa permette di conservare il ripiego CPU sui telefoni
che non offrono quella libreria. [Regola Android ufficiale](https://developer.android.com/guide/topics/manifest/uses-native-library-element).

Il file storico `opencl_stub.c` non risolve questo accesso: i percorsi assoluti
restano soggetti al namespace. Inoltre molte funzioni proxy sono dichiarate
senza parametri e senza il tipo di ritorno OpenCL corretto. Quel codice non
fornisce un inoltro conforme all'ABI e non va riattivato come driver. La ricetta
attuale CPU non lo compila.

### Shader Vulkan su Adreno

Il wrapper conserva un commento su precedenti fallimenti della creazione di
pipeline. Non è stato recuperato qui un log interno che isoli lo shader esatto
di quel fallimento. Le segnalazioni upstream su Adreno 830 documentano problemi
specifici di shader e specializzazione: una pipeline semplice riuscita non
certifica tutti i kernel GGML. La discussione #28635 corregge la propria prima
spiegazione relativa alle versioni NDK; quella spiegazione ritirata non viene
usata come diagnosi di ALLMA. [Segnalazione e correzioni upstream](https://github.com/ggml-org/llama.cpp/issues/28635).

## Prova reale separata sul telefono

Sono stati costruiti due minuscoli APK di diagnostica, package
`org.allma.hardwareprobe`, con target API 34 e lo stesso codice Java/native.
La variante successiva aggiunge soltanto le dichiarazioni delle tre librerie
vendor e cambia il numero di versione. Le impronte del codice DEX e della
libreria di prova coincidono fra le due varianti.

L'esecuzione avviene tramite instrumentation in processi Android reali.
Non si tratta di un eseguibile lanciato dalla sola shell ADB. Non richiede root,
non apre conversazioni e non accede alla cartella privata di ALLMA.

| Controllo | Senza dichiarazioni | Con dichiarazioni |
|---|---|---|
| Caricamento OpenCL | Bloccato | Riuscito |
| Caricamento FastRPC, entrambe le librerie | Bloccato | Riuscito |
| Individuazione GPU OpenCL | Non disponibile | Adreno 830 |
| Calcolo OpenCL e verifica | Non eseguibile | 256/256 risultati corretti |
| Calcolo Vulkan e verifica | 256/256 corretti | 256/256 corretti |

Il kernel trasforma 256 interi con `v[i] = v[i] * 3 + 7`; i risultati vengono
riletti e confrontati con l'atteso. La prova OpenCL comprende compilazione del
programma, buffer, dispatch e lettura. Quella Vulkan comprende shader SPIR-V,
pipeline, memoria, dispatch, sincronizzazione e lettura.

È stata corretta una lettura diagnostica dell'elenco delle estensioni OpenCL:
il primo buffer era troppo piccolo e lasciava il testo del driver precedente.
La versione finale misura la lunghezza e controlla l'esito prima di stampare il
campo. Il primo report resta conservato separatamente; gli esiti dei calcoli
sono confermati anche nella ripetizione finale.

**Limite:** questi kernel non misurano prodotti di matrici quantizzate,
attenzione, stato ricorrente, correttezza dei logits o token al secondo. Le
librerie FastRPC caricate non dimostrano apertura di una sessione DSP o
esecuzione di tensori sulla NPU.

## Percorsi concretamente disponibili

### GPU OpenCL: prima scelta per il prototipo

Il backend upstream mira alle GPU Adreno e comprende la 830 fra i dispositivi
verificati. Supporta le famiglie di quantizzazione usate dal catalogo e conserva
il formato GGUF. [Documentazione OpenCL](https://github.com/ggml-org/llama.cpp/blob/master/docs/backend/OPENCL.md).

Nella sorgente fissata già presente localmente sono riconosciuti anche gli
operatori ricorrenti richiesti da Qwen 3.5. Ciò rende sensato provare per primi
i due file esistenti, mantenendone le impronte. La copertura effettiva delle
forme dei tensori, i passaggi sulla CPU e le prestazioni devono essere osservati
durante l'inferenza, non dedotti dal nome del modello.

Servono una build separata CPU+OpenCL dalla stessa sorgente Python/native,
dipendenze corrette, dichiarazione facoltativa della libreria vendor e selezione
esplicita dei dispositivi. Le cache dei kernel devono avere una directory privata
scrivibile e distinguere modello/runtime/driver: una prima compilazione può
costare più di un'apertura successiva.

### NPU Hexagon nativa: secondo prototipo

llama.cpp offre un backend Hexagon sperimentale per Snapdragon, con libreria
host e kernel compilati per la versione del DSP. Il codice fissato nel progetto
contiene già questo backend e la configurazione per v79, oltre agli operatori
di Qwen 3.5. [Guida Snapdragon](https://github.com/ggml-org/llama.cpp/blob/master/docs/backend/snapdragon/README.md),
[separazione delle librerie host e HTP](https://github.com/ggml-org/llama.cpp/blob/master/docs/backend/snapdragon/developer.md).

Non è obbligatorio convertire a QNN o cambiare modello per iniziare questa
prova. La funzione di capacità della sorgente fissata considera Q8_0 e vari
K-quant, compresi Q4_K e Q6_K, con ulteriori vincoli su layout, dimensioni e
memoria VTCM. Questo è un candidato di compatibilità, non una garanzia di
esecuzione completa dei GGUF attuali.

Qui non sono configurati Hexagon SDK e relativo toolchain; Docker non è
disponibile nel PATH. Vanno preparate librerie host e HTP coerenti, verificata
l'apertura della sessione e controllate tutte le operazioni del modello. La
semplice aggiunta di una libreria o l'attivazione di un'impostazione non basta.

### GenieX / Qualcomm AI Engine Direct: alternativa

Qualcomm documenta anche un SDK Android con selezione CPU/GPU/NPU e un percorso
GGUF, più un percorso con modelli precompilati per il chipset. La versione è
indicata come developer preview. La guida elenca Qwen 3 e Qwen 3.5 e raccomanda
Q4_0 per la propria copertura NPU. Le restrizioni di quella distribuzione non
vanno confuse con le capacità del diverso sorgente GGML fissato in ALLMA.
[Panoramica Qualcomm](https://qualcomm.github.io/qidk/blogs/geniex_android.html),
[API di selezione del motore](https://github.com/qualcomm/GenieX/blob/main/docs/en/run/android/api-reference.mdx).

È un'alternativa da valutare se il percorso diretto non soddisfa i requisiti.
Cambierebbe però l'adattatore di inferenza e, nel percorso AI Engine Direct,
anche il formato/distribuzione dei pesi e i vincoli di contesto. ALLMA dovrebbe
conservare autorità su memoria, identità, strumenti e obiettivi.

Non si propone NNAPI come scorciatoia universale: Android lo ha deprecato.
[Guida di migrazione Android](https://developer.android.com/ndk/guides/neuralnetworks/migration-guide).

## Integrazione richiesta e criterio di scelta

1. Conservare la build CPU come riferimento e compilare il prototipo OpenCL
   separatamente, evitando di mescolare librerie di versioni diverse.
2. Provare operatori, caricamento e generazione dei GGUF esistenti. Registrare
   dispositivo e tensori/livelli realmente assegnati: un backend enumerato o
   un nome nelle impostazioni non dimostra che stia facendo il lavoro.
3. Collegare una selezione del dispositivo verificata. Il binding Python
   di alto livello corrente espone numero di livelli e GPU principale, ma
   non un selettore esplicito dell'elenco `devices`: passare un argomento
   arbitrario attraverso `**kwargs` non è un'integrazione sufficiente.
4. Confrontare stesso modello, prompt, contesto, seed, ragionamento, budget
   della risposta e controlli finali. Separare elaborazione del prompt,
   generazione, primo token interno, prima risposta leggibile e turno totale.
5. Misurare avvio freddo e caldo, prompt corti/lunghi, memoria, annullamento,
   background e cambio modello; poi prove ripetute abbastanza lunghe da
   osservare throttling. Energia e temperatura richiedono condizioni di
   carica e stato termico confrontabili.
6. Preparare allo stesso modo il prototipo Hexagon e confrontarlo. Una diversa
   quantizzazione, se necessaria, va trattata come un secondo esperimento:
   velocità e qualità non sono più un confronto dello stesso file.
7. Scegliere il profilo per telefono, modello e driver. Mantenere un ripiego CPU
   esplicito; errori nativi che arrestano il processo richiedono isolamento
   del collaudo, perché un `try/except` Python non li recupera.

CPU, GPU e NPU condividono memoria e limiti termici. Usarle tutte insieme non
somma automaticamente le velocità; trasferimenti, sincronizzazione, operazioni
non supportate e due modelli residenti possono peggiorare il risultato. Prima
si sceglie il motore migliore per il modello principale; eventuali assegnazioni
separate a Decider o voce vanno giustificate da un confronto successivo.

Accelerare l'inferenza può ridurre attesa e tempo di calcolo, ma non corregge
le conoscenze del modello. Non è necessario ridurre il ragionamento per fare
questo esperimento. Nessuna percentuale di accelerazione, batteria o temperatura
di ALLMA viene dichiarata prima del confronto con inferenza reale.

## Evidenze salvate

Cartella: `/Users/erikahu/ALLMA/analisi/2026-10-24/accelerazione-hardware/`.

- `summary.json`: risultati e confini delle conclusioni.
- `app-process-probes.json`: prove finali, installazione, rimozione e processo ALLMA.
- `baseline-instrumentation.txt`, `declared-instrumentation.txt`: output dei due casi.
- `HardwareProbe.java`, `hardware_probe.c`, `probe.comp`, `build_probe.py`,
  `run_probe.py`: sorgenti e riproduzione della diagnostica.
- `installed-build-manifest.txt`, `source-fingerprints.json`: configurazione e sorgenti.
- `historical-build-errors.json`, `historical-runtime-errors.json`: tracce precedenti.

Controllate le impronte degli undici sorgenti già verificati nella 102552:
invariati. Nessun nuovo commit, push o aggiornamento dell'APK di ALLMA.

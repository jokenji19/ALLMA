# NPU Hexagon — prova reale del 24 ottobre 2026

> Prova iniziale precedente all'integrazione. La build successiva 102556 usa
> [Decider NPU insieme a Qwen GPU](INTEGRAZIONE_NPU_DECIDER_2026-10-24.md).

## Esito

**Qwen 3.5 2B Q4_K_M esegue inferenza reale sulla NPU del Samsung S25 Ultra
testato.** La prova è avvenuta in un APK diagnostico separato, senza root,
senza cambiare la build installata di ALLMA e senza leggere conversazioni,
ricordi o profili personali.

L'accesso non è soltanto un caricamento di librerie: sono documentati apertura
della sessione CDSP, informazioni hardware, esecuzioni HVX/HMX e tempi dei
singoli operatori. Il modello ha completato anche gli operatori ricorrenti
`SSM_CONV` e `GATED_DELTA_NET+CPY`.

ALLMA rimane alla **102555 / 0.9.1**, con CPU e GPU OpenCL. La NPU non è stata
abilitata nella chat. L'APK di prova e la copia temporanea del modello sono
stati rimossi dal telefono; ALLMA è stata riavviata dopo un salvataggio
verificato prima della sospensione.

## Motore e provenienza

- Sorgenti corrispondenti esattamente alla revisione già usata da ALLMA:
  `0c1e57098bba43ac29e6e3b677cdceebdd22334f`.
- [Release ufficiale llama.cpp b11312](https://github.com/ggml-org/llama.cpp/releases/tag/b11312),
  archivio `llama-b11312-bin-android-arm64-snapdragon.tar.gz`.
- Archivio di 57.477.190 byte, SHA256 verificato:
  `831a28efeb992108b84d54c5b7538388eba2978d567175e5cfd9843222c6c03d`.
- Intero runtime coerente della stessa release per tutti i confronti.
  Nessuna sostituzione delle librerie installate di ALLMA.
- Componente host `libggml-hexagon.so` ARM64 e componente DSP
  `libggml-htp-v79.so` ELF32 Hexagon. Il secondo è un asset per il DSP,
  non una libreria ARM64 da caricare con `System.loadLibrary`.
- APK ordinario `org.allma.hexagonbench`, target 34, librerie vendor
  opzionali dichiarate nel manifest e `ADSP_LIBRARY_PATH` privato.
- GGUF pubblico già presente sul Mac: 1.280.835.840 byte, SHA256
  `aaf42c8b7c3cab2bf3d69c355048d4a0ee9973d48f16c731c0520ee914699223`,
  verificato nuovamente dopo la copia nel solo archivio del prototipo.

Questa distribuzione upstream collega staticamente il registro dei backend e
ha dipendenze dirette fra librerie. Non è un plugin da copiare indiscriminatamente
nel runtime dinamico CPU/OpenCL di ALLMA. Un'integrazione richiede un pacchetto
opzionale coerente, con isolamento degli errori e recupero sul motore stabile.

## Verifica dell'hardware

Dispositivo SM-S938B / SM8750, Hexagon **v79**, 6 thread/HVX, 1 HMX,
8 MiB di VTCM riportati dal driver. Registro `HTP0` selezionato esplicitamente.
La query avanzata dei domini restituisce `0x6c`; il percorso di compatibilità
del motore con dominio CDSP statico apre correttamente la sessione.

Sei moltiplicazioni sintetiche, F16/Q4_K/Q6_K con 1 e 16 colonne, hanno superato
il confronto con la CPU. Il candidato usa direttamente il backend Hexagon,
senza scheduler né ripiego CPU. Tolleranze definite prima della prova:
NMSE < 0,001 e massimo errore assoluto < 0,05. NMSE osservati fra circa
2e-8 e 4,6e-6. I log mostrano tre kernel HVX e tre HMX.

## Confronto Qwen

Contesto massimo 2.048, batch/ubatch 512, quattro thread CPU, Flash Attention
disabilitata. Stessi token di input e continuazione imposta per misurare la
stessa quantità di lavoro; tre ripetizioni nello stesso contesto con memoria
azzerata tra i turni. Tempi mediani, escluso il caricamento del modello e la
pipeline applicativa ALLMA.

| Contesto + continuazione | CPU: lettura / generazione / turno | GPU: lettura / generazione / turno | NPU: lettura / generazione / turno |
|---|---:|---:|---:|
| 128 + 64 token | 2,006 / 3,783 / 5,793 s | 0,326 / 1,807 / 2,141 s | 0,121 / 2,210 / 2,333 s |
| 512 + 64 token | non misurato | 1,152 / 2,112 / 3,272 s | 0,354 / 2,172 / 2,533 s |

Sul caso 128+64, il tempo di lettura NPU è inferiore del **62,8%** rispetto
alla GPU; la generazione richiede invece il **22,3%** di tempo in più. Il turno
NPU complessivo è più lento dell'**8,9%** rispetto alla GPU e più rapido del
**59,7%** rispetto alla CPU dello stesso prototipo.

Sul caso 512+64, la riduzione osservata del turno è **22,6%** rispetto alla
GPU. È un risultato esplorativo: le prove sono sequenziali, la terza ripetizione
GPU rallenta sensibilmente e una lettura successiva del servizio termico Android
riporta stato 2. Considerando soltanto il primo turno di ciascun backend,
la riduzione osservata è 14,1%; anche questo confronto non elimina l'effetto
dell'ordine e della temperatura. Ripetere a freddo, alternando l'ordine,
prima di stabilire una politica automatica.

Il prototipo ha completato **20 turni del modello**: 18 con continuazione
imposta e due con generazione libera. Per la domanda sull'arcobaleno, GPU e NPU
hanno prodotto lo stesso testo e 104 token ciascuna, con lo stesso limite di
ragionamento del test. È una verifica puntuale; non dimostra equivalenza della
qualità su tutte le domande. La risposta conserva una lieve imprecisione
scientifica comune ai due backend, quindi non viene classificata come prova
di correttezza generale.

Sono stati esportati e confrontati tutti i 248.320 logits, dopo il prompt e
la continuazione sintetica. Nel caso 128, la similarità coseno NPU/CPU è circa
0,99966 e il token più probabile coincide nei due punti. I valori non sono
identici bit per bit. Non trasformare la similarità numerica in una percentuale
di intelligenza, affidabilità o qualità del dialogo.

## Memoria, calore e limiti

Il buffer dei pesi NPU è 1.319,36 MiB contro 1.211,14 MiB OpenCL; il buffer
di calcolo è circa 493 MiB in entrambi. Sono allocazioni del motore, non una
misura del picco RSS o della RAM totale del processo. Non è dimostrata una
riduzione di memoria con la NPU.

Il telefono era in carica: non sono disponibili joule/token o misure affidabili
del consumo e dell'autonomia. La temperatura batteria non ha superato 37,9 °C
nei campioni raccolti, ma non basta per escludere limiti termici di altri
componenti. Dopo lo stato termico 2 è stato interrotto il proseguimento delle
prove pesanti. Il runner ora controlla sia temperatura batteria sia stato
termico Android e rifiuta/interrompe una prova con stato >= 2 o mancante.
Questa protezione aggiuntiva non era attiva nelle misurazioni sopra riportate.

Il prototipo usa il runtime upstream senza le personalizzazioni di priorità
OpenCL della build 102555; non è un confronto end-to-end con la chat installata.
I tempi di caricamento osservati, generalmente 6–10 s per NPU e GPU calda,
non sono un esperimento controllato a cache fredda. Il primo caricamento GPU
ha richiesto circa 38 s per preparazione/cache. Non includere questi tempi
nel confronto del turno già caricato.

## Decisione tecnica

Il percorso nativo NPU è fattibile per questo hardware e questo GGUF. Conviene
proseguire con un backend opzionale orientato ai contesti lunghi, misurando
prima la scelta del motore su turni rappresentativi dell'app. La GPU mantiene
un vantaggio nella generazione dei casi brevi misurati.

Non è stato realizzato un funzionamento contemporaneo CPU+GPU+NPU dello stesso
turno. Dividere lettura e generazione fra NPU e GPU richiede gestione di pesi,
stato ricorrente e trasferimenti; il guadagno non è la somma dei due motori.
Il caricamento doppio e il cambio motore a ogni messaggio possono annullarlo.

Prima dell'attivazione nella chat restano: confronto a freddo con ordine
alternato e prompt realistici, picco RAM e durata, cancellazione reale,
salvataggio/rientro, recupero da errore nativo e protezione del modello
persistente di ALLMA. Non cambiare identità, apprendimento o budget di
ragionamento per ottenere un punteggio di velocità migliore.

## Evidenza riproducibile

Cartella locale `/Users/erikahu/ALLMA/analisi/2026-10-24/npu-hexagon/`:

- `official-release.json`, `runtime-files.json`, `model.json`: provenienza e impronte.
- `tensor-smoke-case.json`, `tensor-summary.json`: sei calcoli e prova HVX/HMX.
- `qwen-smoke-native.log`, `qwen-dsp-operators.json`: inferenza e operatori sul DSP.
- `comparison-128.json`, `comparison-512-gpu-npu.json`, `final-summary.json`: misure e limiti.
- `*-case.json`, `*-logits.bin`: turni sintetici, tempi e risultati numerici.
- `build_bench.py`, sorgenti JNI/Java, `run_case.py`, `compare.py`: riproduzione.
- `android-lifecycle.json`, `cleanup.json`: salvataggio e rimozione del prototipo.

L'APK diagnostico contiene soltanto il componente DSP v79 e non è distribuito
come release di ALLMA. Nessuna compatibilità con altri telefoni o altri modelli
è stata dimostrata da queste prove.

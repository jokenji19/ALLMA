# Componenti nativi della release 0.9.1.1

Il runtime vocale ARM64 e i suoi sorgenti sono invariati rispetto alla 0.9.1: vedere `THIRD_PARTY_SOURCES.md` e `VOICE_SOURCE_MANIFEST_0.9.1.json`. La release 0.9.1.1 riallega il medesimo archivio, rinominato `ALLMA-0.9.1.1-voice-sources.tar.gz`; SHA-256 `06596a4dc59840b8fc3045aa335936b906199c2163d3672b0cb358b7c2777487`. Le licenze, incluso GPL-3.0-or-later per eSpeak NG, rimangono applicabili alla distribuzione del binario combinato.

## CPU e GPU

`libs/recipes/llamacpp_android/__init__.py` fissa llama-cpp-python 0.3.36, archivio sorgente SHA-256 `832db0699007f1be95a7e41ef12e88926b02ba836461e36a36372db2760c1a2e`, URL e SHA-512 nella ricetta. Il runtime CPU e il plugin OpenCL sono compilati dalla stessa sorgente; le modifiche locali sono in `libs/recipes/llamacpp_android/patches/`. llama.cpp e llama-cpp-python conservano le rispettive licenze MIT e avvisi upstream. Il codice di compilazione installa un runtime ARM64 con backend dinamici; non sostituisce il driver OpenCL del produttore.

OpenCL-Headers e OpenCL-ICD-Loader 2025.07.22 sono dipendenze di compilazione fissate nelle relative ricette; il loader usato per il linking non viene incorporato come `libOpenCL.so` nell'APK. Il telefono deve offrire il proprio driver. Gli avvisi e le licenze upstream rimangono applicabili.

## Hexagon opzionale

I due componenti in `libs/native_backend/hexagon/` provengono dalla release upstream llama.cpp `b11312`, commit `0c1e57098bba43ac29e6e3b677cdceebdd22334f`. `manifest.json` documenta l'archivio di origine, gli hash originali e quelli distribuiti. La libreria host è stata sottoposta soltanto a stripping dei simboli non necessari; il componente DSP è conservato come dati `.so.bin`, senza spacciarlo per un eseguibile ARM64.

Il file `LICENSE.txt` della stessa directory conserva l'avviso MIT upstream. `tools/vendor_hexagon.py` verifica l'archivio e i singoli componenti prima di estrarli. I due componenti verificati sono inclusi nei sorgenti della release affinché un checkout pulito non dipenda dalla cache privata del computer di sviluppo. Le restanti librerie FastRPC e i driver appartengono alla piattaforma Android del dispositivo e non vengono ridistribuiti da ALLMA.

Le sorgenti upstream corrispondenti sono disponibili all'URL fissato nel manifest; le ricette e le patch locali sono incluse nell'archivio sorgente ALLMA. L'accesso al runtime nativo non garantisce il supporto NPU su ogni telefono.

## Verifica dell'aggiornamento

L'APK `0.9.1.1` dichiara versionCode `102593`, API minima 24 e target 34. La firma SHA-256 del certificato coincide con quella dell'APK 0.9.1: `b4287bcd0c64934b0b1f8870d1c15b815787b687e33228afc6ab7c05f95af36a`. È una firma debug per collaudo; non è la firma di una pubblicazione Play.

Modelli GGUF e dati delle voci opzionali non sono incorporati negli archivi sorgente: ciascun modello mantiene la propria licenza e i propri checksum nel catalogo applicativo.

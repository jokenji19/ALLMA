# ALLMA V0.9.0.0

Questa versione raccoglie gli aggiornamenti di ALLMA alla revisione `4c146ee`, con versione Android allineata a `0.9.0.0` e versionCode `102457`.

## Novità

- Collegamento nativo ai modelli GGUF, template dai metadati, selezione e cambio modello nel backend conservando identità e memoria.
- Calcolo aritmetico esatto per le espressioni supportate e identità nominale ALLMA indipendente dal modello.
- Descrizione delle capacità operative, gestione dei follow-up e controlli sulle ripetizioni, sul formato e sull’attribuzione delle esperienze.
- Riconoscimento delle emozioni miste, delle negazioni e delle evidenze emotive nei messaggi.
- Apprendimento tramite conferme esplicite, memoria e persistenza; invio progressivo adattivo delle risposte.
- Diario Sogni con verifica, correzione e scarto delle ipotesi.
- Interfaccia Android coerente, introduzione animata e miglioramenti della modalità vocale e di STT/TTS.
- Benchmark e diagnostica con metriche, interruzione e salvataggio parziale.

## Pacchetto Android

APK `ALLMA-V0.9.0.0-arm64-v8a.apk`, Android 7.0/API 24 o superiore, package `org.allma.allma_prime`, ARM64. Si tratta della build **debug firmata per il collaudo**, distribuita come download GitHub; non è una build di produzione per Google Play. Il modello linguistico non è incluso nell’APK: segue la procedura di download già presente nell’app.

Per aggiornare la precedente build con la stessa firma, installare l’APK senza disinstallare ALLMA. La reinstallazione da zero può eliminare i dati locali. Il file `SHA256SUMS.txt` consente di verificare l’integrità del download.

## Verifiche

Ultima suite del codice applicativo: **856 test superati, 15 saltati**. Collaudo sul telefono completato per calcolo `42`, nome ALLMA e descrizione delle capacità senza LLM. L’APK di questa release viene ricompilata per aggiornare soltanto i metadati di versione; il payload applicativo corrisponde ai sorgenti. Manifest verificato: versionName `0.9.0.0`, versionCode `102457`, API minima 24, ARM64. Firma APK valida e uguale a quella della precedente build 0.56.

## Limiti conosciuti

La qualità generale delle risposte, la latenza, la temperatura e il consumo energetico richiedono ancora miglioramenti e misure controllate. Il supporto a modelli alternativi è vincolato al runtime e alle risorse del dispositivo; manca un selettore Android per il cambio GGUF. L’inventario delle capacità non certifica il funzionamento di ogni servizio esterno. La visione resta una priorità successiva.

SHA256 APK: `2b512743f9cc53cc51d29d558c3220c1d10e03a07a45101780b2ee7427443206`.

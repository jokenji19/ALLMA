# ALLMA 0.9.1

Aggiornamento del 21 ottobre 2026. Versione Android `0.9.1`, versionCode `102539`, package `org.allma.allma_prime`, ARM64, Android 7.0/API 24 o superiore.

## Novità rispetto a 0.9.0.0

- Selettore dei modelli nell'app, Qwen 3 e Qwen 3.5 2B, cambio del motore conservando identità e stato persistente.
- Decider locale operativo per proposte di instradamento e priorità, con azioni vincolate e controllate da ALLMA.
- Richiamo documentato dei dati personali, correzioni, revoche e gestione dei conflitti; recupero degli aggiornamenti di apprendimento dopo interruzioni.
- Personalità e coalescenza: preferenze dichiarate, riscontri sull'utilità delle risposte, significati emotivi personali e distinzione fra esigenze momentanee e tendenze persistenti.
- Sensibilità al contesto recente, emozioni negate e miste, distinzione fra utente e altre persone, ascolto e aiuto pratico.
- Strumenti esatti per calcoli e conteggi, Unicode e richieste di chiarimento; apprendimento delle strategie d'uso attraverso riscontri espliciti.
- Copie private verificate, esportazione cifrata e ripristino controllato; diagnostiche sintetiche per memoria, conservazione e storie lunghe.
- Schermate interne per impostazioni, memoria e diario, navigazione Indietro, nuova introduzione e visualizzazione del cervello con attività osservata dei moduli.
- Notifiche Android opzionali con consenso e icona ALLMA.
- Voce: gestione delle sessioni e delle disconnessioni, opzioni di lingua, voci italiane naturali opzionali Sara e Nicola, generazione audio separata dalla riproduzione e correzione delle pause fra frasi e numeri.
- Benchmark ampliati, interruzione e report parziali, controlli del formato, dell'attribuzione e delle ripetizioni.

## Verifiche

La raccolta completa sul Mac comprende **2.089 casi: 2.074 superati e 15 saltati**, più **7 script JavaScript superati**. Tre prove di recupero inizialmente bloccate dall'avvio OpenMP nella sandbox sono passate nella ripetizione mirata. I casi saltati restano dichiarati; i conteggi non misurano l'intelligenza o l'affidabilità universale.

Sulla build applicativa precedente al solo aggiornamento di versione sono state confermate sul telefono: risposta vocale esatta `42`, cambio di argomento verso l'arcobaleno, richiamo del contesto recente, arresto della voce con Home e ripresa al rientro. Questa release conserva quel codice applicativo.

## Installazione

Scaricare `ALLMA-0.9.1-arm64-v8a.apk` e verificarlo con `SHA256SUMS.txt`. È una **build debug firmata per il collaudo**, come la release precedente, non una distribuzione Google Play. Modelli conversazionali e dati vocali opzionali vengono scaricati separatamente dall'app.

Per conservare i dati, aggiornare l'installazione esistente con la stessa firma, senza disinstallare ALLMA. È disponibile anche l'esportazione cifrata della storia nelle impostazioni.

## Sorgenti e dipendenze

Il tag della release identifica i sorgenti ALLMA; gli allegati comprendono le informazioni e i sorgenti delle dipendenze vocali native, con le rispettive licenze. La licenza dei file originali ALLMA non sostituisce le licenze dei componenti incorporati. Consultare gli avvisi in `assets/web/licenses/` e la documentazione dei sorgenti allegata.

## Limiti conosciuti

Questa versione pubblica lo stato attuale e **non include correzioni non ancora applicate dell'audit del 21 ottobre**. Restano da affrontare in particolare: consegna persistente dei messaggi proattivi, validità temporale dei sensori, crescita degli archivi e dell'indice, limite della cache delle risposte apprese, completezza di alcune preferenze nei backup e migliore uso della percezione. Il rapporto completo è in [AUDIT_SISTEMA_2026-10-21.md](AUDIT_SISTEMA_2026-10-21.md).

La qualità delle risposte dipende anche dal modello collegato. Le lingue riconoscibili offline dipendono dai dati Android installati; il riconoscimento emotivo locale non ha la stessa copertura in tutte le lingue. L'apprendimento acustico della pronuncia personale non è implementato. La visione resta una fase successiva.

## Integrità dell’APK

SHA-256: `06d7634dcd4919a4c7174a433260d0f35fc463ffc87b3c0ebdf9d328e7fc319a`.

Manifest verificato: versione `0.9.1`, versionCode `102539`, API minima 24, ARM64. Firma valida e corrispondente alla build precedente. Payload applicativo e risorse iniziali corrispondenti ai sorgenti; il pacchetto verificato non include gli archivi personali e i log rimossi dal tracciamento Git.

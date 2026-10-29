# NPU per Decider, GPU per Qwen — build 102556

La build **102556 / 0.9.1** è installata e collaudata sul Samsung S25 Ultra
SM8750. Decider utilizza Hexagon v79; Qwen 3.5 mantiene il motore OpenCL e la
gestione della fluidità della 102555. I log della stessa istanza Android
confermano entrambi i backend e la pipeline operativa.

## Divisione del lavoro

| Hardware | Compito |
|---|---|
| CPU | Stato persistente di ALLMA, memoria, regole, controlli, organizzazione e supporto ai motori nativi |
| NPU | Lettura del contesto di Decider 0.8B e calcolo dei punteggi delle alternative |
| GPU | Ragionamento e risposta di Qwen 3.5 |

Decider continua a proporre risorse e priorità. ALLMA conserva la decisione
sull'esecuzione, i controlli e l'autorità sul proprio stato. Il checkpoint,
la temperatura 1,03 dei punteggi, la soglia 0,80, il margine 0,20 e la memoria
azzerata fra richieste non cambiano. Non sono stati ridotti i budget di
ragionamento o risposta di Qwen e non viene caricata una seconda copia di Qwen.

L'accelerazione segue l'impostazione esistente «Usa Decider»: disabilitare
Decider continua a impedirne l'uso. Non è una nuova attivazione delle azioni.

## Perché questa soluzione

Sono state provate anche due divisioni dello stesso Qwen fra NPU e GPU,
assegnando i blocchi a un dispositivo e la proiezione finale all'altro.
L'esecuzione in un solo contesto riesce, ma il trasferimento introduce un
compromesso: sul caso breve 128+64 token, NPU+GPU richiede circa 2,46 s contro
2,30 s GPU; sul caso 512+64, circa 2,43 s contro 3,05 s. Le condizioni termiche
di queste prove non sono identiche. Non è una scelta generale sufficientemente
vantaggiosa da sostituire il motore di chat già verificato.

Decider esegue essenzialmente prefill e una lettura dei punteggi, senza una
lunga generazione. Sfrutta quindi il vantaggio misurato della NPU nella lettura
del contesto, senza trasferire avanti e indietro lo stato ricorrente di Qwen.

## Misure controllate sul telefono

Checkpoint Decider identico alla versione precedente: 529.297.504 byte,
SHA256 `5cb5d042a236add5cde5459f8e8b8f8f80161ad4a1779a49377b70a64eb7b11a`.
Due ripetizioni di otto casi EN/IT già presenti nel progetto e di un caso
lungo aggiuntivo, con due thread CPU e ubatch 256.

| Caso | CPU: mediana | NPU: mediana | Riduzione del tempo |
|---|---:|---:|---:|
| Otto casi brevi, 81–86 token | 622,8 ms | 68,8 ms | 88,95% |
| Caso lungo, 482 token | 5.044,6 ms | 282,6 ms | 94,40% |

I 18 confronti mantengono le stesse **scelte accettate e astensioni**.
Le probabilità non sono identiche: nei casi ambigui il modello può anche
cambiare la proposta più probabile, mantenendola sotto soglia. Questi test
non dimostrano che ogni possibile classificazione sia identica sui due backend.
Le sei operazioni F16/Q4_K/Q6_K sono state inoltre ripetute con successo sul
motore dinamico effettivo di ALLMA, prima dell'integrazione Python.

La prova di coesistenza ha mantenuto Qwen caricato sulla GPU durante 18
valutazioni NPU di Decider e ha ripreso il medesimo contesto Qwen con logits
finiti. La verifica nativa puntuale del logit conservato non sostituisce una
valutazione generale della qualità; la pipeline applicativa è stata verificata
separatamente come descritto sotto.

## Collaudo dentro ALLMA

- Build 102556 verificata prima dell'installazione: sorgenti incorporati,
  Python/C ABI, selezione esplicita dei dispositivi, impronte dei componenti,
  licenza, schermata iniziale e KivyMD 1.2.0.
- Diagnostica Decider: **8/8 casi completati**, sei scelte corrette, due
  astensioni, nessuna scelta errata accettata. Tempi circa 79–103 ms, inclusi
  preparazione Python e controlli. Due cicli di azioni su fixture sintetiche
  sono inclusi nel report e non modificano la memoria dell'utente.
- Benchmark Rapida: **6/6 casi completati**. Le sei risposte e i conteggi dei
  token coincidono con il report salvato della 102555. Decider usa Hexagon
  nella pipeline operativa e Qwen usa OpenCL.
- Fluidità: 3.221 campioni WebView, massimo intervallo rAF 25 ms, nessun
  intervallo >100 ms. Frame Android: massimo osservato 26,3 ms.
- Background/rientro: salvataggio osservato prima del ritorno; stesso processo,
  rientro verificato, nessun nuovo traceback, fatal signal o errore di pausa.
- Marcatori delle operazioni native rimossi al completamento; impostazioni
  temporanee dello schermo ripristinate.

Nel confronto salvato Rapida, la somma delle durate passa da **40,86 s a
30,17 s**. È un dato prima/dopo esplorativo: temperatura e condizioni non
sono identiche, quindi non attribuire l'intera riduzione alla NPU. Il confronto
controllato sopra riguarda il solo Decider.

Il primo caricamento operativo di Decider rimane costoso: circa **6,16 s**
nel nuovo giro contro 6,76 s nel giro precedente. I successivi passaggi
operativi misurati scendono da circa 1,19–1,39 s a 82–95 ms. Il beneficio
non significa che ogni risposta inizi sempre in 70 ms: Qwen e il resto della
pipeline conservano i propri tempi.

## Implementazione e recupero

Il componente opzionale proviene dalla release ufficiale llama.cpp b11312,
alla stessa revisione `0c1e57098bba43ac29e6e3b677cdceebdd22334f` del motore
già usato da ALLMA. L'archivio, il componente host e il componente DSP hanno
impronte verificate. `tools/vendor_hexagon.py` riproduce l'estrazione; la
licenza è inclusa nel pacchetto. Non è necessario distribuire l'SDK Hexagon.

Il componente ARM64 è caricato in modo opzionale e registrato tramite
l'API nativa del medesimo motore. Lo scheletro DSP v79 viene distribuito come
`.bin`, verificato e collocato nella cache privata come `.so` per FastRPC.
Non viene presentato al caricatore Android come libreria ARM64.

Il binding Python espone il campo `devices` già previsto dall'ABI C. Qwen
seleziona esplicitamente `GPUOpenCL`, Decider `HTP0`; un ripiego CPU usa una
lista vuota esplicita. Registrare la NPU non cambia quindi implicitamente
il dispositivo degli altri modelli o dei caricamenti successivi.

La selezione NPU richiede il profilo misurato SM8750, componenti corrispondenti
e impronta FastRPC `60f7d28f535a3bb589e44073d1c092015682b73cbe994cdbcc132d2624a5c00a`.
Hardware/driver diversi, componenti mancanti o non integri e inizializzazione
fallita conservano il Decider CPU. Lo stato termico è controllato prima
della selezione e prima dell'inferenza NPU; se non è disponibile o è >=2,
la richiesta NPU non viene eseguita.

Un arresto nativo lascia `npu-decision-pending.json`: al successivo avvio il
profilo NPU viene escluso. Questo marcatore è indipendente da quello GPU;
un problema NPU non disattiva automaticamente la GPU verificata. La normale
eccezione Python pulisce il marcatore e consente il ripiego CPU.

## Test software e compilazione

- **86 test mirati passati**, inclusi isolamento GPU/NPU, driver non misurato,
  integrità dei componenti, errore di caricamento NPU con ripiego CPU,
  interruzione e blocco termico.
- **2.423 test passati e 15 saltati** nella suite desktop in sandbox.
- I tre test di arresto improvviso che necessitano della memoria condivisa
  OpenMP del Mac sono stati eseguiti separatamente fuori sandbox: **3 passati**.
  Totale verificato nei due ambienti: **2.426 passati, 15 saltati**.
- I tentativi di eseguire l'intera suite fuori sandbox e in parallelo con la
  compilazione non sono stati usati come esito finale: hanno incontrato
  esaurimento temporaneo dello spazio del Mac. I test finali e il packaging
  sono stati separati.

La compilazione ha fatto emergere un ambiente pip generato incoerente e la
risoluzione non vincolata di dipendenze nuove. Sono state conservate le
versioni della 102555 in `android-build-constraints.txt`. La compatibilità
p4a per riconoscere distribuzioni già installate, come Kivy-Garden che si
importa come `garden`, evita reinstallazioni ripetute. La patch riproducibile
è in `libs/patches/`; `tools/build_android_safe.py` la applica quando necessaria.

Il controllo dell'APK ha verificato le impronte dopo lo stripping effettivo
di Android, evitando componenti dichiarati corretti ma modificati durante
il packaging. Il prototipo separato e i suoi modelli temporanei sono stati
rimossi dal telefono.

## Limiti

Le percentuali sopra misurano latenza, non intelligenza o affidabilità generale.
Non sono stati misurati joule/token, autonomia o un miglioramento termico
sostenuto. Sono stati collaudati questo telefono, questo driver e questi
checkpoint; nessuna attivazione NPU universale su Android viene implicata.
La memoria e la personalità persistenti di ALLMA non sono state usate come
fixture né esportate nelle prove.

## Artefatti

Evidenza in `/Users/erikahu/ALLMA/analisi/2026-10-24/npu-collaborazione/`:
`decider-summary.json`, `integration-summary.json`, `android-decider-result.json`,
`npu_assist/quick.json`, `npu_assist/result.json`, `android-lifecycle.json`,
`apk-verification.json`, `desktop-regression-sandbox.log` e
`desktop-shared-memory.log`.

APK: `bin/allma_prime-0.9.1-arm64-v8a-debug.apk`.
SHA256: `527f77f2e12cf406ca8b8b2b6f547ebee88ed4fc18e9a2f028992dc6c2323457`.
Le modifiche sono locali; questo intervento non crea commit, push o release.

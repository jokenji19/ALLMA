# Collaudo della struttura ALLMA — 6 ottobre 2026

## Esito finale

- Suite completa dopo le correzioni: **559 test superati, 15 saltati**, nessun fallimento; 13 warning di dipendenze. Durata 51,93 s.
- **20 controlli browser passati** su doppio invio, streaming, cambio chat, cancellazione, sicurezza del Markdown e rappresentazione dei numeri/liste.
- Build ARM64 compilata, payload verificato e installazione con `adb install -r` riuscita.
- APK SHA256: `0bf124519b71c6764b20e7d4a2d1ef3b94a8bd2573bb20a9bcc11443277fc8a2`.
- Confronto dei file `allma_memory.json` e `cognitive_state.json` prima/dopo l'aggiornamento: **identici byte per byte**. Nessuna disinstallazione o cancellazione dati.
- JavaScript estratto sul telefono identico al sorgente corretto: SHA256 `47f6a9e171e5f8f50224a700f683ad04e0a07b9ddd6228f29d42998a57022dc0`.
- Avvio finale: coalescenza attivata e TTS ready; nessun traceback Python o errore di inizializzazione nei log acquisiti.

## Difetti riprodotti e corretti

1. **Aggiornamenti simultanei dei concetti:** il ciclo SQLite lettura/modifica/scrittura poteva perdere campi scritti da un'altra connessione. Ora acquisisce il lock di scrittura prima della lettura con `BEGIN IMMEDIATE`. Test con 40 aggiornamenti indipendenti su 12 worker.
2. **Interoperabilità delle emozioni:** la coalescenza chiamava `.lower()` su un enum e poteva memorizzare un oggetto esterno non serializzabile. Ora normalizza enum/stringa e intensità e salva il formato emotivo interno supportato.
3. **Risultati numerici alterati dall'interfaccia:** la risposta salvata `87.` era interpretata come una lista vuota; la sanitizzazione rimuoveva `start`, facendo apparire `1.`. Le righe numeriche isolate rimangono testo e le vere liste conservano il numero iniziale validato. I controlli di sicurezza del Markdown restano attivi.
4. **Falsa tristezza:** «Rispondi solo con il numero» attivava la tristezza per il termine «solo». Ora la solitudine richiede espressioni pertinenti, come «mi sento solo» o «mi sento sola»; i vincoli sul formato non sono trattati come emozioni.

La prima suite dello stato precedente passava 553 test: i nuovi casi hanno riprodotto due fallimenti che non erano coperti. I difetti del numero visualizzato e della tristezza sono emersi dal telefono. Le prove iniziali e finali sono conservate tra gli artefatti.

## Prove reali sul Samsung SM-S938B

Tre richieste nella chat di prova, attraverso la UI e con il modello GGUF del telefono; nessuna risposta sostitutiva predisposta. Le due inferenze precedono le correzioni; le metriche non costituiscono un confronto prima/dopo.

| Richiesta | Esito | Generazione | Primo segmento risposta | CPU | Batteria (sensore) |
|---|---|---:|---:|---:|---:|
| Come ti chiami? | Mi chiamo ALLMA; percorso identitario | Nessun LLM | Non misurato | Non misurata | Non misurata |
| Calcola 23 per 7 e spiegalo in due frasi | 161, calcolo corretto; usa impropriamente «dividendo» per la scomposizione | 17,64 s; 186 token; stop | 14,51 s | 49,0 → 63,3 °C | 40,4 → 40,4 °C |
| Quanto fa 29 per 3? Rispondi solo con il numero | 87, ma aggiunge anche l'equazione; prima della correzione UI mostrava 1 | 9,20 s; 78 token; stop | 8,50 s | 47,8 → 63,7 °C | 40,4 → 40,4 °C |

Il modello sa risolvere questi due calcoli, ma non rispetta sempre il formato richiesto e non garantisce una buona spiegazione. Non sono stati inseriti risultati hardcoded o correttori specifici delle domande. Il ragionamento ha raggiunto il budget in entrambi i casi; la riserva della risposta ha comunque permesso un finale completo.

## Limiti

Queste prove non verificano tutta l'intelligenza, l'apprendimento o la qualità etica. La temperatura CPU arriva ancora a circa 64 °C; la batteria era già a 40,4 °C e il telefono era collegato via USB: non è stimabile il consumo energetico o l'autonomia. Non ripetute prove vocali con parlato umano o l'intero benchmark cognitivo. Persistenza, cancellazione e vincoli energetici dei sogni sono verificati automaticamente; nessuna conferma automatica di ipotesi oniriche come conoscenza.

Artefatti: `/Users/erikahu/ALLMA/analisi/2026-10-06/collaudo-struttura`.

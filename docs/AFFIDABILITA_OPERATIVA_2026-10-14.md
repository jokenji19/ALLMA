# Affidabilità operativa ALLMA — batteria v1, 14 ottobre 2026

**Risultato osservato: 95% — 57 scenari riusciti su 60.**

Questo è il tasso di superamento della batteria di affidabilità software sul codice locale attuale. Non è una stima universale della probabilità che ALLMA risponda correttamente, né una percentuale di perfezione del progetto. Non certifica l’APK installata.

## Metodo

Sei categorie con dieci scenari ciascuna. Ogni scenario vale uno e deve rispettare tutte le sue condizioni; formula `100 × scenari superati / 60`. Il piano e i criteri sono scritti prima dell’esecuzione. I risultati negativi restano nel punteggio. Nessuna modifica al codice del prodotto durante la misura: hash dei sorgenti verificati e invariati.

Dati sintetici e archivi temporanei separati, cancellati dopo i test. Le prove del core utilizzano i sistemi reali con risposte del modello programmate: verificano origine, contenimento di output errati e persistenza, **non la qualità del GGUF**. La prova della cancellazione nativa usa un iteratore simulato. La batteria contiene varianti correlate e casi già affini alle regressioni: non è un campione casuale di tutte le situazioni d’uso. Non viene calcolato un intervallo di confidenza per l’utilizzo reale.

## Risultati per categoria

| Categoria | Superati | Totale | Riuscita |
|---|---:|---:|---:|
| Persistenza e riavvio | 10 | 10 | 100% |
| Errori e recupero | 8 | 10 | 80% |
| Isolamento utenti | 10 | 10 | 100% |
| Controlli e streaming | 9 | 10 | 90% |
| Cancellazione e concorrenza | 10 | 10 | 100% |
| Integrazione core con LLM di prova | 10 | 10 | 100% |

## Tre fallimenti riprodotti

1. **Salvataggio di un messaggio fallito:** il file precedente rimane integro, ma il messaggio non salvato resta in RAM. Memoria attiva e disco divergono; una ripetizione dell’operazione può duplicarlo. Criterio: una scrittura fallita non deve risultare applicata allo stato attivo.
2. **Salvataggio del contesto fallito:** dopo l’errore il nuovo valore rimane in RAM, mentre il disco conserva quello vecchio. Criterio: stesso rollback coerente per aggiornamenti di contesto.
3. **Vincolo sulle frasi con citazione:** `"Prima". Seconda. Terza.` viene accettato dal controllo che richiede due frasi, perché il parser considera ambigui i testi citati e li lascia passare. Criterio: un risultato noto di tre frasi non soddisfa il formato richiesto di due.

Tutti e tre sono stati ripetuti con nuovi archivi temporanei **tre volte ciascuno**, riproducendo il difetto ogni volta. Le nove ripetizioni non sono sommate ai 60 scenari né usate per aumentare artificialmente la numerosità.

Soluzioni: rollback o staging delle mutazioni prima del commit del messaggio e del contesto; conteggio capace di trattare citazioni oppure gestione esplicita dell’incertezza del formato.

## Relazione con i 965 test precedenti

La suite precedente aveva 965 test superati e 15 saltati. Questi tre invarianti nuovi non erano verificati da quelle regressioni. Una suite verde non dimostra assenza di difetti. I conteggi delle due batterie non sono combinati in una percentuale globale.

## Android e limiti

Il telefono Samsung SM-S938B è collegato. Il package `org.allma.allma_prime` riporta versione 0.9.0.0, versionCode 102457, ultimo aggiornamento 2026-10-14 11:23:43. L’APK precede le ultime correzioni locali: non viene incluso nel 95%. Nessuna nuova APK installata, nessun dato personale del telefono copiato e nessuna conversazione reale usata per questa batteria.

Restano fuori dalla misura: qualità delle risposte del modello, comportamento nativo di microfono/TTS/WebView, resistenza su sessioni lunghe, crescita degli archivi, consumo energetico, temperature reali e recupero dopo terminazione Android. Per l’affidabilità complessiva sul telefono il risultato è ancora **non misurato**.

## Riproduzione

Dal repository:

```sh
KIVY_NO_ARGS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 python3 tools/measure_reliability.py --output /private/tmp/allma-reliability-replay
```

Il primo tentativo del runner è stato interrotto dal parsing degli argomenti di Kivy; è conservato come `attempt-1-harness-cli-error` e non valutato come fallimento di ALLMA. Il runner è stato corretto impostando `KIVY_NO_ARGS=1` e poi ha eseguito tutti e 60 i casi senza modificare criteri o prodotto.

Piano: [plan.json](/Users/erikahu/ALLMA/analisi/2026-10-14/affidabilita/plan.json). Risultati: [results.json](/Users/erikahu/ALLMA/analisi/2026-10-14/affidabilita/results.json). Riepilogo: [summary.json](/Users/erikahu/ALLMA/analisi/2026-10-14/affidabilita/summary.json). Ripetizioni: [failure-replays.json](/Users/erikahu/ALLMA/analisi/2026-10-14/affidabilita/failure-replays.json). Runner: [measure_reliability.py](/Users/erikahu/ALLMA/ALLMA_V4/tools/measure_reliability.py).

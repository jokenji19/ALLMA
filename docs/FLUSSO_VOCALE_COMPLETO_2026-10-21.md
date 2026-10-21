# Flusso vocale completo — 21 ottobre 2026

## Versione verificata

Build Android **102538**, versione applicativa 0.9.0.0. APK compilata, contenuto verificato e installata durante il collaudo.

SHA-256 APK: `7d77aa5512e41130c8f5996d5d6042f37306ad7d2464b9c3f7bb8d884b4f6997`.

Evidenze locali: `/Users/erikahu/ALLMA/analisi/2026-10-21/flusso-vocale-completo/`.

## Difetti trovati e corretti

1. **Audio a scatti fra frasi e numeri.** La scrittura audio bloccante avveniva sul worker di generazione: la frase successiva attendeva la riproduzione della precedente. Ora generazione e riproduzione hanno worker separati e una coda limitata a quattro segmenti. Una riserva iniziale fino a due secondi evita di leggere un piccolo titolo e poi fermarsi ad aspettare la frase. I titoli numerati sono normalizzati senza modificare numeri decimali e versioni.
2. **Calcolo vocale inviato inutilmente al modello.** La trascrizione «Quanto fa 18 + 24 rispondi con un solo numero» non attivava il calcolo esatto perché la formulazione del formato non era riconosciuta. Ora restituisce `42` attraverso lo strumento esatto, senza generazione LLM.
3. **Risposta numerica precedente riutilizzata sul cambio di argomento.** Il controllo di continuità non intercettava una breve risposta puramente aritmetica a una nuova richiesta esplicita di spiegazione. Il controllo ora riconosce questo caso anche prima della visualizzazione progressiva. Restano ammesse nuove domande aritmetiche e richieste riferite esplicitamente al calcolo precedente. Non vengono introdotte risposte precostruite sull'arcobaleno o nuovi tentativi automatici del modello.

La cancellazione invalida il turno audio e sblocca anche produttore o consumatore in attesa. Il buffer conserva l'eventuale errore di generazione e non cresce senza limite nel numero di segmenti. Il motore naturale mantiene il rilascio previsto dopo 45 secondi di inattività.

## Verifica automatica

- **935 test di regressione superati**, zero errori e zero fallimenti, in 29,43 s: `regressione-finale.xml`.
- **12 verifiche mirate superate** dopo l'aggiunta dell'ultimo caso di cancellazione durante la generazione: `integration-final.xml`. Sono 11 prove del flusso completo e una prova concorrente del buffer Java. Questo gruppo si sovrappone alla regressione e i conteggi non vanno sommati.
- Il flusso integra callback STT, gestione del turno, core ALLMA, archivio temporaneo, streaming e invio al TTS. Android I/O e modello sono simulati in queste prove.
- Coperti 30 turni completi simulati, richiamo di un dato sintetico dalla memoria, passaggio della lingua inglese, cancellazione prima e durante la generazione, sospensione/ripresa e rifiuto del risultato aritmetico fuori argomento.
- La prova Java esegue il buffer reale con produttore e consumatore concorrenti: ordine di 100 segmenti, copia dei campioni, limite della coda, cancellazione durante l'attesa e conservazione degli errori.

## Collaudo sul telefono

| Percorso | Esito | Evidenza |
|---|---|---|
| Microfono → calcolo esatto → risposta `42` → voce | Riuscito | Controllo mirato del risultato sintetico, eventi tecnici e conferma dell'utente «entrambi perfetti» |
| Nuova domanda sull'arcobaleno → modello → risposta pertinente → voce | Riuscito | Controllo del tema della risposta, eventi di generazione e conferma dell'utente |
| Domanda successiva sul fenomeno appena spiegato | Riuscito | Conferma dell'utente nella prova guidata |
| Home durante la lettura → arresto della voce | Riuscito | Conferma dell'utente nella prova guidata |
| Rientro → riapertura Voce → domanda sul nome | Riuscito | Conferma dell'utente nella prova guidata |

L'utente ha confermato «Tutti e tre i controlli funzionano» per gli ultimi tre percorsi. Alla lettura conclusiva il telefono non risultava più collegato ad ADB: questi ultimi esiti sono conferme del collaudo umano, senza attribuire loro log che non sono stati acquisiti.

### Tempi osservati

Per il calcolo breve, il log della sintesi naturale registra avvio della riproduzione dopo **2.029 ms** dal suo avvio e completamento dopo **3.249 ms**, con 26.116 campioni a 24 kHz. Il completamento riporta `max_gap_ms=0` e un underrun Android. L'indicatore del vuoto audio è approssimativo; un underrun isolato non dimostra da solo una pausa percepibile. Questi tempi non comprendono l'ascolto e non sono una media di molte richieste.

Per l'arcobaleno, la generazione del modello dura **24.439 ms**. Dal riconoscimento all'avvio del TTS trascorrono circa **31,24 s**, inclusi i passaggi della pipeline. L'ultimo campione tecnico salvato precede la riproduzione di questa risposta: non permette di misurarne tutti gli intervalli audio. La qualità della lettura è stata confermata dall'utente.

Nei log salvati compare anche un errore STT **7** (nessuna corrispondenza) prima dei due turni riusciti. La prova successiva ha riconosciuto il messaggio; non va descritto come assenza assoluta di errori del servizio.

## Limiti della conclusione

Il flusso richiesto è verificato nei cinque percorsi reali sopra elencati. Non dimostra assenza di ogni bug né stabilità indefinita. I 30 turni sono simulati; accuratezza del microfono nelle altre lingue, chiamate/interruzioni di sistema, sessioni reali prolungate, consumo di batteria e rilascio effettivo della memoria naturale dopo inattività richiedono misure separate. Il servizio del telefono ha segnalato una lingua locale installata e 30 supportate: non equivalgono a 30 lingue già disponibili offline.

Il miglioramento risolve difetti della pipeline e della riproduzione; non costituisce una misura percentuale dell'intelligenza del modello. L'attesa delle risposte generative resta una priorità distinta dalla fluidità dell'audio.

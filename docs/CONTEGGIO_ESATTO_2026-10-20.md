# Conteggio esatto dei testi — build 102530

La 102529 rispettava il formato numerico, ma sul telefono aveva risposto `26`
alla domanda sulle lettere di `JSON`. La validazione del formato non poteva
verificarne il contenuto. Il nuovo strumento calcola il risultato in ALLMA,
indipendentemente dai pesi del modello.

## Operazioni disponibili

- Lettere: caratteri alfabetici Unicode dopo normalizzazione NFC. Numeri,
  spazi, punteggiatura ed emoji non sono lettere. Non è una segmentazione
  linguistica universale dell'alfabeto di ogni lingua.
- Caratteri: gruppi grafici, con gli spazi inclusi; non si confondono i punti
  di codice con emoji composte. Percorso locale per il latino semplice,
  segmentazione ICU integrata in Android per le sequenze complesse.
- Punti di codice Unicode: conteggio del testo originale, quando richiesto
  esplicitamente, distinto dal conteggio dei caratteri.
- Occorrenze: corrispondenze letterali, distinte per maiuscole/minuscole e
  senza sovrapposizioni per impostazione predefinita. La frase «includendo le
  sovrapposizioni» abilita l'altro criterio. Nessuna interpretazione come regex.
- Verifica di proposizioni esplicite, ad esempio «Il testo JSON contiene quattro
  lettere?», anche nel formato solo sì/no.

Esempi:

| Richiesta | Risultato |
| --- | --- |
| Rispondi solo con un numero: quante lettere contiene JSON? | `4` |
| Il testo JSON contiene quattro lettere? Rispondi solo si o no | `sì` |
| Quante lettere contiene «ippopotamo»? Rispondi solo con un numero. | `10` |
| Conta i caratteri di " A B ". Rispondi solo con un numero. | `5` |
| Quante volte compare "ana" in "banana", includendo le sovrapposizioni? Rispondi solo con un numero. | `2` |

Il formato JSON generico produce `{"conteggio":4}`; una proposizione aggiunge
`"esito":true` o `false`. Schemi JSON personalizzati e istruzioni aggiuntive non
vengono ignorati per forzare un conteggio.

## Integrazione

`exact_text.py` separa riconoscimento dell'intera richiesta ed esecuzione.
Accetta testi delimitati oppure singoli termini espliciti. Conserva il contenuto
tra delimitatori, inclusi spazi e righe. Non interpreta escape né esegue codice.
Il limite per testo è 8192 punti di codice; la richiesta completa è limitata.

Il percorso passa prima di AnswerRecall, Decider e generazione del modello.
Una risposta appresa o presente nella conversazione non sostituisce il calcolo.
L'animazione del cervello registra la reale esecuzione del modulo strumenti.
Il risultato attraversa salvataggio, cancellazione e consegna una sola volta,
come gli altri risultati verificati dell'architettura.

La provenienza riporta operazione, criterio, impronta del testo e risultato.
`knowledge_verified` vale solo per il risultato effettivamente calcolato su quel
testo. Non significa che il testo costituisca un fatto reale o un ricordo
personale di ALLMA. Non si aggiungono risposte al recupero appreso né si
modificano i pesi del modello.

Testi mancanti, riferimenti ambigui, citazioni di domande, istruzioni negate,
richieste multiple e formati incompatibili non vengono reinterpretati. Restano
sul percorso conversazionale ordinario, la cui correttezza dipende ancora dal
modello. Un elemento di ricerca vuoto produce una richiesta di chiarimento.
Se il servizio Unicode nativo non è disponibile, il conteggio complesso viene
dichiarato non verificabile: nessun ripiego silenzioso su `len()` o sul modello.

## Verifiche

- 80 test dedicati: 66 per riconoscimento, calcolo e Unicode; 14 sul vero core.
- Batteria mirata complessiva: **351 superati, nessun fallimento o test saltato**.
- **60/60** scenari operativi precedenti superati su Mac con dati sintetici.
- Sei richieste nel core completo, archivi temporanei e modello che solleverebbe
  un errore se chiamato: **6/6**, nessuna generazione. Tempi 7,27–18,11 ms su Mac,
  esclusi inizializzazione e interfaccia Android. Non sono tempi del telefono.
- Prima della modifica, tutti i sei controlli sull'instradamento esatto fallivano
  perché le richieste arrivavano al recupero di risposte. È una verifica del
  nuovo percorso, non una percentuale generale di intelligenza.

La segmentazione Android è coperta localmente con un iteratore simulato che
restituisce confini UTF-16. La prova reale di emoji complesse è confermata sotto; resta distinta da
questi test. I risultati non dimostrano l'assenza di errori su ogni domanda.

Evidenze: `/Users/erikahu/ALLMA/analisi/2026-10-20/conteggio-esatto/`.

Riferimenti per i criteri Unicode:
[Unicode UAX #29](https://www.unicode.org/reports/tr29/),
[Android ICU BreakIterator](https://developer.android.com/reference/android/icu/text/BreakIterator).

## Stato sul telefono

APK 102530 installata tramite aggiornamento. Verificati: corrispondenza delle
impronte del codice, inizializzazione del modello e della WebView, completamento
della transizione di avvio; nessun indicatore tecnico di errore rilevato.
L’utente ha confermato in chat i risultati `4` per le lettere di JSON e `1`
per il carattere emoji composto 👩‍💻: **2/2 prove corrette**. Nei log della
102530 risultano due risposte `verified_text_count` e zero
`text_count_unavailable`, senza indicatori di errore. Il codice installato
usa ICU per questa sequenza complessa: percorso coerente con la prova reale,
non una misura separata del servizio. Non sono stati misurati tempi Android
o consumi; il risultato non assegna una percentuale di affidabilità generale.
Evidenza aggiuntiva: `android-user-probe.json`.

# Richieste naturali e continuità degli strumenti — build 102531

La 102530 calcolava correttamente i conteggi espliciti, ma alcune formulazioni
comuni passavano ancora al modello. Inoltre il criterio delle sovrapposizioni
era implicito, anche quando portava a un risultato diverso.

## Comportamento aggiornato

Un piccolo lettore condiviso delle istruzioni riconosce formule come «Per
favore», «Puoi contare», «Potresti dirmi» e «Dimmi quante». Le istruzioni di
formato possono precedere o seguire la richiesta. Calcolo e conteggio usano
lo stesso componente; il contenuto citato resta separato dai comandi.

| Richiesta | Risultato diretto |
| --- | --- |
| Per favore, puoi dirmi quante lettere ha banana? Rispondi solo con un numero. | `6` |
| Conta le lettere di 'l'acqua'. Rispondi solo con un numero. | `6` |
| La parola a contiene una lettera? Rispondi solo sì o no. | `sì` |
| Rispondi solo con un numero: quanto fa 18 + 24? | `42` |
| Puoi calcolare 0,1 + 0,2? Rispondi solo con un numero. | `0.3` |
| Calcola 0,1 + 0,2. Rispondi solo in JSON. | `{"risultato":0.3}` |

I conteggi riconoscono anche «la lettera», «la sequenza» e «quante occorrenze».
Sono corretti gli apostrofi interni a parole italiane delimitate da apici e
la forma singolare delle unità nelle risposte. I testi citati conservano spazi,
maiuscole e altri caratteri originali.

## Ambiguità e seguito del dialogo

In `banana`, la sequenza `ana` compare una volta senza sovrapposizioni o due
volte includendole. Ora ALLMA chiede quale criterio usare quando i due risultati
differiscono e manca un'indicazione esplicita. Non presenta una scelta implicita
come unico conteggio verificato. Questo sostituisce il criterio predefinito
della 102530 per i casi effettivamente ambigui.

Alla risposta «Con le sovrapposizioni» o «Senza sovrapposizioni», ALLMA riprende
la richiesta appena chiarita e ricalcola il risultato. Conserva il formato
precedentemente richiesto, salvo una nuova istruzione esplicita compatibile.
Tutto questo avviene senza generazione del modello.

Il recupero usa soltanto gli ultimi due messaggi della chat corrente, già
filtrati per utente dal core. Devono essere una richiesta dell'utente seguita
da un chiarimento prodotto dallo strumento, con impronte del testo e della
sequenza corrispondenti. Una chat diversa, un altro utente, metadati incoerenti
o una conversazione intervenuta non autorizzano il recupero. Le dichiarazioni
citate e le risposte del modello non diventano automaticamente comandi.

La richiesta pendente viene ricostruita dai messaggi salvati, quindi continua
a funzionare anche dopo il riavvio del core. Non si introduce un secondo
archivio di testi o un nuovo stato globale condiviso tra utenti.

## Limiti mantenuti

Richieste multiple, negazioni del compito, spiegazioni aggiuntive, riferimenti
non risolti e schemi JSON personalizzati non vengono troncati per eseguire una
parte soltanto. In questi casi resta il percorso conversazionale normale.
Gli strumenti esatti continuano a precedere risposte apprese e inferenza.

L'aritmetica mantiene i limiti su lunghezza, complessità e dimensione dei
risultati. I decimali verificati sono esatti e finiti. Una divisione per zero
può essere spiegata anche nel formato JSON richiesto, con stato di errore e
senza dichiarare una conoscenza verificata.

## Risultati verificati su Mac

- Batteria mirata complessiva: **417 test superati**, nessun fallimento o test
  saltato.
- Nuovo gruppo di 53 controlli su riconoscimento, formato e ambiguità:
  **23/53** con i moduli archiviati della 102530, **53/53** dopo la modifica.
  Il confronto esegue gli stessi test finali contro entrambe le versioni.
- 13 controlli di integrazione aggiunti sul core reale: calcolo e conteggio
  prima delle risposte apprese, consegna unica, chiarimento fra turni,
  isolamento, integrità delle evidenze e recupero dopo riavvio.
- Batteria operativa precedente: **60/60** scenari superati, con dati sintetici
  e modello simulato.

Questi numeri misurano i casi elencati e il corretto instradamento degli
strumenti. Non sono una percentuale generale di intelligenza, una misura della
qualità del GGUF o un confronto di batteria/temperatura sul telefono.

Evidenze e confronto riproducibile:
`/Users/erikahu/ALLMA/analisi/2026-10-20/strumenti-richieste-naturali/`.

## Installazione Android

La build 102531 è installata. Il contenuto dell’APK corrisponde al pacchetto
compilato; sul telefono corrispondono le impronte di tutti i file controllati,
inclusi il lettore condiviso delle richieste, i due strumenti e il core.
Verificati caricamento del modello, WebView e completamento dell’avvio, senza
indicatori tecnici di errore rilevati.

Richiesta all’utente una prova in tre messaggi (42, chiarimento, 2). Il risultato
visibile della nuova sequenza sul telefono resta da confermare; i test di
integrazione descritti sopra sono stati eseguiti su Mac.

## Controllo dei log del 21 ottobre

Nel processo Android della 102531 risultano due messaggi elaborati, seguiti
rispettivamente da `verified_calculation` e `text_count_clarification`. Non
risultano generazioni del modello, errori tecnici o un successivo evento di
conteggio verificato. Il terzo passaggio non è osservato nel registro: non
viene classificato come fallimento della continuità né come prova superata.
I testi delle risposte sul telefono non sono stati estratti.

Durante il controllo dell’interfaccia ALLMA non era in primo piano; la lettura
dei soli stati booleani dei pulsanti è scaduta. Non è quindi verificato lo stato
attuale del compositore, e non sono state effettuate modifiche basate su
questa sola assenza di eventi. Evidenze in
`/Users/erikahu/ALLMA/analisi/2026-10-21/verifica-strumenti-android/`.

## Seguito confermato sul telefono — 21 ottobre

L’utente ha poi confermato che «Con le sovrapposizioni» restituisce `2`.
Nei log disponibili risulta la sequenza `text_count_clarification` seguita da
`verified_text_count`, senza eventi di generazione del modello. Il seguito
del chiarimento è quindi confermato anche nella prova Android. Il registro
attuale non contiene il precedente calcolo: i due controlli sono conservati
come osservazioni distinte. Non si deduce un riavvio reale dall’assenza di
eventi nel buffer; il recupero dopo riavvio resta verificato su Mac.

Evidenza: `followup-confirmed.json` nell’archivio di analisi del 21 ottobre.

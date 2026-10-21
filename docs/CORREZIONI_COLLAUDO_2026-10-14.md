# Correzioni dopo il collaudo Android

Problemi riprodotti e interventi:

1. Un messaggio rimaneva nella RAM dopo un errore di scrittura, e poteva
   essere salvato da un turno successivo. Ora il fallimento ripristina la
   cronologia sotto lo stesso lock, prima di propagare l'errore.
2. Un aggiornamento di contesto fallito lasciava metadati nuovi in RAM.
   Ora si prepara un nuovo dizionario e si ripristina l'oggetto originale
   se la scrittura fallisce.
3. Le citazioni facevano saltare il controllo del numero di frasi.
   Ora vengono contate anche le frasi citate. Un formato non misurabile
   (codice, elenchi, abbreviazioni ambigue) non supera un vincolo esatto.
   In assenza di quel vincolo, resta ammesso.
4. «Qual è il mio colore preferito?» veniva affidato al modello, che
   rispondeva sulle proprie preferenze. Ora le domande dirette supportate
   consultano esclusivamente dichiarazioni complete dell'utente corretto.
   Sono supportati colore, cibo, film, libro, animale e sport; non è un
   interprete universale delle preferenze. Prevalgono dichiarazioni più
   recenti e rinunce esplicite. Citazioni, altri utenti e risposte del
   modello non diventano prove personali.
5. Il benchmark Rapida non conservava il candidato scartato nel caso
   emotivo N4. Ora lo raccoglie nel solo nucleo temporaneo sintetico,
   con seed diagnostico e recupero delle risposte disabilitato, come
   già faceva il profilo Supporto. Nessun logging aggiunto alle chat reali.
   Questo è un intervento diagnostico, non una correzione dimostrata della
   qualità emotiva. Il controllo sull'attribuzione resta attivo.

La batteria invariata passa da 57/60 a 60/60 sul Mac. Otto nuovi casi
controllano rollback, tentativo successivo, rilettura da disco, citazioni,
isolamento e correzione/rinuncia delle preferenze. Il sottoinsieme mirato
passa 158/158. Il 100% riguarda solo i 60 scenari prestabiliti; non misura
affidabilità universale né correttezza del modello.

La suite completa finale termina con 976 test passati, 15 saltati e 12
avvisi (109,60 secondi). Il primo giro aveva un solo fallimento nel vecchio
test che esigeva l'accettazione automatica di formati non misurabili;
il test ora verifica che il vincolo esatto non venga saltato. La batteria
da 60 scenari non è stata modificata. Nei log Mac compaiono anche abort
di processi figli avviati per OCR in un processo con thread attivi: la
suite continua, ma questo esito non certifica il funzionamento OCR.

Restano da verificare sul GGUF reale il candidato N4, la formulazione e
le affermazioni del caso N5. Non è stato inserito un riferimento al pesce
nei generatori per far passare il benchmark. Non si attribuiscono miglioramenti
di temperatura, consumo o qualità semantica senza nuove misure.

## Esito sul Samsung

APK verificata e installata senza cancellare i dati: versione 0.9.0.0,
codice 102459, SHA256
`73a4baee6bb62e9de4bcc76df660ad65e5586060c2a5ba52a7345f5c974cbd82`.

La stessa batteria passa 60/60 anche sul runtime Python Android. Rapida
completa tutti i sei casi nella sessione `f7c14f4e8a8440da9958ba28d0623e5a`:
N1, N2, N3 superano i controlli automatici; N4 resta bloccato. Il suo
candidato dice «Sono felice per il nuovo lavoro, ma mi sento un po'
preoccupata per il primo giorno»: è appropriazione effettiva, non un
falso positivo. Introduce inoltre «panico», non espresso dall'utente.
Non si allenta il controllo e non si considera risolto questo difetto.

N5 ripete la precedente spiegazione imprecisa (anche «glii» al posto
di branchie). N6 risponde correttamente «Non trovo ancora nei ricordi
disponibili il tuo colore preferito» in 0,04 secondi, senza LLM.
N5 e N6 richiedono revisione del contenuto: non hanno verifiche automatiche
che permettano di aumentare il punteggio 3/4, rimasto invariato.

I tempi del giro sono 29,66 / 0,03 / 19,85 / 29,89 / 38,08 / 0,04 secondi.
Non si deduce una variazione di velocità generale: le condizioni termiche
sono differenti. La batteria era a 38,0 °C nel primo caso e 40,5 °C
nell'ultimo generato. Dopo il giro sono stati rimossi il collegamento
diagnostico ADB e l'impostazione temporanea di schermo sempre acceso.

Report conservati fuori dal repository:
`/Users/erikahu/ALLMA/analisi/2026-10-14/affidabilita/dopo-correzioni/`.

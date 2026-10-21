# Recupero emotivo basato su evidenze

Il caso N4 ha riprodotto un errore reale del modello: raccontava in prima
persona il lavoro e la preoccupazione dell'utente. Non si tratta di un falso
positivo del controllo, che rimane attivo.

Quando quella risposta viene completamente trattenuta, ALLMA può costruire
un breve riscontro utilizzando esclusivamente parole emotive attribuite
all'utente corrente. Il recupero copre da due a quattro emozioni chiare;
si astiene per indizi incerti, ipotetici, storici, citati o attribuiti solo
ad altre persone, oppure per vincoli di formato incompatibili. Riprende
«preoccupata», senza trasformarlo in «panico» o formulare diagnosi.

Il recupero rispetta uno o due periodi richiesti, non aggiunge inferenze
e non esegue una seconda chiamata al modello. Non viene usato se una parte
della risposta è già stata mostrata o se ripeterebbe il turno precedente.
Non è una comprensione semantica universale né una soluzione a ogni richiesta:
è una forma limitata di ascolto di riserva.

La provenienza `grounded_emotional_recovery` e gli intervalli delle parole
utilizzate sono conservati nei metadati. Il motivo della risposta modello
scartata rimane `generation.status=subject_mismatch`; il benchmark distingue
`pipeline_valid`, `recovery_used` e `model_answer_valid`. Un recupero valido
non prova che il modello sia diventato migliore. I controlli automatici
validano il formato e gli indizi, non l'utilità completa del dialogo.

Questo testo non entra nell'apprendimento delle risposte né nel recupero
delle risposte confermate. Non diventa conoscenza verificata o vissuto di ALLMA.

È stata provata un'istruzione generale per spiegazioni causali, senza
risposte di riferimento o termini specifici sul pesce. Nel giro Android
non ha aiutato: il modello ha usato «ghiandole gili» e ha aggiunto una
morte in «pochi secondi», senza riconoscere eccezioni. L'istruzione è
stata ritirata: la versione finale conserva il prompt precedente.

## Idee successive e limiti

* Dare a ogni affermazione un proprietario e una provenienza: parole
  dell'utente, esperienza personale documentata, conoscenza con fonte,
  oppure proposta del modello. I primi campi sono già presenti; un
  verificatore delle fonti per tutte le affermazioni resta da costruire.
* Consentire un ampliamento offline di conoscenza da documenti affidabili,
  separato dai ricordi autobiografici. Ogni passaggio usato dovrebbe
  mantenere fonte, ambito, data e limiti; la sola somiglianza vettoriale
  non deve trasformarlo in prova. È un progetto successivo, non implementato.
* Usare i casi di rifiuto sintetici come prove di compatibilità del motore
  quando si cambia GGUF. Conservare i difetti e i recuperi come misure
  separate, invece di proclamare una vittoria del modello.

Per la revisione indipendente di N5 sono state consultate fonti primarie:
[Australian Museum, What is a fish?](https://australian.museum/learn/animals/fishes/what-is-a-fish/)
e [dissezione e anatomia](https://australian.museum/learn/animals/fishes/fish-dissections/).
Descrivono il ruolo respiratorio delle branchie e le eccezioni dei pesci
capaci di respirare aria. Non sono state inserite nel prompt o nella memoria
del benchmark e non sono fonti che ALLMA abbia effettivamente consultato.

Verifiche sul Mac: 993 passati, 15 saltati; batteria invariata 60/60.
Sul Samsung: batteria invariata 60/60 sulla build sperimentale 102460,
dati conservati. Sessione Rapida `9916fd9f46e64a79b420adc14a69afd6`:
N1/N2/N3 superano i controlli; N4 viene consegnato tramite recupero;
N6 conserva la corretta assenza di evidenza senza LLM.

N4 consegnato: «Hai descritto emozioni diverse: “felice” e “preoccupata”.
Se ti va, possiamo approfondire cosa accompagna queste sensazioni, una
alla volta». I controlli automatici della pipeline passano 4/4, ma il
candidato originale del modello resta respinto. Il risultato non misura
un miglioramento dell'intelligenza del GGUF. Il recupero accoglie le
emozioni senza fornire una risposta approfondita alla situazione.

La build finale 102461 ritira solo il suggerimento causale e corregge
la valutazione delle risposte deterministiche: il campo
`model_answer_valid` è nullo quando non viene usato un modello.
Negli altri casi questo campo indica l'esito dei controlli di output,
non la verità fattuale. I report sperimentali originali restano immutati.
La correttezza delle spiegazioni fattuali resta un problema aperto.

La build finale è verificata, installata e avviata sul Samsung (102461):
SHA256 `0c9b6937745e9fab96efaa2750ba0c8be3653e7c5f5729a9835228ccb7357d19`.
Il payload corrisponde al codice corrente. Dopo il ritiro dell'esperimento,
105 test mirati passano. La prova GGUF descritta sopra è della build 102460:
non è stata ripetuta sulla finale, per evitare un ulteriore giro consecutivo
con batteria già a 41,4 °C. Il recupero emotivo ha lo stesso codice nelle
due build; è stato rimosso il solo suggerimento causale e affinata la
telemetria del benchmark. Schermo sempre acceso e forwarding ADB ripristinati.

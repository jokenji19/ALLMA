# Emozioni apprese, coalescenza e crescita progressiva

ALLMA nasce con un nome e con meccanismi di funzionamento. Un punto neutro
dei parametri di controllo (per esempio 0,5) non costituisce una preferenza
appresa o un ricordo. La nuova sezione di crescita nasce senza significati
personali, associazioni consolidate o disposizioni apprese.

## Percorso operativo

1. Un messaggio dell'utente viene prima salvato nella memoria conversazionale.
2. Gli indizi emotivi chiaramente attribuiti all'utente producono una goccia
   sospesa. Emozioni altrui, negazioni, citazioni e ipotesi non diventano
   esperienze emotive dell'utente. Una parte incerta non cancella eventuali
   indizi chiari in un'altra parte dello stesso messaggio.
3. Un altro contesto testuale distinto può consolidare l'associazione.
   Ripetere lo stesso contenuto non è una nuova prova. Due contesti sono
   una soglia tecnica iniziale, non una legge psicologica o la certezza
   che ALLMA abbia compreso completamente un'emozione.
4. Le associazioni trattenute producono un componente piccolo e reversibile
   dei tratti: sostegno/empatia oppure esplorazione/curiosità. Queste sono
   tendenze di risposta di ALLMA, non copie dell'umore dell'utente.
5. La tendenza arriva al prompt anche quando il livello facoltativo del
   modulo di personalità non viene eseguito. Il modello può comunque
   ignorarla o formulare male la risposta: i controlli di attribuzione restano.

Il nome è immutato. Le informazioni del modello non sono vissuti di ALLMA.
Le interpretazioni computazionali non dimostrano esperienza soggettiva.

## Significati personali

Sono supportate dichiarazioni esplicite come «Per me spenta significa
tristezza» o «Quando dico spenta intendo tristezza». La definizione rimane
attribuita a quell'utente. Se contiene il nome univoco di un'emozione,
un termine nuovo può essere riconosciuto in future dichiarazioni in prima
persona. Il sistema non sostituisce con essa il significato generale
di parole emotive già presenti nel vocabolario linguistico.

«Non mi sento spenta», «mia sorella è spenta» e «la lampada è spenta» non
diventano tristezza dell'utente. «Cosa significa spenta per me?» consulta
solo i significati documentati di quell'utente. Una nuova definizione
corregge la precedente; ritira gli indizi interpretati con la vecchia
associazione e ricalcola il componente appreso dei tratti.

È un primo apprendimento semantico delimitato, non la comprensione di ogni
metafora o definizione libera. Un significato ambiguo può essere conservato
senza tradursi in una nuova regola di riconoscimento.

## Persistenza e confini

CoalescenceProcessor rimane il proprietario dello stato. Significati,
associazioni, gocce e disposizioni sono contenuti nella sua sezione
`personality.emotion_growth` del cognitive_state.json; non nasce un secondo
database della personalità. Gli altri salvataggi della coalescenza e del
feedback conservano questa sezione. Il cambiamento viene preparato in copia
e reso visibile in RAM solo dopo la scrittura atomica riuscita.

Le risposte rapide e quelle recuperate osservano anch'esse gli eventuali
indizi del messaggio salvato. Un errore di generazione non cancella
l'esperienza dichiarata dall'utente. Il testo generato dal modello e le
ipotesi oniriche non alimentano questo percorso di crescita.

La finestra di lavoro conserva 32 contesti recenti per sfumatura, 256
identificatori recenti di eventi e 48 gocce recenti. Il numero cumulativo
di osservazioni continua a crescere oltre la finestra, senza conservare
tutti i testi nel profilo emotivo. Contatori distinti per provenienza lessicale
permettono di ritirare anche le interpretazioni meno recenti quando un
significato personale viene corretto. La migrazione conta soltanto le prove
ancora presenti: non ricostruisce prove già eliminate dalla vecchia versione.

La curiosità apprende da tutte le famiglie emotive riconosciute, comprese
le esperienze difficili; il sostegno resta prioritario quando necessario.
I tratti restano parametri limitati, mentre nuove prove possono continuare
ad aggiornare la storia. Non esiste più la soglia di 64 significati personali:
il detector compila soltanto gli alias presenti nel messaggio corrente.
Il dizionario persistente è comunque caricato in RAM e riscritto in copia:
per vocabolari molto grandi servirà un archivio indicizzato. Questa modifica
non costituisce memoria infinita, apprendimento universale o fine-tuning GGUF.

La deduplicazione di testi ed eventi copre le finestre recenti, non l'intera
storia: una ripetizione molto lontana può essere contata nuovamente.
Le relazioni sono separate per utente; il componente precedente della
personalità e il feedback esplicito sono mantenuti per compatibilità.

## Prove

Estensione della crescita continua: 210 test mirati passati; suite completa
1026 passati, 15 saltati, 11 avvisi (101,56 secondi). Prove dedicate con
80 esperienze, ripartenza a 81, correzione di interpretazioni già uscite
dalla finestra recente, conservazione delle esperienze dirette e 80 parole
personali. Il detector riconosce anche l'ottantesima parola. Questi sono
test software, non una misura di curiosità soggettiva o di apprendimento generale.
APK 102465 verificata: payload coerente, SHA256
`05a9170e0339237bd9ef2a40e459938013fd3b42061279ee3865871745615704`.

Verificati nascita senza storia appresa, sospensione, consolidamento,
attribuzione, negazione, correzione, distinzione tra tristezza percepita
e disposizione al sostegno, isolamento tra utenti, riavvio, salvataggio
fallito, conservazione durante i salvataggi del feedback, uso nel detector
e nelle istruzioni al modello. Suite completa sul Mac: 1021 passati,
15 saltati. Batteria invariata: 60/60.

«Crescita emotiva · 5 turni» nella diagnostica usa uno stato temporaneo.
Le verifiche di crescita e persistenza sono separate dalla validità delle
risposte generate. Il test non alimenta la storia personale dell'ALLMA reale.

Prima prova Android, build 102463, sessione
`35d5c8fd6e4a47d38c87df1d8c1375ad`: tutti e quattro i controlli strutturali
passano (fasi, termine appreso, risposta propria distinta e ripristino).
L'utente sintetico insegna «spenta» → tristezza; una prima esperienza
rimane sospesa, una seconda distinta consolida una tendenza al sostegno.
Il componente appreso dell'empatia è 0,0015503563, stima di controllo,
non percentuale di empatia reale. ALLMA conserva il significato e può
descrivere la crescita avvenuta senza dichiararsi triste come l'utente.

La seconda risposta del modello ripete la prima e viene bloccata: il primo
giro non passa complessivamente la qualità della pipeline. Il report
originale è conservato. Si estende quindi il recupero controllato a un
singolo indizio chiaro quando è sostenuto da un significato personale
appreso o da un'associazione già consolidata. Il recupero cita il contesto
attuale dell'utente, offre ascolto e non viene usato per addestrare o
confermare una risposta. Anche i fallimenti per ripetizione possono usare
questo percorso, solo se nessun testo era stato emesso e i vincoli sono
soddisfatti. Il report distingue i passi recuperati dalle risposte valide
del modello. Dopo questa modifica, 114 test mirati passano sul Mac.

## Esito finale sul telefono

Build 102464 verificata e installata senza cancellare dati. SHA256
`47b4bff5edb22471a399dc3b67e43dede5451ca90d401a9534a89ec88336abd8`.
Sessione di prova `883c136fe9f349d38589162e6281f311`: tutti i cinque turni
sono validi per la pipeline, i quattro controlli strutturali passano,
e il ripristino rilegge le medesime associazioni dal disco. Al terzo turno
la risposta ripetuta del modello viene sostituita dal recupero controllato:
«Mi dici come ti senti: “Mi sento spenta dopo una discussione”. Se ti va,
possiamo approfondire cosa accompagna queste sensazioni, una alla volta».
Il report conserva `model_answer_valid=false` per quel passo.

Il modello rimane imperfetto: la prima risposta è generica e propone
positività/rilassamento senza approfondire; la seconda è ripetuta. La prova
dimostra il percorso di apprendimento e la sua integrazione, non una
comprensione umana completa o un miglioramento del GGUF.

Tempi dei turni: 0,133 / 33,596 / 22,156 / 0,020 / 0,017 secondi.
Il recupero avviene dopo la generazione fallita, quindi non evita il suo
costo in questo giro. Insegnamento, recupero del significato e descrizione
del proprio stato non richiedono generazione. Non è stata misurata una
riduzione di temperatura o consumo. La batteria durante le due generazioni
passa da 38,4 a 39,6 °C, con telefono collegato USB.

Suite finale: 1022 passati, 15 saltati, 12 avvisi (101,78 secondi).
Batteria invariata finale: 60/60 sul Mac e 60/60 nel runtime Android.
Impostazione di schermo sempre acceso e forwarding ADB ripristinati.

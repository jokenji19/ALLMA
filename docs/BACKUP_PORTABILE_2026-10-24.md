# Preferenze portabili e ripristino — 24 ottobre 2026

## Comportamento

La build 102550, versione pubblica 0.9.1, include `model_binding.json` e
`notifications.json` fra i dati persistenti migrabili, nelle copie private e
negli archivi cifrati esportabili. Le regole Android di backup e trasferimento
elencano gli stessi file. Non sono inclusi i pesi GGUF, il codice o la cache
vettoriale derivata.

Ogni copia verifica lo schema delle due preferenze oltre all'integrità dei byte:
versione supportata, tipi, nome locale GGUF senza percorsi, ragionamento booleano
o automatico, consenso booleano e date finite del cooldown. Un file futuro o
invalido non sostituisce una copia verificata. Le preferenze hanno un limite di
64 KiB, separato dai limiti degli archivi di memoria.

Il ripristino conserva esattamente i file verificati. Le impostazioni di una
vecchia installazione o della cartella dei sorgenti non vengono unite allo stato
ripristinato. Le copie precedenti prive delle due preferenze restano importabili;
in quel caso non viene ricostruito un consenso alle notifiche inesistente.

## Modello sul nuovo dispositivo

La selezione salvata identifica un nome locale, non un percorso del vecchio
telefono. Quando il file corrispondente è disponibile viene usato quel modello,
con la sua scelta del ragionamento. La preparazione del backup non richiede la
presenza del GGUF sul dispositivo che verifica o importa l'archivio.

Se il file manca, è esterno alla cartella dei modelli oppure la preferenza locale
non è interpretabile, ALLMA conserva i dati personali e la preferenza. Apre
l'interfaccia di configurazione per scegliere o scaricare il modello. Non
seleziona un altro motore di nascosto e non avvia download da quella condizione.
Un errore nativo effettivo nel caricamento resta un errore di avvio; non viene
presentato come un semplice modello da selezionare.

Questo recupero riguarda la selezione salvata dopo l'avvio del core. La procedura
iniziale già esistente per preparare i componenti richiesti dall'app resta
distinta: il backup non contiene quei componenti e non sostituisce il loro setup.

La scelta esplicita di un nuovo modello continua a passare dalla verifica del
download e dal collegamento ai consumatori del core. Solo il successo salva la
nuova preferenza e chiude la condizione di configurazione richiesta.

## Notifiche

Si trasferiscono la preferenza dell'app e i cooldown, non un permesso Android.
Ogni stato e ogni invio controllano il permesso e il canale del dispositivo
corrente. Caricare la preferenza non chiede automaticamente un permesso e non
pubblica una notifica di prova. Una preferenza malformata non abilita parzialmente
il consenso prima di fallire.

È corretto anche il caso di orologio riportato indietro rispetto all'ultima
notifica: permette un nuovo invio autorizzato e applica subito il nuovo cooldown,
senza sospendere le notifiche per tutta la differenza tra i due orologi.

## Verifica

I test usano installazioni e archivi temporanei separati. Il trasferimento cifrato
parte da un'installazione sintetica, viene verificato, preparato e applicato a
un'altra, prima di aprire i consumatori delle preferenze. Si controllano byte,
proprietà della storia, modello mancante/presente, consenso distinto dal permesso,
migrazione, copie precedenti, schemi invalidi anche con digest corrispondenti,
recupero dell'interfaccia e rifiuto delle scritture non confermate.

La diagnostica «Conservazione e backup» comprende ora 28 scenari: i 20 precedenti
su cifratura, recupero e conservazione più 8 sulle preferenze portabili. Il test
desktop esegue l'intero runner condiviso, non solo i casi isolati.

Evidenze: `/Users/erikahu/ALLMA/analisi/2026-10-24/portable-backup/`.
I risultati finali del desktop e del telefono vengono registrati separatamente
dal confronto delle impronte e dalla verifica del pacchetto Android.

| Controllo finale | Esito |
|---|---:|
| Suite completa offline sul Mac | 2.297 superati, 15 saltati, zero fallimenti su 2.312 raccolti |
| Prove mirate iniziali | 114/114 |
| Prove mirate dopo la correzione del confezionamento | 32/32 |
| Android, conservazione e backup | 28/28 |
| Android, controlli generali | 60/60 |
| Sorgenti applicativi installati confrontati | 13/13 corrispondenti |

Le prove mirate si sovrappongono alla suite completa: non si sommano per ottenere
una copertura percentuale. Sul telefono le batterie sono complete e i marcatori
tecnici non riportano traceback, errore di benchmark o crash. Sono state
verificate anche le regole compilate di backup cifrato e trasferimento Android.
Il collaudo del telefono è terminato il 24 ottobre 2026 sulla 102550.

La prima suite completa ha rilevato la mancanza dei due nuovi nomi nelle esclusioni
di `buildozer.spec`: i dati possono essere copiati nel backup, ma non devono entrare
nei sorgenti distribuiti. L'esclusione è stata corretta prima di installare l'APK.
Il primo report fallito è conservato in `full/`; la ripetizione con configurazione
finale usa `full-final/`. Le regole XML vengono controllate anche nel pacchetto
Android compilato, oltre alle verifiche dei file sorgenti.

## Perimetro

Non è stato ripristinato l'archivio personale del telefono e non sono state
esportate conversazioni. I controlli del motore usano un sostituto sintetico;
non certificano la compatibilità o la qualità di qualsiasi futuro GGUF.
Le copie private sul telefono non sostituiscono una copia cifrata conservata
separatamente. Non viene dichiarata una durata garantita di anni o millenni.
Le modifiche sono salvate localmente; commit e pubblicazione GitHub restano
operazioni separate.

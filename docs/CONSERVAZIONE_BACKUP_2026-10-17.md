# Conservazione, protezione e backup — 17 ottobre 2026

## Obiettivo e limiti reali

La storia di ALLMA deve poter essere conservata e trasferita indipendentemente dal modello linguistico. Nessun telefono, formato, algoritmo crittografico o software può essere certificato oggi per funzionare senza manutenzione per migliaia di anni. Queste modifiche proteggono dati e recupero nei casi verificati, senza attribuire una percentuale di affidabilità eterna.

Le date ISO vengono conservate senza scadenza automatica dell'archivio conversazionale. Le prove includono gli anni 2038, 2256, 3000 e 9000; i test di regressione arrivano anche al 9999. Sono simulazioni su archivi sintetici, non anni di servizio reale. Python datetime supporta gli anni 1–9999. L'ordine dei nuovi eventi di apprendimento usa ora un contatore logico, ricostruito da storia, giornale e checkpoint, senza dipendere dall'orologio. I precedenti contatori rimangono compatibili. L'esaurimento del formato genera una richiesta esplicita di migrazione, mai un ritorno a zero.

## Copie private

- Nuovo servizio `BackupRuntime` nei dati Android gestiti: controllo ogni minuto, copia dopo almeno 30 minuti quando i dati sono cambiati e ALLMA è libera. Rimanda con conversazione, cambio modello, benchmark, sogni, batteria sotto il 20%, temperatura batteria sopra 40 °C o sensori non validi. Nessuna nuova inferenza del modello.
- La chat interrompe la copia in corso; i file temporanei vengono abbandonati senza pubblicare copie incomplete. Non è una garanzia di tempo reale: la durata di un singolo controllo/formato JSON resta proporzionale alle dimensioni del file.
- Include gli archivi autorevoli presenti: conversazioni, SQLite principale, apprendimento incrementale, richiamo confermato, preferenze di consegna, impostazioni, stato cognitivo/personale, diario e revisione dei sogni, moduli e diario della coalescenza. Esclude GGUF, codice, cache vettoriale ricostruibile, report diagnostici, consenso notifiche e collegamento al modello specifico del dispositivo.
- Snapshot SQLite con API backup, comprendente le transazioni WAL confermate. Gli altri file vengono copiati con controllo delle modifiche avvenute durante la cattura.
- Manifest versionato, dimensioni e SHA-256 di ciascun file; verifica ZIP, percorsi, tipi, limiti di espansione, JSON/formati principali e integrità SQLite prima di pubblicare la copia.
- Conserva sette generazioni recenti, fino a quattro settimane e dodici mesi distinti. Le sole copie gestite/verificate possono essere ruotate. Una copia fallita non rimuove copie precedenti. Spazio insufficiente: errore, senza cancellare la storia.
- Ricostruzione esplicita del catalogo danneggiato: verifica gli archivi esistenti e conserva anche quelli non validi per il recupero. Non sostituisce silenziosamente la storia con una copia più vecchia.
- Scrittura JSON atomica: sincronizza anche la directory dopo la sostituzione dove il filesystem lo permette. Un fallimento di sincronizzazione successivo alla sostituzione segnala minore durabilità senza fingere che la scrittura non sia avvenuta.

Le copie private restano nel contenitore dell'app: **non proteggono dalla disinstallazione o perdita del telefono**. Non sono una seconda collocazione indipendente. Una copia può inoltre contenere errori logici già presenti nei dati; un hash verifica i byte, non la verità dei ricordi.

## Esportazione cifrata e importazione

Impostazioni → Dati e backup consente di creare/verificare una copia privata e di salvare/aprire una copia cifrata con il selettore documenti Android. L'utente sceglie la posizione: locale, supporto esterno o un provider cloud. ALLMA non effettua caricamenti automatici in cloud.

Password di 12–1024 caratteri: non viene salvata in impostazioni, log o localStorage. Rimane in memoria soltanto per completare l'operazione; non esiste recupero della password. La sua robustezza resta importante. Il file esportato protegge il contenuto, mentre nome, dimensione e parametri pubblici del formato sono visibili.

Formato `ALLMA-BACKUP-1`: PBKDF2-HMAC-SHA256 con 600.000 iterazioni e sale casuale di 16 byte; AES-256-GCM per record da 256 KiB, nonce composto da prefisso casuale di otto byte e indice a quattro byte. Intestazione, ordine e marcatore finale sono autenticati. Record mancanti, alterazioni, dati aggiunti e password errate impediscono la pubblicazione del file decifrato. Android usa JCA attraverso una piccola classe Java con tipi espliciti per evitare ambiguità nelle firme PyJNIus, Mac il pacchetto cryptography; nessuna nuova libreria nativa pesante nell'APK. Un vettore fisso verifica compatibilità tra implementazioni. Il primo caricamento della classe Java avviene brevemente sul thread UI con il classloader dell’app; derivazione della chiave e cifratura rimangono sui worker.

Il formato è versionato per future migrazioni: questo **non** promette che algoritmi o password attuali resteranno sicuri per secoli. Conservare una copia esterna aggiornata, la password separatamente e verificare periodicamente un ripristino su dati separati.

## Ripristino

1. Selezione del file cifrato e password, decifratura privata e verifica completa.
2. Anteprima con data e numero degli archivi; conferma esplicita nell'interfaccia.
3. Nuova copia verificata dello stato corrente, preparazione di una cartella separata e marcatore durevole.
4. Chiusura completa e riapertura dell'app: applicazione **prima** di aprire i database del core. Nessun rimpiazzo di database in uso.
5. Due rinomine recuperabili anche dopo interruzione: lo stato precedente resta in `allma_state.before-restore.<id>`. Non viene eliminato automaticamente.

Il ripristino sostituisce l'intero stato, senza unire due personalità/storie. I vecchi dati presenti nel pacchetto dell'app non vengono nuovamente importati dopo un ripristino. Se il JSON o SQLite corrente è già danneggiato, il ripristino della copia sana può procedere senza dichiarare verificati i dati corrotti: l'intera cartella originale viene comunque conservata dalla procedura di rinomina. Gli errori di spazio e gli annullamenti non vengono ignorati. Una corruzione che impedisce perfino l'avvio dell'interfaccia richiede ancora recupero assistito o una reinstallazione con successiva importazione della copia esterna.

## Protezione del pacchetto distribuito

Il pacchetto Android esclude esplicitamente archivi personali locali, copie precedenti del codice, cartelle di test, report, modelli scaricati e cache desktop. La verifica dell'APK rifiuta la presenza degli archivi autorevoli del Mac o di cartelle di sviluppo. I file originali sul Mac non vengono rimossi. Un hook locale normalizza i frammenti del manifest passati da Buildozer a p4a, evitando quote letterali negli attributi e senza modificare strumenti installati.

## Backup Android

Regole esplicite per Android precedente e successivo ad API 31: solo file autorevoli, esclusi modelli, codice, cache, copie private e file temporanei. Backup cloud consentito soltanto con le capacità di cifratura previste dalle API. Il backup di sistema dipende da impostazioni, provider e quota; Android Auto Backup ha quota di 25 MB per app. L'esportazione cifrata scelta dall'utente resta necessaria per una copia indipendente e archivi più grandi.

Fonti: [Auto Backup](https://developer.android.com/identity/data/autobackup), [Storage Access Framework](https://developer.android.com/training/data-storage/shared/documents-files), [Cipher Android](https://developer.android.com/reference/javax/crypto/Cipher).

## Capacità e prossime migrazioni

Limiti intenzionali di questa versione: file 512 MiB, totale autorevole 2 GiB, JSON verificabile 128 MiB per file, involucro cifrato fino a 4 GiB. Non sono dati cancellati automaticamente: al superamento viene richiesta una migrazione. Il core carica ancora la storia conversazionale JSON in RAM; prima di una crescita molto grande serviranno archivio paginato e migrazione verificata. La finestra del modello e le cache rimangono limitate, senza essere equivalenti all'intero archivio storico. Alcuni registri operativi/onirici mantengono per progetto solo una finestra recente: il backup conserva lo stato persistito disponibile, non ricostruisce tracce già eliminate in passato.

La continuità per molti anni richiede manutenzione dei formati, copie indipendenti, prove di recupero, spazio disponibile e aggiornamento della sicurezza. Questi interventi costituiscono una base concreta; non equivalgono a capacità illimitata o affidabilità assoluta.

## Verifica

La prima prova Android 102511 ha passato 11/20 casi e ha identificato due incompatibilità reali: selezione errata della firma sovraccaricata di Cipher.init tramite PyJNIus e copia dei metadati di sicurezza Android durante la conservazione dell'indice danneggiato. Corrette nella 102512 con un confine Java tipizzato e copia dei soli byte in file privati 0600. Non sono stati nascosti o rietichettati i fallimenti. Altre correzioni di collaudo: isolamento del controllo ripristino alle cartelle gestite, cancellazione di un selettore documenti se l'interfaccia è stata chiusa, esclusione di dati locali dalla distribuzione.

Suite completa della 102512: 1.680 casi raccolti, 1.665 superati, 15 saltati, nessun fallimento. Integrazione finale di recupero da dati correnti corrotti: 7/7 casi del controller, compreso un caso aggiuntivo, dopo la suite. La seconda prova Android 102512 ha passato 12/20: corretta la conservazione dell'indice, ma il worker JNI usava il classloader di sistema e non trovava la classe Java pur presente nel DEX. Il caricamento iniziale della classe viene quindi effettuato sul thread UI dell'app. Build finale 102514: aggiunge il ramo di recupero dei dati corrotti nell'interfaccia e il caricamento corretto della classe Java. Le regressioni mirate finali passano 71/71; la classe Java passa anche cifratura, decifratura e rifiuto di alterazioni confrontati indipendentemente con il riferimento desktop. Terza prova Android sulla build 102514: **20/20**, completa in **49.82 secondi**, inclusa interoperabilità della cifratura nativa. L'unione dei casi sorgente della suite e delle regressioni finali contiene 1.681 casi distinti: **1.666 superati, 15 saltati, nessun fallimento**. Il 100% del piano Android riguarda questi venti scenari sintetici; non è una percentuale di affidabilità universale o di durata eterna. Evidenze in `analisi/2026-10-17/conservazione-backup` fuori dal repository dell'app. Nessun ripristino dei dati personali durante la batteria sintetica.


La cattura di una schermata del dispositivo sul Mac è stata bloccata dalla revisione automatica perché potrebbe includere chat personali. Nessun tentativo di aggirare il blocco: verifica tramite log e report sintetici. Il controllo visivo sul dispositivo e il trasferimento reale attraverso un provider documenti esterno restano distinti dai test automatici/simulati. L'APK di collaudo è ancora debug: un rilascio destinato a distribuzione richiede firma e configurazione di produzione; l'accesso ADB autorizzato può accedere ai dati dell'app debug.


APK finale 102514 verificata, installata con aggiornamento che mantiene i dati. SHA-256: `cbb7c187c5b0821afbd769f6d0a082f125a1dc2cd48afb84a747e7e34cbed99c`. Manifest compilato con fullBackupContent e dataExtractionRules; supporto Java AES presente nel DEX. Nessuna esportazione o sostituzione dei dati personali sul telefono durante il collaudo. La batteria a 45,6 °C ha fatto rinviare le copie automatiche: soglia di ammissione 40 °C. Per la prima copia esterna l'utente deve scegliere password e destinazione nel selettore Android.

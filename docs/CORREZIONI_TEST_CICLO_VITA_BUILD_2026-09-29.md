# Terzo blocco: test, ciclo di vita, persistenza e build

Modifiche salvate localmente, senza commit o push. Non sono stati completati i moduli mancanti né riorganizzata l'intera architettura.

## Test e difetti funzionali

- Risolti i quattro errori di raccolta: i test importavano API rimosse. Migrati alle API attuali di core, profilo, risposta contestuale e meta-apprendimento. Gli originali sono conservati in `analisi/2026-09-29/correzioni-03/test-originali` nella cartella superiore al repository. Questo aggiornamento non implementa le vecchie API né dimostra equivalenza delle funzionalità rimosse.
- Isolati i database e i file di memoria dei test del core; chiusura esplicita dei suoi worker al termine di ciascun test.
- I test degli adattamenti ora forniscono un generatore simulato: non richiedono un modello reale non configurato.
- Il profilo conta i turni utente; la cronologia viene filtrata per utente prima del limite. Eliminato il fallback mobile che poteva mostrare messaggi di altri utenti.
- Applicato lo stile emotivo anche alla risposta senza conoscenza disponibile; protetto l'accesso all'ultimo messaggio quando la cronologia è vuota.
- Verificato che una generazione fallita conservi la cronologia senza aggiungere conoscenza; la conoscenza iniziale di sistema rimane legittimamente presente.

## Ciclo di vita

- Rimosso il controllo sincrono del checksum del modello durante `build`: la verifica viene eseguita dal worker di SetupView prima di aprire la chat.

- Il bootstrap conserva l'istanza interna, imposta il suo root, ne avvia `on_start` e inoltra pausa, ripresa e arresto. L'app esterna viene acquisita prima di costruire la nuova istanza Kivy.
- La pausa richiede l'annullamento del turno, sospende l'avvio dei sogni e salva memoria/apprendimento. Pause ripetute non sovrascrivono la preferenza da ripristinare.
- All'arresto viene cancellato il timer dello stato di apprendimento e viene richiesta la chiusura del core su un thread separato, evitando attese native sul thread grafico.
- Disattivato l'avvio automatico del servizio Android indipendente: istanziava un secondo core senza un protocollo di coordinamento con l'app. La dichiarazione del servizio resta disponibile nella configurazione, ma il bootstrap non lo avvia. La sua riattivazione richiede gestione esplicita della proprietà del modello e dei dati.
- L'annullamento resta cooperativo; questi controlli headless non dimostrano i tempi di arresto dell'inferenza nativa né garantiscono completamento del thread di chiusura se Android termina il processo.

## Persistenza

- Nome, età e scelta dei sogni sono salvati atomicamente in `allma_settings.json`, accanto al database, e ripristinati all'avvio. Una sospensione temporanea dei sogni non modifica la preferenza salvata.
- Corretto il dizionario incompleto del progresso utente che causava errori nella lettura delle statistiche. Persistiti argomenti, conteggi degli eventi di apprendimento per confidenza, cronologia e aree di miglioramento.
- Persistite anche la storia del feedback (compresi enum/date) e le aree di miglioramento della conoscenza, prima perse al riavvio.
- Restano da verificare sul dispositivo terminazione forzata, riavvio, gestione dei file corrotti e migrazioni con dati reali. La persistenza dell'intero profilo emotivo/sociale e la cancellazione coordinata di tutti gli archivi non sono completate in questo blocco.

## Build

- Il controllo delle modifiche include servizio, manifest, librerie personalizzate e script inclusi nel payload.
- L'hash viene calcolato dopo la rigenerazione del payload, evitando di salvare lo stato della versione precedente di `main.py`.
- Dichiarata NDK 27d coerente con il percorso locale; in Docker i percorsi locali di SDK/NDK vengono azzerati per usare quelli della piattaforma Linux.
- La CI rigenera il payload e usa lo script di build; rimosso il vecchio passaggio che cancellava `Model`.
- Rimosso il download a runtime delle librerie native da URL GitHub mutabili: il bootstrap cerca la libreria inclusa dalla ricetta nell'APK. Se manca, segnala il difetto della build; non sostituisce silenziosamente il binario con un download.
- La riproducibilità completa non è ancora garantita: ramo p4a e immagine Docker restano non fissati a un commit/digest e le dipendenze native richiedono una compilazione verificata.

## Risultati

Suite eseguita offline su una copia temporanea del progetto: **321 passati, 0 falliti, 0 errori di raccolta, 15 saltati** (ultima esecuzione: 30 settembre, incluse le regressioni chat). I 15 skip preesistenti riguardano un file di prova mancante, cinque test di API core non disponibili, otto di NLP non disponibile e uno di API reasoning non disponibile. Non sono test superati. Rimangono avvisi Transformers sull'API deprecata `return_all_scores`.

Nove nuove regressioni coprono inoltro del ciclo di vita, pausa ripetuta, riavvio del progresso, riavvio del feedback, invalidazione della build e scelta della libreria nativa, passaggio tra app esterna/interna e ordine di confezionamento/hash e avvio senza checksum sul thread grafico. Un ulteriore test di integrazione verifica identità e preferenza dei sogni dopo riavvio.

Log e XML: `/Users/erikahu/ALLMA/analisi/2026-09-29/correzioni-03/`.

ADB ha rilevato il dispositivo con API 36. La build è stata successivamente installata e avviata; l’utente ha confermato download e chat funzionanti, segnalando poi il difetto di separazione pensiero/risposta documentato in CORREZIONI_CHAT_2026-09-30.md.

Payload rigenerato; il verificatore APK controlla la corrispondenza del payload incorporato con quello corrente in main.py. Sintassi dei file modificati e `git diff --check` verificati.

## Compilazione proseguita il 30 settembre

Eseguiti confezionamento e pulizia iniziale; i tentativi successivi riutilizzano le dipendenze native già compilate. Il primo tentativo ha compilato Python/SDL ma si è fermato su NumPy: il virtualenv PEP 517 del Python host rilocato non trovava `math`. La ricetta locale NumPy usa il Python host preparato da p4a, con backend installato esplicitamente, senza un secondo virtualenv; NumPy ha poi completato la compilazione.

La stessa correzione è applicata a Pillow, Kivy, pyjnius e android, conservando patch e file delle ricette upstream. Un ulteriore difetto di `pip --target --upgrade` lasciava metadati di versioni precedenti accanto al codice aggiornato: il supporto locale usa il resoconto JSON di pip per archiviare i soli metadati superati fuori da site-packages. Non elimina i pacchetti né assume che la versione numericamente maggiore sia quella corretta. **Due test dedicati passati**, per aggiornamento e downgrade; sono inclusi nel totale aggiornato della suite.

Esclusi dal confezionamento APK `tmp_llama_check` e `allma_model/tests`. Queste cartelle rimangono nel progetto.

Kivy 2.3.1 richiede versioni specifiche dei tool: la ricetta locale usa Cython <=3.0.11, packaging ~=24.0, setuptools ~=69.2.0 e wheel ~=0.44.0. La compilazione ha superato NumPy, Pillow, pyjnius, android e llama.cpp; l'installazione dei tool Kivy si è poi fermata con OSError 28 (disco pieno). Dopo autorizzazione è stata rimossa esclusivamente la vecchia cache `.buildozer/android/platform/build-arm64-v8a` (4,9 GB, marzo 2026). La cache attiva `.buildozer_local` è conservata; verificati 5,1 GiB liberi e ripresa la compilazione. Log diagnostici conservati compressi senza il dump dell'ambiente.

## Esito della compilazione e protezione dei dati

La compilazione Android è stata completata con Kivy 2.3.1 e KivyMD 1.2.0; verificati moduli Python e librerie native ARM64 nell’APK. La versione inizialmente installata ha completato il download del modello e una generazione reale sul telefono.

I dati applicativi sono ora in files/allma_state, fuori da files/app che p4a sostituisce agli aggiornamenti. La migrazione copia solo archivi mancanti e usa il backup SQLite per includere il WAL. Modello in files/models; KIVY_HOME in files/.kivy. Tre regressioni verificano migrazione, mancata sovrascrittura e percorso del diario. Il collaudo completo del ciclo di vita rimane da completare.

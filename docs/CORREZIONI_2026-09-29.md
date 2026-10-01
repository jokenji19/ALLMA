# Correzioni avviate — 29 settembre 2026

Questo è il primo blocco di interventi dell'audit. Non rappresenta la chiusura di tutti i problemi. Le modifiche locali già presenti sono state conservate. Nessun APK è stato compilato o installato.

## Implementato e verificato con test Python

- Memoria vettoriale: ricostruzione coerente di vocabolario e vettori al riavvio; ricerca funzionante anche con un solo documento; aggiornamenti da altre istanze rilevati; chiavi di origine per evitare duplicazioni nella migrazione dei messaggi.
- Conversazioni: indicizzazione dei messaggi normali e migrazione di quelli salvati; esclusione delle risposte marcate non valide; percorso di archiviazione collegato alla directory del database del core.
- Persistenza JSON: file temporaneo univoco, flush/fsync e sostituzione atomica senza cancellazione preventiva. Metadati datetime, enum, dataclass e NumPy serializzabili. Salvataggio dei dati utente già presenti in memoria.
- Apprendimento: salvataggio automatico della knowledge base e delle varianti; ripristino delle unità recuperabili, con compatibilità per i vecchi snapshot aggregati.
- Risposte: ricerca prima dell'indicizzazione del messaggio corrente; eliminato il bypass basato sulla sola similarità lessicale; una risposta non valida mantiene il suo stato e non alimenta l'apprendimento. Nessun feedback positivo o incremento di successo inventato dal core.
- Risposta finale: conservati thought_trace e parametri vocali; la cronologia salva lo stesso contenuto restituito al chiamante.
- Importazioni: caricamento differito di ALLMACore, evitando l'importazione circolare che poteva disattivare il motore vettoriale in base all'ordine degli import.
- Eventi: coda thread-safe, bus distinto per ogni core e collegamento del relativo DreamManager. API close() per arrestare scheduler/loop/executor, usata nei test del bridge.
- Sogni: toggle senza logger mancante; trigger manuale subordinato a impostazione, identità utente e assenza di attività; eliminato il secondo trigger basato sulla sottostringa "notte".

## Implementato, da verificare anche sul dispositivo

- Il modello caricato in ritardo viene collegato anche al DreamManager e al Tree of Thoughts. Senza modello/utente, il gestore non avvia il sogno.
- Lo scheduler dei sogni conserva il riferimento al thread e attende durante la fascia mattutina, senza terminare definitivamente.
- Core emotivo e orchestratore condividono la stessa istanza SoulCore.
- Il bridge trasmette la risposta finale alla WebView; il testo definitivo sostituisce i token provvisori. La sintesi vocale attende il testo finale: questo aumenta la latenza della voce, ma evita di leggere un testo successivamente corretto.
- Il rendering Markdown usa una lista di tag ammessi, rimuove attributi eseguibili e accetta soltanto collegamenti assoluti HTTP/HTTPS. Necessaria verifica del DOM nella WebView reale.
- La garbage collection conserva i messaggi se l'estrazione dei fatti fallisce o non produce fatti validi. Da completare la verifica dell'intero ciclo e della cancellazione coordinata dell'indice.
- Rigenerato il payload ZIP_DATA in main.py e confrontato ogni file incorporato con il sorgente.

## Verifica

Suite eseguita su copia temporanea, offline, senza usare i database personali:

- 10 nuovi test di regressione passati, inclusi nella suite generale.
- Verifica mirata (regressioni, bridge Android, scenari complessi): 22 passati.
- Suite generale: 248 passati, 5 falliti, 15 saltati, 4 errori di raccolta.
- I 5 fallimenti e i 4 errori di raccolta corrispondono alle categorie già presenti nell'audit: adattamenti delle risposte, aspettativa obsoleta sul conteggio del profilo, conversazione emotiva beta e import di moduli legacy mancanti.
- Compilazione sintattica dei file Python modificati, controllo sintattico JavaScript e git diff --check passati.

Log e XML: /Users/erikahu/ALLMA/analisi/2026-09-29/correzioni-01/.

## Lavoro ancora aperto al termine del primo blocco

Aggiornamento: nuova chat, invii simultanei, annullamento e download sono stati affrontati nel [secondo blocco](CORREZIONI_CHAT_DOWNLOAD_2026-09-29.md).

1. Migrare i test legacy e correggere i fallimenti funzionali ancora presenti, senza nasconderli con skip indiscriminati.
2. Completare il ciclo di vita dell'app esterna/interna e collegare close() all'arresto reale; coordinare servizio Android, sogni e accesso al modello. Il bus in memoria non comunica tra processi.
3. Collegare "Nuova chat" alla creazione di una conversazione nel backend e gestire invii simultanei/annullamento dello streaming.
4. Completare persistenza e isolamento dei profili, feedback, progresso dell'apprendimento, diario e impostazioni. JSON atomico non risolve scritture concorrenti da processi separati.
5. Cancellazione coordinata tra messaggi, conversazioni e indice; gestione dei limiti dimensionali e misurazione del costo della ricostruzione vettoriale su grandi archivi.
6. Download dei modelli: ripresa HTTP corretta, integrità verificata, nessuna eliminazione automatica di file estranei.
7. Build riproducibile: ordine pack/hash, versioni native/ABI, dipendenze, servizio e manifest; compilazione e prova Android.
8. Sicurezza e completezza dei servizi accessori, visione simulata, budget dei moduli e riduzione del codice duplicato/legacy secondo l'audit.

Non sono disponibili pesi del modello nel progetto: inferenza reale, prestazioni, GPU/OpenCL e comportamento Android restano non verificati.

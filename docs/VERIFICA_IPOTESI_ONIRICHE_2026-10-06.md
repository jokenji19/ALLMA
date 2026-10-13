# Verifica delle ipotesi oniriche — 6 ottobre 2026

Il Diario Sogni dispone ora di una revisione persistente: Conferma, Correggi e Scarta. La visione resta rinviata.

## Uso e significato

Aprire il Diario Sogni dal menu. Le ipotesi da valutare mostrano il testo e tre azioni. Correggi apre un campo di modifica: salvare esplicitamente la correzione. Origine e revisione mostra il messaggio di partenza, la nota e le ultime cinque revisioni. L’archivio SQLite conserva la cronologia completa. Durante una risposta in corso la revisione viene rifiutata con un messaggio; riprovare dopo la fine della risposta.

La conferma rappresenta un giudizio dell’utente. Non certifica una verità indipendente, non crea un ricordo autobiografico e non modifica i pesi del GGUF. Le ipotesi non valutate e scartate non entrano nel contesto delle risposte. Quelle confermate o corrette possono contribuire come dati attribuiti all’utente, con provenienza esplicita, al massimo due per richiesta. Il recupero è lessicale e limitato, senza una nuova chiamata al modello.

## Persistenza e revoca

Il nuovo archivio dream_journal.json.reviews.db importa le ipotesi precedenti senza duplicazioni. Ogni revisione conserva originale, fonte, testo corretto, nota e numero di revisione. Salvataggio dello stato, evento di audit e versione utente avvengono nella stessa transazione. Richieste ripetute sono idempotenti; revisioni concorrenti obsolete vengono rifiutate. Gli accessi sono separati per utente e il ponte Android usa l’identità della sessione, senza fidarsi di quella inviata dal frontend.

Una revoca cambia la versione del contesto: le risposte già confermate nel recupero rapido con la vecchia versione non vengono riutilizzate. Anche le precedenti risposte nella cronologia che dipendevano da ipotesi superate vengono escluse dal contesto futuro. Restano archiviate, senza cancellazioni. Un test ha riprodotto un difetto in cui questi metadati non venivano persistiti: il salvataggio è stato corretto e il test ora passa.

Il sistema sospende nuove generazioni oniriche quando ci sono 50 ipotesi non valutate per utente. Se l’archivio revisioni non è disponibile, i sogni si fermano e la chat resta utilizzabile; l’archivio danneggiato non viene cancellato automaticamente. Gli errori di salvataggio nell’interfaccia conservano la bozza e non mostrano conferme premature.

## Verifiche eseguite

- Suite finale: **606 test superati, 15 saltati, 11 avvisi**, 52,97 secondi. Gli avvisi sono deprecazioni delle dipendenze. I test saltati non sono prove superate.
- 19 regressioni aggiunte rispetto alla suite precedente: persistenza e riavvio, isolamento utente, revoche, conflitti concorrenti, rollback, importazione ripetibile, archivio corrotto e limiti della coda.
- **33 controlli web superati**, con ponte simulato: payload delle azioni, attesa del salvataggio, gestione degli errori, conservazione della correzione e rendering sicuro dei testi.
- Verifica grafica nel browser a 390 × 844: nessuna fuoriuscita orizzontale; pannello scorrevole e tema scuro leggibile. Screenshot con dati sintetici conservato negli artefatti.
- Controllo sintattico JavaScript e diff whitespace superati.
- Audit statico: 167 moduli nel perimetro del payload, 95 raggiungibili dai percorsi principali; nessun errore sintattico e nessuna importazione locale mancante sui percorsi principali. Rimane un riferimento a vocabulary_data fuori dal grafo principale: l’audit statico non dimostra che tutti i moduli siano operativi.
- pack_brain.py completato; APK debug compilata e verifica del payload superata.

APK: bin/allma_prime-0.56-arm64-v8a-debug.apk. SHA-256: 20de5df28fe4e3421f56f35166d8cf11443ded67bcaae264607077e9c8f2f1c0. Architettura arm64-v8a, KivyMD 1.2.0.

## Limiti e stato finale

Non sono stati eseguiti installazione o collaudo fisico Android in questa sessione. Le prove web simulano le risposte del ponte; le prove Python verificano archivio e integrazione con il core. Non sono state misurate nuove prestazioni termiche o qualità cognitiva sul telefono. La nuova APK è pronta per questo controllo.

Le modifiche sono salvate localmente, senza nuovo commit o push. Tutte le modifiche precedenti sono conservate. Artefatti: /Users/erikahu/ALLMA/analisi/2026-10-06/verifica-ipotesi-oniriche.

## Aggiornamento successivo: installazione sul telefono

Su richiesta dell’utente, APK installata con adb install -r sul Samsung SM_S938B (Success), conservando i dati dell’app. L’impronta SHA-256 del base.apk installato coincide esattamente con quella verificata sopra. Activity avviata e processo presente (PID 13836). Questo conferma installazione e avvio, non il collaudo completo delle nuove revisioni oniriche sul dispositivo.

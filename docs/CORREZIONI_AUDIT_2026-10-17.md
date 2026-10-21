# Correzioni dell’audit ALLMA — 17 ottobre 2026

I 17 difetti riproducibili D01–D17 dell’audit hanno ricevuto correzioni e prove mirate. Questo non certifica l’assenza di qualsiasi altro errore, la qualità generale del modello o una percentuale di affidabilità nell’uso reale.

L’audit iniziale resta conservato in [RAPPORTO.md](/Users/erikahu/ALLMA/analisi/2026-10-17/audit-attuale/RAPPORTO.md). Le nuove evidenze sono separate in [correzioni-audit](/Users/erikahu/ALLMA/analisi/2026-10-17/correzioni-audit).

## Difetti corretti

| ID | Cambiamento e risultato | Verifica principale |
|---|---|---|
| D01 | Conferme e osservazioni di AnswerRecall tornano allo stato precedente quando il salvataggio fallisce. Le letture non espongono oggetti interni modificabili. Una conferma non salvata non sblocca una risposta. | `test_audit_transactions.py`: conferma fallita, sostituzione fallita, recupero e riapertura. |
| D02 | I mutatori dell’apprendimento sono transazionali: preparano copie dei soli record interessati e annullano le modifiche in caso di errore. Il salvataggio propaga l’insuccesso. | Cinque prove con scrittura guasta: inserimento, interazione, feedback, successo, varianti. |
| D03 | Il caricamento valida l’intero archivio in strutture candidate. Un record errato conserva lo stato precedente, produce un backup e impedisce la sovrascrittura finché il file non viene recuperato e ricaricato. Anche una versione booleana è rifiutata. | Caricamento parziale e versione malformata, file originale conservato, ripristino verificato. |
| D04 | Ogni apprendimento invalida l’indice correlato; la ricerca lo ricostruisce quando serve, sotto il blocco del learner. Evitata la ricostruzione a ogni singolo inserimento. | Stesso ricordo trovato subito e dopo il riavvio, isolamento del proprietario. |
| D05 | L’archivio cognitivo distingue assenza e corruzione. Un errore resta esplicito e blocca le scritture normali; gli originali sono preservati. | JSON troncato, radice errata e sezione errata; successiva riparazione senza perdere le altre sezioni. |
| D06 | Un validatore necessario non disponibile non equivale a una validazione superata. La chat restituisce stato `validation_unavailable`, senza apprendere il candidato. | Guasto del validatore nella pipeline e in un turno completo con modello simulato. |
| D07 | Preparare un candidato non modifica più identità o regole plastiche. L’aggiornamento avviene dopo i controlli finali e il salvataggio della risposta ammessa e completa. Rimossa la crescita automatica della maturità a ogni chiamata; attività e crescita non sono la stessa misura. | Risposta respinta, salvataggio della risposta fallito, salvataggio dello stato fallito, archivio cognitivo ricaricato. |
| D08 | Negazioni coordinate, emozioni in credenze/desideri subordinati e “mi manca” sono trattati con maggior cautela. La mancanza di aria, tempo o denaro non diventa lutto; l’assenza di una persona non prova un decesso. | Casi negativi e ambigui in `test_audit_context.py`, oltre alle regressioni emotive esistenti. |
| D09 | Il livello tecnico parte da “sconosciuto” e usa dichiarazioni esplicite dell’utente, revocabili. Il contesto usa progetti reali del proprietario, compresi i metadati, quando il riferimento è univoco. Eliminati “expert” e progetto ALLMA fissi. | Dichiarazioni di utenti diversi, revoca, progetto assente, progetto reale e metadati. |
| D10 | Le risposte incomplete sono escluse dalla cronologia fattuale ordinaria. Se usate come contesto conversazionale vengono marcate esplicitamente come incomplete. | Ammissibilità e marcatura della risposta troncata. |
| D11 | Diario dei sogni con annullamento delle modifiche se il salvataggio fallisce. Un diario corrotto non viene sostituito. Gli archivi di ipotesi pendenti e ricordi elaborati sono preservati; il lavoro che potrebbe sovrascriverli è sospeso. Anche un errore contemporaneo della schermata non impedisce il recupero. | Diario troncato, scrittura guasta, schermata chiusa, archivi ausiliari corrotti, recupero e riapertura. |
| D12 | Rimossi testi di messaggi, contesti ricchi, trascrizioni e aggiornamenti del profilo da diversi log dei percorsi attivi. Restano eventi, identificatori ed esiti. | Turno con segreto sintetico: assenza del testo in log e uscite catturate. Non è una certificazione di tutti i log di librerie esterne. |
| D13 | Il vecchio metodo della personalità individua i valori usando il vocabolario condiviso del processore; non itera più un valore `None`. | Aggiornamento dei valori di curiosità con esperienza sintetica. |
| D14 | Il sistema storico di memoria usa vettori lessicali deterministici al posto di numeri casuali. I vettori forniti esplicitamente sono conservati. | Stesso testo → stesso vettore; testo diverso → vettore diverso. Non è un embedding semantico. |
| D15 | Backend HTTP opzionale con factory, credenziali configurate e password cifrate tramite hash, token Bearer a scadenza, limitazione dei tentativi di login, controlli del proprietario e contratti effettivamente disponibili nel core. Nessun server avviato durante gli import. | Client Flask locale: login, rifiuto delle credenziali dimostrative, conversazione, statistiche, proprietà e assenza di CORS aperto. |
| D16 | Il bridge alternativo usa learner, personalità, emozioni e progetti del core. Non crea una seconda rappresentazione cognitiva indipendente. Le proprie impostazioni applicative sono separate. | Identità degli oggetti condivisi, apprendimento visibile attraverso il bridge, isolamento di cronologia e progetti. |
| D17 | L’estrattore documenti delega al processore esistente una sola volta. La manutenzione storica ripara riferimenti a ricordi mancanti senza cancellare esperienze. Rimossa la dichiarazione di supporto per i vecchi formati `.doc` e `.xls` non realmente leggibili dal processore. | Estrazione di testo sintetico con singola lettura e riparazione di collegamenti pendenti. Non certifica ogni formato né la visione. |

Le prove aggiunte sono in [test_audit_transactions.py](/Users/erikahu/ALLMA/ALLMA_V4/tests/regression/test_audit_transactions.py), [test_audit_validation.py](/Users/erikahu/ALLMA/ALLMA_V4/tests/regression/test_audit_validation.py), [test_audit_context.py](/Users/erikahu/ALLMA/ALLMA_V4/tests/regression/test_audit_context.py) e [test_audit_compatibility.py](/Users/erikahu/ALLMA/ALLMA_V4/tests/regression/test_audit_compatibility.py): **47 casi**, compresi quelli parametrizzati.

## Verifiche e provenienza dei conteggi

- Audit iniziale: **1.444 superati, 4 falliti, 15 saltati** su 1.463 casi.
- Dopo le correzioni: raccolta completa di 1.506 casi, eseguita in processi piccoli per contenere le risorse. Esito iniziale conservato: 1.490 superati, un riferimento obsoleto in un test fallito, 15 saltati.
- Corretto anche il riferimento del mock a `core.*`: ricontrollato lo stesso gruppo, **11 superati e uno saltato**. Il primo tentativo manuale di questo ricontrollo non aveva l’ambiente Kivy previsto: errore d’invocazione conservato, non contato come prova riuscita.
- Controllo finale delle aree modificate: **100 casi superati**. Controllo aggiuntivo degli archivi onirici: **16 superati**, comprendenti due casi nuovi. I conteggi non vengono sommati contando due volte lo stesso test.
- Riepilogo per caso univoco: **1.495 superati, 15 saltati, nessun fallimento residuo, 1.510 casi complessivi**. [Dati e metodo di consolidamento](/Users/erikahu/ALLMA/analisi/2026-10-17/correzioni-audit/test-results/final-summary.json), [esito di ogni caso e provenienza](/Users/erikahu/ALLMA/analisi/2026-10-17/correzioni-audit/test-results/final-cases.json). Non è un nuovo giro completo successivo alle ultime quattro prove: è la raccolta completa con ricontrolli mirati delle modifiche successive.
- Batteria operativa su Mac: **60/60**, dati sintetici e modello simulato, anche dopo le ultime protezioni. [Riepilogo](/Users/erikahu/ALLMA/analisi/2026-10-17/correzioni-audit/batteria-mac-finale/summary.json).
- JavaScript: sintassi dei due script principali e tre harness superati, inclusi 11 controlli di interruzione e 11 di completamento. Non equivale a verificare ogni gesto del WebView.
- Analisi sintattica di **366 file Python** nelle directory dei sorgenti, dei test e degli strumenti. Questo perimetro è diverso dai 226 file del solo inventario applicativo iniziale.

I 15 test saltati rimangono esplicitamente non verificati: uno richiede un’immagine assente, cinque si riferiscono a vecchie API di integrazione, otto a un’interfaccia NLP non disponibile e uno a vecchie API di ragionamento. Non sono stati eliminati né trasformati in successi. Le nuove regressioni verificano diversi contratti attuali, ma non sostituiscono automaticamente ogni vecchia specifica.

## APK e collaudo Android

**Build finale 102508**, versione visualizzata **0.9.0.0**, installata senza disinstallare l’app. Il pacchetto è [allma_prime-0.9.0.0-arm64-v8a-debug.apk](/Users/erikahu/ALLMA/ALLMA_V4/bin/allma_prime-0.9.0.0-arm64-v8a-debug.apk). La verifica del pacchetto conferma la corrispondenza del payload incorporato e il runtime nativo ARM64 compatibile con Qwen 3.5: [controllo APK e SHA-256](/Users/erikahu/ALLMA/analisi/2026-10-17/correzioni-audit/apk-check-102508.json).

Sul Samsung SM-S938B sono verificati l’avvio della build finale, la disponibilità dell’interfaccia e **60/60 scenari operativi completati**. L’utente ha avviato l’ultimo giro dall’interfaccia alle 15:58; i log ne confermano il completamento. [Riepilogo Android 102508](/Users/erikahu/ALLMA/analisi/2026-10-17/correzioni-audit/android-summary-102508.json). Un primo giro sulla 102507 aveva già superato gli stessi 60 casi; i tentativi di tocco remoto che non avevano avviato la seconda prova non vengono contati.

Questa batteria usa Python realmente eseguito sul telefono, archivi sintetici temporanei e un generatore di risposte simulato. Comprende integrazione, recupero dagli errori, isolamento, concorrenza/ciclo di vita, controlli sull’output e persistenza. **Non misura la qualità del GGUF, ogni nuova regressione dell’audit, la voce, ogni gesto dell’interfaccia o l’autonomia.** Le prove nuove sui guasti specifici sono state eseguite sul Mac.

Non è stato eseguito un nuovo benchmark linguistico lungo. La batteria era a 40,2 °C in carica durante il primo controllo e a 37,7 °C prima del giro finale: condizioni diverse e ricarica attiva impediscono di ricavarne un miglioramento termico percentuale. Le conversazioni personali non sono state copiate per il collaudo; sono stati conservati i riepiloghi sintetici e i log di esecuzione di ALLMA.

## Riduzione dei costi e controlli di consegna

Il core mobile non carica più anche il classificatore Transformers inglese del sistema di contesto. Rimangono il percorso emotivo mobile e le capacità del modello selezionato. È rimosso anche un recupero di conoscenze senza proprietario che non veniva utilizzato nel turno. Questi cambiamenti eliminano lavoro superfluo; non sono disponibili misure controllate per attribuire una percentuale di risparmio energetico.

Il programma [run_tests.py](/Users/erikahu/ALLMA/ALLMA_V4/tools/run_tests.py) raccoglie tutta la suite prima di suddividerla, disabilita la rete esterna nei processi dei test e salva log e XML. Le directory di lavoro dei test sono temporanee. Il workflow Android deve superare i test prima di compilare; l’immagine di build è fissata tramite digest e le dipendenze di test hanno versioni definite. Il workflow modificato **non è stato ancora eseguito su GitHub** in questo intervento.

Riferimenti per la configurazione CI: [immagine ufficiale Buildozer](https://github.com/kivy/buildozer), [installazioni ufficiali PyTorch 2.5.1 CPU](https://pytorch.org/get-started/previous-versions/).

## Compatibilità del backend HTTP

Il backend alternativo resta opzionale e non viene esposto dalla chat Android. Per abilitarlo occorre configurare `ALLMA_API_SECRET` con almeno 32 caratteri casuali e `ALLMA_API_USERS` come oggetto JSON utente → hash della password creato con `werkzeug.security.generate_password_hash`. Niente credenziali dimostrative o segreto predefinito.

`create_app(core=..., config=...)` permette di condividere un core esistente. La risposta del login contiene un `access_token` da trattare come opaco e inviare nell’intestazione `Authorization: Bearer …`; non è più un JWT da decodificare lato client. La durata predefinita è un’ora. Il comando locale del modulo usa solo `127.0.0.1`, senza debug. I test impiegano il client Flask, senza aprire un server.

## Archivi danneggiati e limiti rimanenti

Un file danneggiato non viene interpretato come autorizzazione a ricreare una memoria vuota. Si conserva un backup `.invalid.bak`, con ulteriori copie distinte quando necessario; se non è possibile copiarlo resta comunque bloccata la sovrascrittura normale. Il recupero richiede un archivio valido e il suo ricaricamento; non si inventano i record mancanti. Un’interfaccia guidata per questo recupero è ancora da realizzare.

Le transazioni aggiunte riguardano singoli componenti. Non costituiscono una transazione unica fra tutte le basi dati: un guasto durante gli aggiornamenti opzionali può lasciare una risposta già salvata e un apprendimento non salvato, dichiarato nei metadati restituiti. Questi esiti successivi al salvataggio non vengono tutti riscritti retroattivamente nella cronologia.

Restano attività separate: recupero semantico sulle parafrasi, costo degli archivi grandi, riduzione della concentrazione del core, consolidamento della storia lunga, rimozione ragionata dei percorsi storici, qualità fattuale su casi nuovi, compatibilità di altre famiglie di modelli e misure lunghe Android di voce, temperatura, batteria e cambi di modello. L’analizzatore emotivo resta euristico e deve poter dichiarare incertezza; non comprende ogni possibile emozione umana.

Le correzioni sono salvate localmente. In questo intervento non è stato effettuato un nuovo commit, push o rilascio GitHub.


## Rafforzamento successivo nello stesso giorno

Il successivo intervento [Memoria, apprendimento e recupero](/Users/erikahu/ALLMA/ALLMA_V4/docs/RAFFORZAMENTO_MEMORIA_RECUPERO_2026-10-17.md) aggiunge ricerca per un vocabolario delimitato di parafrasi funzionali e recupero ordinato degli aggiornamenti dopo interruzioni. Riduce quindi due dei limiti elencati sopra, senza trasformare gli archivi in una singola transazione e senza risolvere la comprensione semantica generale. La nuova build è 102509; il rapporto separato contiene prove e misure aggiornate.

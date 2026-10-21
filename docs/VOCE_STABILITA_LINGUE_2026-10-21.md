# Voce: stabilità, lingue e sintesi naturale — 21 ottobre 2026

## Cosa cambia

- Il riconoscitore Android viene riutilizzato dopo i turni conclusi correttamente. La cancellazione di un turno ancora attivo ritira invece la connessione, per non riutilizzare uno stato incerto.
- Disconnessione (11) e servizio occupato (8): un solo tentativo automatico dopo 700 ms. Nessun ciclo infinito, nessun tentativo automatico dopo permesso negato, lingua assente, silenzio o troppe richieste.
- Le sessioni e i singoli tentativi hanno identificatori separati. Risultati, livelli audio e callback di connessioni precedenti non possono riaprire il microfono né consegnare testo dopo una cancellazione.
- Attesa massima: 10 s per l'avvio, 12 s per la trascrizione dopo fine ascolto; singolo ascolto limitato a 60 s. Uscita, pausa e chiusura cancellano timer e riconnessioni.
- I log conservano codici di errore, stato, lingua e tipo di servizio; non aggiungono trascrizioni o registrazioni audio.
- La diagnostica non mostra più «pronto» quando è presente un errore vocale.

## Lingue

Nella schermata Voce, «Lingua e voce» offre 16 lingue manuali e l'opzione automatica. Le preferenze sono salvate nel database dei moduli già incluso nei backup, senza diventare ricordi autobiografici.

Su Android 13+ viene richiesta al servizio la lista delle lingue locali installate, supportate e in preparazione. La verifica è limitata a 2,5 s; i servizi che non implementano l'inventario possono comunque rispondere con il loro normale esito. I dati mancanti non vengono confusi con una trascrizione riuscita.

Su Android 14+ la modalità automatica richiede rilevamento e cambio di lingua, limitando la scelta ai pacchetti locali quando il servizio ne fornisce la lista. Il supporto effettivo dipende dal servizio Android e dai dati installati. Su versioni precedenti viene segnalato l'uso dell'italiano e resta disponibile la selezione manuale.

La lingua riconosciuta viene comunicata alla conversazione e alla sintesi. I codici validi non presenti nella vecchia lista di cinque lingue non ricadono più automaticamente sull'italiano. Le voci Android che richiedono rete non vengono selezionate per la lettura offline.

Il servizio locale è la scelta predefinita. L'uso del servizio Android generico, che può usare la rete, richiede una scelta esplicita nelle opzioni vocali.

## Voci naturali opzionali

- Kokoro INT8 con Sara (`if_sara`, speaker 35) e Nicola (`im_nicola`, speaker 36), per l'italiano.
- Motore Android Sherpa ONNX 1.12.20, CPU, due thread; non viene usato il caricatore GGUF.
- Download ufficiale da 132.303.094 byte; modello estratto 114.203.756 byte, tabella voci 28.200.960 byte, oltre ai dati di pronuncia.
- SHA-256 dell'archivio e dei file principali verificati, estrazione con rifiuto di percorsi esterni e collegamenti, installazione per sostituzione atomica. Il modello è opzionale ed escluso dal backup della storia personale.
- La generazione è eseguita fuori dal thread dell'interfaccia. L'audio arriva per segmenti nativi e può essere interrotto; il modello viene liberato dopo 45 s di inattività.
- Le altre lingue usano la voce Android. La voce Android resta la preferenza predefinita finché non viene selezionata una voce naturale.
- Le licenze e le origini sono in `assets/web/licenses/natural-voices.txt`. La build sperimentale include un componente GPL di fonemizzazione; prima di una distribuzione pubblica occorre soddisfare le relative condizioni di distribuzione. La licenza MIT del codice ALLMA non cambia le licenze delle dipendenze.

## Verifica

Evidenze locali: `/Users/erikahu/ALLMA/analisi/2026-10-21/voce-stabile-multilingua/`.

915 test di regressione passano. I test comprendono 30 turni simulati di riconoscimento con una sola connessione sana, riconnessione limitata, timer, risultati tardivi, uscita, cambio lingua, permessi, inventario lingue, persistenza, integrità e riparazione dei pacchetti.

Il collaudo Android ha identificato e corretto due problemi non visibili nei mock: caricamento delle classi applicative dal thread JNI sbagliato e firma del callback audio Kotlin/Java. La firma compilata corretta è `invoke(float[]) -> Integer` (evidenza `java-callback-signature.txt`). Le build sperimentali iniziali non sono considerate un collaudo riuscito.

I 30 turni simulati non rappresentano 30 scambi parlati reali. Il collaudo prolungato del microfono, la qualità percepita delle voci e l'accuratezza nelle diverse lingue richiedono prove reali sul dispositivo. I tempi di una frase e la temperatura istantanea non misurano da soli il consumo di batteria o l'affidabilità di lungo periodo.

### Esito sul telefono della build 102536

Sara e Nicola hanno completato la riproduzione e l'utente ha confermato «si funzionano». Nei campioni riusciti osservati l'inizio dell'audio naturale è arrivato dopo 1.103–3.300 ms; questo misura la sintesi, non l'intera risposta del modello. I due completamenti registrati contano 111.189 e 115.603 campioni audio a 24 kHz.

L'inventario del telefono ha comunicato una lingua installata e 30 supportate: il numero delle lingue offerte dal servizio non equivale al numero già pronto offline.

Alla verifica conclusiva Android segnala chiusura richiesta dall'utente (`USER REQUESTED / REMOVE TASK`, stato 0). Non è stato possibile misurare il rilascio della memoria a riposo con il processo ancora attivo. Il rilascio dopo 45 secondi è implementato; la sua efficacia sulla memoria e il confronto controllato di batteria restano da misurare.

## Ricontrollo e build 102537

Il controllo successivo ha riprodotto quattro difetti con test inizialmente falliti: consegna audio tardiva dopo annullamento, doppia chiusura del motore, verifica di integrità rimasta in cache dopo sostituzione dei file e download riavviabile dopo chiusura. Sono stati corretti tramite sincronizzazione della consegna/cancellazione, chiusura idempotente e controllo dei metadati dei file prima di riutilizzare la verifica.

Aggiunti anche controlli per uno stop Android tardivo e per la cancellazione del download prima dell'avvio del worker, senza aprire la rete. Il callback Java di rilascio viene sincronizzato con la chiusura per evitare l'invio di lavori a un executor già chiuso.

Risultato: **921 test superati, zero fallimenti**. APK 102537 compilata, contenuto verificato e installazione confermata sul telefono; nessun avvio in primo piano richiesto durante l'aggiornamento. Le prove audio reali confermate dall'utente si riferiscono alla build 102536. La 102537 richiede ancora la ripetizione vocale reale e il collaudo prolungato già indicato sopra.

# Correzioni e risposte troncate — primo intervento

Problema osservato: un conteggio sbagliato veniva difeso anche dopo
«Sbagliato, 5 è la risposta». La seconda risposta terminava al limite di token,
senza spiegare il taglio nell'interfaccia.

Cambiamenti:
- Riconoscimento di Sbagliato/Sbagliata, Non è così e risposte corrette proposte,
  distinguendo frasi ipotetiche, citazioni e commenti non correttivi.
- Contestazione fattuale separata dalle correzioni sulle ripetizioni.
  Rivalutazione della domanda originale; proposta dell'utente non verificata,
  nessuna adesione obbligata. Un risultato corretto può restare uguale.
- Le risposte contestate escono dal recupero appreso; il turno passa al modello
  per riesame invece di riproporre una risposta confermata in precedenza.
  La correzione non diventa conoscenza verificata né aggiorna i pesi GGUF.
- Indicazione generale per distinguere quantità presenti e cambiamenti di stato,
  sottraendo dalla categoria richiesta soltanto gli elementi rimossi.
  Nessuna risposta dell'enigma dei pesci è stata inserita nel codice.
- Budget breve: conclusione e spiegazione essenziale, senza aumentare i limiti
  termici. Istruzioni di riesame compatte per limitare l'overhead del prompt.
- Stato truncated_answer trasmesso dal core alla WebView: avviso esplicito e
  pulsante Continua per una nuova richiesta manuale. Nessun retry automatico.
  Non sovrascrive una bozza, non continua un vecchio turno dopo un altro invio.

Verifiche:
- 44 test Python su riconoscimento, continuità, asset, dispatch e voce.
- 5 test focalizzati del core: correzione falsa conservata come non verificata,
  contesto originale presente nel prompt, invalidazione recupero, generazione
  singola e gestione budget. Usano motori simulati, non misurano l'intelligenza.
- 11 asserzioni JS pure sul comando Continua (nessuna navigazione browser).
- Sintassi JS/Python e contenuto APK verificati.

Il controllo della pagina browser locale è stato bloccato dalla policy URL
dello strumento; nessun tentativo di aggirarlo. Il comando UI è stato testato
in isolamento e il collaudo visivo/funzionale reale richiede la prova Android.
La correttezza semantica del modello resta da misurare con casi nuovi sul
telefono: i test di flusso non garantiscono che il modello risolva un enigma.

APK 102478, versione 0.9.0.0. SHA256:
1ad22cf03ca53afa32cd1e7fa0243d86ac5339c86364f2b12e70c9b66256d0eb.
Installazione con mantenimento dati e runtime qwen35.

Installazione 102478 confermata sul telefono. Inizializzazione nativa riuscita,
WebView caricata e TTS pronto. Nessuna nuova generazione automatica avviata
per il collaudo su un telefono ancora caldo. Richiesta prova manuale con una
correzione volutamente falsa su un conteggio di palline: esito non ancora ricevuto.

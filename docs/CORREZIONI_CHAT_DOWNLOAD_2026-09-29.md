# Secondo blocco — chat, annullamento e download

Modifiche salvate nel progetto ALLMA_V4. Nessun commit, push, build APK o installazione è stato eseguito. Le modifiche locali precedenti restano presenti.

## Chat

- `ChatSession` assegna ogni richiesta a una conversazione e consente un solo turno attivo. La prenotazione avviene prima dell'avvio del thread: un comando "Nuova chat" immediatamente successivo non può spostare il vecchio messaggio nella nuova conversazione.
- "Nuova chat" crea realmente una conversazione nel core. Se è in corso una risposta, ne richiede l'annullamento e attende la conclusione del worker prima di cambiare conversazione. La schermata viene pulita solo alla conferma del backend; la cronologia precedente resta salvata.
- Aggiunto il pulsante "Interrompi". L'annullamento arriva al core e al wrapper del modello; lo stream nativo viene chiuso e il lock di inferenza rilasciato.
- Gli invii simultanei sono respinti con un avviso, senza avviare una seconda inferenza. Non è stata introdotta una coda invisibile di messaggi.
- Gli eventi di streaming portano l'identificatore del turno. Token e completamenti tardivi vengono ignorati; i timer di rendering vengono cancellati alla fine del flusso.
- L'input resta occupato fino al rilascio del turno nel backend, anche quando il testo finale è già visibile.
- Le risposte annullate durante l'inferenza non vengono salvate come risposte complete né inviate all'apprendimento. Il messaggio dell'utente già registrato può restare nella cronologia della vecchia conversazione.
- Il percorso vocale usa lo stesso controllo dei turni. Android inizializza il core con `mobile_mode=True`.

## Download

- Rimossa l'eliminazione automatica dei file non riconosciuti nella cartella dei modelli. Il controllo dei file mancanti è in sola lettura; l'API di pulizia elenca soltanto i file estranei.
- Il file Qwen è fissato alla revisione `90862c4b9d2787eaed51d12237eafdfe7c5f6077`, con dimensione esatta di 1.834.426.016 byte e SHA-256 `061b54daade076b5d3362dac252678d17da8c68f07560be70818cace6590cb1a`.
- Fonte: metadati LFS del [repository ufficiale Qwen](https://huggingface.co/Qwen/Qwen3-1.7B-GGUF/tree/90862c4b9d2787eaed51d12237eafdfe7c5f6077), letti attraverso l'API pubblica il 29 settembre 2026. Nessun peso del modello è stato scaricato durante questo lavoro.
- I trasferimenti usano `.part`. Il nome definitivo viene assegnato con sostituzione atomica soltanto dopo verifica di dimensione e hash.
- Se il server risponde `200` a una richiesta di ripresa, la scrittura riparte dall'inizio. Non aggiunge più un file completo al frammento già presente.
- Le risposte `206` richiedono un Content-Range coerente; `416` non è considerato un successo. Download troncati, dimensioni errate e checksum non validi vengono respinti.
- La ripresa conserva i byte ricevuti dopo un'interruzione di connessione. I vecchi download incompleti vengono migrati a `.part`; un file finale corrotto resta presente fino alla disponibilità di un sostituto verificato.
- Un lock per percorso impedisce download contemporanei dello stesso file tra istanze nello stesso processo. Non è un coordinamento tra servizi/processi indipendenti.
- La verifica SHA-256 viene eseguita in background, senza bloccare il thread grafico Kivy. Rientrare nella schermata non avvia un secondo download né duplica il timer del battito visivo.

## Verifiche

- Suite generale su copia temporanea offline: **269 passati, 5 falliti, 15 saltati, 4 errori di raccolta**. I fallimenti e gli errori sono gli stessi del blocco precedente.
- Dopo l'aggiunta di due ulteriori test sui download, suite di regressione completa: **33 passati**. Non è stata rieseguita inutilmente l'intera suite storica, poiché i due ultimi cambiamenti aggiungevano soltanto test.
- Test con trasferimenti simulati: ripresa HTTP 200/206, 416, troncamento, hash errato, interruzione e ripresa della connessione, file estranei conservati, download duplicato e callback finale su eccezione.
- Test di concorrenza: un solo turno su 16 invii concorrenti, cambio chat differito, eventi di annullamento, thread non ancora avviato e chiusura dello stream nativo simulato.
- Browser locale: **10 controlli passati** su DOM e funzioni JavaScript reali, con backend simulato. Verificati doppio invio, testo finale, attesa del backend, token tardivi, nuova chat, buffer/timer, Markdown e comando Interrompi. Nessun errore nella console della pagina.
- Sintassi Python/JavaScript e `git diff --check` verificati.
- Rigenerato `ZIP_DATA` in `main.py`: **169 file confrontati**, nessuna differenza rispetto ai sorgenti.

Log, XML, screenshot e hash del pacchetto sono salvati in `/Users/erikahu/ALLMA/analisi/2026-09-29/correzioni-02/`.

## Limiti e prossimi interventi

L'annullamento è cooperativo: viene controllato tra i token. Una chiamata nativa impegnata nella preparazione del prompt può terminare prima che l'annullamento venga recepito; l'interfaccia attende il rilascio effettivo. Non è stata misurata questa latenza sul telefono.

Non sono stati eseguiti inferenza reale, trasferimento del GGUF completo o collaudo su Android. I test usano piccoli file e un generatore simulato, verificando la gestione degli errori senza consumare gigabyte o modificare dati personali.

Restano aperti: ciclo di vita app/servizio Android, gestione del modello tra processi, persistenza completa di profili/impostazioni/feedback, cancellazione coordinata della memoria, test legacy e build Android riproducibile. La verifica del Markdown su browser desktop non equivale a un audit completo di sicurezza della WebView Android.

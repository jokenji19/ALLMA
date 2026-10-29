# Identità, provenienza e obiettivi persistenti — build 102558

## Percorso operativo

Il primo percorso completo usa chat e voce già collegate al core: registrare un obiettivo, conservarne criterio/progresso/prossimo passo, riprenderlo in un'altra sessione, correggerlo, registrare un risultato e confermarlo. Non richiede nuove inferenze per amministrare lo stato. Le domande aperte relative a un unico obiettivo attivo ricevono invece lo stato corrente come dato attribuito, per permettere al modello di proporre aiuto.

Lo stato appartiene ad ALLMA ed è indipendente dal modello selezionato. È conservato nello stesso archivio `action_authority` di `cognitive_state.json`, tramite `GoalProgress`: non esiste un secondo gestore di autorizzazioni o un nuovo database degli obiettivi. Il bus di eventi transitorio resta transitorio; la cronologia delle conversazioni resta il registro durevole degli eventi.

## Uso dalla chat

Esempio con dati di prova:

```text
Nuovo obiettivo: Preparare una lista di viaggio
Criterio: tre categorie controllate
Prossimo passo: scrivere la categoria abbigliamento
```

Sono facoltativi criterio e prossimo passo alla creazione. Prima di registrare un risultato occorre definire il criterio. Per gli aggiornamenti:

```text
Progresso obiettivo: categoria abbigliamento controllata
Prossimo passo: controllare i documenti

Criterio obiettivo: quattro categorie controllate

Risultato obiettivo: tutte le categorie controllate

Confermo il risultato dell'obiettivo
```

`Quali sono i miei obiettivi?` e `Riprendiamo l'obiettivo` mostrano il punto raggiunto anche in una chat nuova. `Come gestisco gli obiettivi?` mostra le istruzioni. Sono disponibili anche `Sospendi obiettivo`, `Riprendi obiettivo`, `Annulla obiettivo`, `Correggi obiettivo: …` e `Risultato obiettivo sbagliato: …`. Un obiettivo completato può essere riaperto esplicitamente; uno annullato richiede una nuova creazione.

Con più obiettivi, il sistema chiede quale aggiornare. Si può indicare:

```text
Per l'obiettivo “Preparare una lista di viaggio”: Progresso: documenti controllati
```

Una frase ordinaria, una storia o una risposta del modello non aprono automaticamente un compito. Questi sono controlli espliciti; non costituiscono comprensione universale di ogni possibile formulazione dell'intento.

## Provenienza e verifica

Ogni cambiamento è collegato a un messaggio utente durevole tramite identificatore dell'evento, conversazione, data e SHA-256 del testo. Il risultato ha fonte `user_report`. La conferma finale è `confirmed_by_user`: documenta il controllo dichiarato dall'utente, senza certificare indipendentemente un risultato fisico.

Cambiare criterio, titolo o prossimo passo, aggiornare il progresso o rifiutare il risultato invalida la conclusione precedente. Le revisioni impediscono a un aggiornamento preparato sul vecchio stato di sovrascrivere quello nuovo. I conteggi di correzioni, risultati rifiutati e confermati restano attribuiti al compito; non sono premi automatici ai pesi del modello o certificazioni di conoscenza generale.

Un compito ammette soltanto l'azione di lettura `review_goal`. Crearlo non concede strumenti esterni, notifiche, accesso alla fotocamera o al microfono. Qwen e Decider non possono modificare il suo stato attraverso il testo generato.

## Recupero e backup

L'intento del controllo è salvato nel messaggio utente prima dell'applicazione. Il registro `DeliveryUpdates` riprende gli effetti attraverso il normale percorso di recupero. Il cambiamento dell'obiettivo e il relativo checkpoint sono salvati insieme nel file cognitivo: un'interruzione fra salvataggio e conferma del registro non duplica il compito. L'identificatore della creazione deriva dall'evento e dall'utente.

Gli errori di disco non ricevono una conferma falsa di aggiornamento. Un archivio illeggibile o incoerente non viene presentato come un elenco vuoto. Le copie e il trasferimento cifrato già esistenti includono lo stato; la verifica semantica del backup controlla anche gli obiettivi. Non sono stati usati archivi personali come fixture.

## Iniziativa

`Puoi propormi il prossimo passo dell'obiettivo` abilita le proposte per il compito; `Non propormi il prossimo passo dell'obiettivo` le disabilita. Il consenso iniziale è disattivato. Restano necessari i controlli generali già esistenti su iniziativa, primo piano, inattività, energia, temperatura, cancellazione e cooldown.

Il messaggio spontaneo può proporre un passo, senza dichiararlo eseguito. La consegna ricontrolla identificatore e revisione dell'obiettivo. Correzione, sospensione, annullamento o revoca del consenso impediscono di consegnare una proposta salvata sullo stato precedente. Le proposte restano nel percorso dell'iniziativa conversazionale esistente; non vengono aggiunti invii in background o nuove autorizzazioni Android.

## Prestazioni, diagnostica e limiti

Le conversazioni ordinarie non leggono l'archivio degli obiettivi. I controlli espliciti non caricano Qwen o Decider. Il formato dell'autorità conserva il limite esistente di 256 obiettivi complessivi: non è un archivio illimitato di pianificazione. La cronologia delle dichiarazioni resta nel sistema di memoria già paginato.

La diagnostica `Obiettivi e continuità · 18 scenari` usa archivi sintetici e comprende il core reale con ricostruzione dello stato, criterio, progresso, conferma, revoca, ambiguità, proprietà dei dati, consenso, errori di scrittura e recupero del registro. È disponibile sul desktop e dalla Diagnostica Android.

Questo intervento realizza la continuità documentata di compiti espliciti. Restano da sviluppare estrazione di proposte da linguaggio libero, pianificazione generale, verificatori specifici per risultati esterni e apprendimento generalizzato delle strategie tra compiti. La visione non viene attivata.

Evidenze locali in `analisi/2026-10-24/obiettivi-continuita/`, esterna al repository: risultati pytest, 18 scenari condivisi, verifica dell'APK e collaudo Android vengono conservati separatamente. I conteggi mirati si sovrappongono alla suite completa.

## Verifica della build

- Suite completa finale: 2.468 casi superati, 15 saltati e quattro casi di arresto improvviso eseguiti separatamente fuori sandbox per OpenMP; anche questi quattro sono passati. Totale verificato: **2.472 superati, 15 saltati**.
- Batteria condivisa di continuità: **18/18** sul desktop. I test coprono anche trasferimento cifrato in una seconda installazione sintetica, mancata scrittura, mancata conferma del registro e annullamento di una proposta divenuta obsoleta.
- La prima regressione completa ha individuato un import locale di `json` che interferiva con il contesto onirico revisionato. È stato rimosso; il caso specifico e l'intera suite sono stati ripetuti con successo.
- APK 102558 / 0.9.1 verificata: payload, risorse di avvio, ABI ARM64 e componenti CPU/OpenCL/Hexagon coerenti.
- SHA-256 APK: `5234871420716f60701feec43d0397fb9901d1b76f029bded463d08815c2a693`.
- Installazione sul telefono completata con aggiornamento dei dati esistenti. Il primo tentativo di diagnostica non è partito perché l'app è passata in pausa durante l'avvio. Dopo il ritorno in primo piano il collaudo della **102558** è concluso: **18/18 scenari di obiettivi e continuità e 60/60 controlli generali**, entrambi completi.
- Lo stesso processo Android 4250 è rimasto attivo durante il collaudo; Qwen 3.5 risulta caricato su OpenCL. Gli scenari di continuità amministrano il compito senza inferenza del GGUF, usando archivi sintetici. Il caso di ripresa ricostruisce il core e rilegge lo stato nella stessa app; i quattro test di morte effettiva del processo sono stati eseguiti separatamente sul Mac.
- Nessun obiettivo o ricordo personale è stato usato come fixture. Il timeout dello schermo è stato ripristinato al valore iniziale di 60.000 ms. Report tecnico Android in `android-results.json`; il riepilogo `summary.json` distingue i risultati desktop dal collaudo del telefono.

# Verifica dei piani e collegamenti appresi — build 102563

## Controllo prima dell'adozione

ALLMA esamina alcuni requisiti numerici espliciti del criterio dell'utente. Se servono tre oggetti controllati, il controllo «almeno uno dei tre nella lista finale» ammette un risultato incompleto: uno controllato e due scoperti. Il piano può essere compatibile con l'obiettivo, ma quel controllo non ne garantisce il raggiungimento. Il riscontro espone questa lacuna senza inventare fatti fisici o dichiarare che il piano debba necessariamente fallire.

La revisione è un calcolo locale, con fonte `host_count_coverage_v1`, hash del criterio e dei passi, requisito riconosciuto, passo interessato e controesempio. I requisiti vengono estratti soltanto dal criterio esplicito dell'utente; testo citato, negazioni, quantità approssimative, durate e costrutti fuori ambito rimangono esclusi o non valutabili.

Gli esiti sono:

- `needs_review`: un controllo esplicito lascia scoperta una parte del minimo richiesto. Compare un avviso sotto la proposta e l'adozione non modifica il piano attivo.
- `no_known_gap`: non emerge una lacuna nei requisiti numerici riconosciuti. Non certifica fattibilità o correttezza generale.
- `not_automatically_checkable`: l'analisi non copre il criterio, oppure il testo non permette una conclusione sicura. Compare una nota che richiede una valutazione del contenuto; l'adozione esplicita dell'utente rimane disponibile.

Il campo `semantic_correctness_verified` resta sempre falso. `is_valid` della risposta descrive l'ammissione del messaggio nella pipeline: una proposta valida come messaggio può comunque essere un piano da rivedere. Il confine operativo è il controllo in `GoalProgress.apply`, che ricalcola il verdetto prima di adottare e non si fida dei metadati salvati.

Il controllo distingue «uno soltanto» da «uno alla volta», considera controlli completi successivi, ripartizioni esplicite e campioni di audit. Ambiguità non risolvibili restano sconosciute. Il linguaggio supportato è limitato: quantità da 1 a 999, parole da uno a dieci in italiano/inglese e alcune forme di verifica. Una lettura linguistica errata resta possibile: non è un dimostratore generale di programmi o piani.

## Controesempi conservati per la proposta successiva

La proposta e la revisione rimangono nella conversazione canonica. Un tentativo di adozione da rivedere salva atomicamente il checkpoint con il rapporto, lasciando invariati revisione e stato del compito. Il recupero dopo un arresto non deve adottare successivamente quel piano o trasformare il riscontro in un esito vissuto.

La successiva richiesta di piano può ricevere il controesempio ricalcolato sul testo durevole, per lo stesso obiettivo e revisione. Una modifica al criterio invalida il vecchio collegamento. Non esiste un secondo archivio di errori e il giudizio del controllo non diventa un ricordo autobiografico o una conferma dell'utente.

## Collegamenti fra contesti appresi dall'esperienza

Il recupero delle esperienze ora considera anche i contesti di altri compiti nei quali l'utente ha dichiarato utile una precauzione, dopo un risultato confermato. Questo crea una nuova via di recupero: una difficoltà nei «documenti di viaggio» può essere ritrovata parlando di «passaporto prima della partenza», dopo quel riscontro.

La via è indicata come `confirmed_task_bridge`, con il compito e l'evento di valutazione che l'hanno originata. Il risultato descrive un'utilità riferita dall'utente, non prova che i contesti siano identici. Ripetere il feedback non moltiplica il supporto; l'obiettivo originario non vota per se stesso. Un riscontro contrario, la riapertura del compito o la correzione del criterio possono rimuovere la via. Le esperienze restano separate per utente.

Il collegamento viene ricostruito dai dati già presenti in `workflow.learning`, senza un nuovo database, sinonimi aggiunti per gli esempi o un modello residente. Serve un'esperienza confermata che colleghi i contesti: il trasferimento automatico fra tutti i sinonimi mai incontrati resta fuori dall'ambito.

## Misure locali

Su un corpus congelato di 40 piani: **10/10 controlli insufficienti segnalati**, **0/20 blocchi nei casi legittimi** e **10/10 casi fuori ambito mantenuti non valutabili**. I test aggiuntivi variano quantità e nomi, includendo numeri mai usati nelle prime prove e singolare/plurale inglese. Questi risultati non sono una percentuale di correttezza generale.

Il testo reale della prova nella 102561, allora adottato, produce ora `needs_review`. L'altro testo sul ringraziamento rimane non valutabile automaticamente: non gli viene attribuita una certificazione numerica.

Su tre richieste nuove con lessico differente, il recupero della stessa precauzione originaria passa da **0/3 prima del riscontro** a **3/3 dopo un uso confermato**; torna **0/3 dopo il ritiro**. Altre esperienze positive pertinenti possono restare recuperabili. È una prova di collegamento appreso, non un benchmark di comprensione semantica universale.

La revisione del piccolo caso reale ha richiesto sul Mac in media **0,096 ms**, massimo 0,107 ms su 200 campioni. Registrazione, revisione e recupero non aggiungono inferenze. Il contesto aggiunto alla richiesta originale può aumentare il costo del modello, che va misurato sul dispositivo.

La suite finale comprende **2.620 test passati** e 15 saltati: 2.614 nella suite ordinaria più sei arresti reali del processo. È verificato anche il caso di arresto dopo il salvataggio del rifiuto di adozione e prima della conferma del registro. Il recupero lascia il piano non adottato e non genera un'esperienza fittizia. I casi Markdown controllano che grassetto e corsivo non nascondano il quantificatore.

## Diagnostica e confronto

`Requisiti e collegamenti appresi · 24 scenari` attraversa il controllo locale, i casi di non blocco, il core della chat, il recupero e il ritiro dei collegamenti.

`Piani · confronto requisiti · 2 coppie` effettua quattro richieste reali, con lo stesso obiettivo/criterio e seed per coppia, nuove chat e ordine alternato. Una variante riceve il criterio ordinario, l'altra anche la rappresentazione dei requisiti e le istruzioni di copertura. Il controllo locale rimane attivo in entrambe; nessuna proposta viene eseguita e non ci sono retry nella singola prova. La diagnostica applica un tetto comune di 192 token, fino a 64 per il ragionamento, mantenendo sempre le protezioni termiche. Il report confronta i budget effettivamente registrati, invece di presumerli uguali. Quattro testi non permettono di stimare una percentuale generale di miglioramento della qualità.

Nella prima prova sulla 102562, i 132 scenari software e la verifica dell'avviso nella WebView sono passati. La seconda coppia reale ha però ricevuto budget diversi (224 e 192 token) per effetto dei limiti termici. I risultati sono conservati come prova non controllata, non come dimostrazione di efficacia delle istruzioni. La 102563 corregge il solo tetto della diagnostica; una successiva suite mirata di **151 test** è passata. Le chat normali mantengono i loro budget e le loro protezioni.

## Risultato finale sul dispositivo

La **102563** è installata e verificata sul Samsung S25 Ultra. SHA-256 dell'APK: `b92bd6c1417acddf303f0854172eb35e4c6c7a75f39af83400004031dfca10ea`. Payload Python, risorse iniziali e backend nativi corrispondono ai sorgenti.

Sono passati di nuovo **132/132 scenari software**: 60 generali, 26 di obiettivi/piani, 22 di apprendimento dagli esiti e 24 di requisiti/collegamenti. L'avviso è stato verificato anche nel DOM della WebView: testo numerico corretto e nessun duplicato. Nessuna conversazione personale è stata usata dalla diagnostica.

Il confronto finale ha completato **4/4 richieste**, una generazione per variante, senza retry interni. Entrambe le coppie hanno stesso obiettivo e seed, budget totale **192**, ragionamento **64**, risposta **128**, temperatura **0,6** e top-p **0,95**. Ordine A/B per gli oggetti, B/A per i documenti. Il report conferma `budget_matches=[true,true]`.

| Caso | Variante | Tempo totale | Sola generazione | Esito locale |
|---|---|---:|---:|---|
| Tre oggetti | Criterio ordinario | 18,78 s | 9,45 s | Non valutabile automaticamente |
| Tre oggetti | Requisiti espliciti | 11,72 s | 10,32 s | Nessuna lacuna numerica rilevata |
| Cinque documenti | Requisiti espliciti | 13,08 s | 11,24 s | Nessuna lacuna numerica rilevata |
| Cinque documenti | Criterio ordinario | 12,24 s | 10,37 s | Nessuna lacuna numerica rilevata |

«Non valutabile» non significa risposta errata: la prima proposta parla comunque di tre elementi e assenza di duplicati, ma la formulazione implicita non è coperta dal controllo. Con requisiti espliciti gli oggetti ricevono un controllo diretto sui tre elementi; il testo introduce però anche tre categorie e un campione, dettagli non necessari. Il piano dei documenti con requisiti aggiunge una cronologia degli eventi non richiesta. Il filtro numerico non certifica questi aspetti semantici.

Quindi non si deduce un miglioramento percentuale della qualità generale o della velocità. Il primo tempo totale comprende un costo iniziale maggiore della pipeline; la sola generazione delle varianti con requisiti è leggermente più lunga in questo giro. I confronti restano esplorativi, su due obiettivi, con possibili effetti di cache e condizioni del dispositivo.

Qwen ha usato OpenCL; Decider è ricaduto sulla CPU con motivo `npu_thermal_unavailable`. Nessun crash, processo rimasto attivo, tempo di spegnimento ripristinato a 60 secondi. Le protezioni termiche e i limiti delle chat normali sono conservati.

Evidenze locali: `analisi/2026-10-25/verifica_piani/`, esterna al repository. I report separano test software, replay del testo precedente, dati del modello reale e osservazioni umane.

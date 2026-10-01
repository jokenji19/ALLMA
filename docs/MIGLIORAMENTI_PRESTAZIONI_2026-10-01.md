# miglioramenti_prestazioni — 1 ottobre 2026

Baseline comunicata dall'utente: sei domande, 76,81 s medi; L2 e C2 senza risposta finale a 768 token.

## Interventi
- Budget separato: massimo 128 token di ragionamento e 384 di risposta per richieste complesse (l’esperimento 256 + 384 è stato ritirato dopo le prove mirate); 64 e 192 per richieste ordinarie. Il limite energetico di 64 token totali resta rispettato tramite divisione proporzionale.
- Due segmenti della stessa completion, con chiusura esplicita del ragionamento; nessuna domanda duplicata o conversazione sintetica. La seconda fase include prompt e ragionamento precedente. Lo stop naturale può anticipare entrambi i limiti.
- Cancellazione controllata in entrambe le fasi; iteratori chiusi e lock rilasciato.
- Prompt generale orientato a concisione, vincoli, ipotesi e coerenza. Rimossa l'istruzione specifica sul paradosso del boia dal prompt principale.
- Errori distinti: limite esaurito, output vuoto e errore inferenza. Questi casi non dichiarano arbitrariamente il modello offline; risposte fallite marcate non valide.
- Metadati associati alla risposta e preservati nella risposta finale; conteggi separati ragionamento/risposta, arresti, budget, TTFT e tempo generazione. I conteggi sono esplicitamente marcati come ritokenizzati, non token nativi esatti.
- Benchmark senza retry correttivi nascosti; nessuna lettura di metriche globali potenzialmente obsolete; metriche mancanti non stimate; distinzione tra velocità end-to-end e generazione. Esportazione Markdown e JSON, risultati azzerati tra esecuzioni.

## Verifiche
77 test di regressione passati nella prima iterazione, inclusi esaurimento ragionamento con risposta riservata, cancellazione, errori e conservazione metadati, assenza di retry e metriche obsolete nel benchmark.
Build debug verificata: SHA256 `32858a28cf8ad58d8d0f6bb2cfa114a156c8be4fac41f5f813c2dbaf69c80ddf`.
Confronto Android in corso. I budget ridotti non dimostrano da soli un aumento di qualità o velocità: occorre valutare output e tempi effettivi.

## Primo confronto Android
Sei risposte finali, nessun fallback per risposta vuota; tempi L1 52,81 s, L2 33,39 s, C1 44,20 s, C2 52,96 s, E1 57,55 s, E2 49,12 s. Media 48,34 s, circa -37% rispetto alla singola baseline dell'utente. Non è un esperimento controllato: temperatura, caricamento e casualità differiscono. Qualità ancora insufficiente: L1 deduzioni non supportate, L2 spiegazione contraddittoria, C1 metafore extra e imprecisioni, C2 usi non praticabili dello specchio, E1 elusione dell'ipotesi, E2 astratta. Lo stato `completed` segnala fine della generazione, NON correttezza semantica.

## Seconda iterazione
Rilevamento di correzioni esplicite anziché parole generiche come "errore" o "bugia". Richiami alle correzioni limitati a utente e conversazione con provenienza esplicita; i vecchi record non vengono cancellati. Rimossa dal prompt la lista delle chiavi della mappa del sé, conservando la funzione operativa. Istruzione generale per 3-5 frasi/circa 80 parole salvo richieste di dettaglio e per non aggiungere cause non giustificate.
85 test di regressione passati. Build finale verificata e installata: SHA256 `9dcd96335ccf3f8f4d4349c350f2bcc2474fdc1579aae16aa4a3e85bf73b393e`.

## Benchmark salvato dall’utente, 14:28
Media 46,33 s contro 76,81 s iniziali (circa -39,7% nel confronto tra queste due esecuzioni, non controllato). Sei risposte finali, senza falso messaggio di modello offline. Tutte le prove hanno esaurito 128 token di ragionamento. L2 resta errata; C2 non soddisfa la praticità richiesta; E1 elude l’ipotesi; L1, C1 ed E2 contengono imprecisioni o spiegazioni astratte. La riduzione della latenza non implica qualità sufficiente.

## Terza iterazione, verifica mirata
Budget complesso aumentato a 256 token di ragionamento + 384 di risposta, massimo 640. Eliminato il vincolo interno di un terzo: rimane almeno metà del budget totale riservata alla risposta quando intervengono limiti energetici. Aggiunti `reasoning_truncated` e somma `total_tokens`, sempre con conteggi ritokenizzati. 11 test mirati passati (budget, cancellazione, risposta core e benchmark).
APK verificato e installato con aggiornamento conservativo: SHA256 `876621ad964b450f6952d2582ca09b9ff735111fb06704dc1cb4beff4c4a922c`. La maggiore disponibilità di ragionamento è un’ipotesi da verificare con L2 e C2, non una garanzia di correttezza.

La prima prova L2 è stata annullata dal passaggio dell’app in pausa dopo circa 72 s, prima della risposta finale; esclusa dalla valutazione. Ripetizione esplicita in chat ordinaria, non nel benchmark; il contesto della conversazione e i prompt senza accenti rendono il confronto non controllato.

### Esito delle prove mirate e impostazione finale
L2: 53,69 s, risposta errata; C2: 82,37 s, usi poco pratici e due proposte quasi identiche. Risposte salvate in `analisi/2026-10-01/miglioramenti_prestazioni/prove-budget-256.json` nella cartella superiore del progetto. Sono prove in chat ordinaria con contesto condiviso, prompt senza accenti e telefono caldo; non costituiscono un confronto controllato né dimostrano che il limite di ragionamento sia irrilevante. Non offrono evidenza sufficiente per mantenere il limite maggiorato: ripristinato il default 128 + 384 (512 totali). Conservati i nuovi metadati diagnostici e il supporto interno a budget maggiori. Qualità semantica ancora irrisolta; nessuna risposta preimpostata per aggirare il benchmark.

APK finale verificato: SHA256 `544f7efa1479c7ac793daf05e210af68411f7bca047c443a16bf83502a44adf2`, payload conforme ai sorgenti e architettura ARM64. Aggiornamento Android effettuato con `install -r`, senza cancellazione dei dati. Le modifiche sono salvate localmente; non è stato creato un commit Git.

# Ciclo operativo delle capacità — 15 ottobre 2026

## Scopo distribuito

Il recupero della memoria nella chat e nella voce condivisa con il core passa ora attraverso il ciclo di azione reale, anziché usare quel ciclo soltanto nella diagnostica. La scelta del modello è una proposta; ALLMA ammette una lettura limitata alla richiesta e al suo utente, esegue il recupero e osserva il risultato prima di comporre il prompt di Qwen.

- Una scelta `memory` già selezionata viene riutilizzata come prima proposta: zero inferenze aggiuntive per eseguire e verificare il recupero.
- Le richieste personali protette possono eseguire una ricerca per decisione del codice anche se il modello sceglie male o si astiene. La telemetria distingue `decider` da `host_memory_policy`.
- L'autorizzazione di lettura è effimera, scade anche su eccezioni e cancellazione e non riempie l'archivio di 256 obiettivi persistenti. Non consente scritture o azioni esterne.
- Calcoli esatti, identità e risposte già confermate mantengono i percorsi diretti. Il router non propone più un calcolatore senza argomenti eseguibili: le espressioni supportate sono già state risolte prima di quel punto.
- I backend vettoriale e TF-IDF sono vincolati all'utente. Sono ammessi soltanto resoconti attribuiti all'utente, con metadati validi, contenuto non vuoto e punteggio finito. I risultati sono ordinati e limitati a tre.
- Un esito di lettura verificato significa provenienza/esecuzione controllate, non verità del contenuto né correttezza della risposta.
- Ricerca riuscita, ricerca vuota e ricerca fallita vengono distinte nel prompt. Un risultato vuoto non dimostra che un'esperienza non sia mai avvenuta. Nessun retry nascosto dopo un errore.
- L'ottimizzazione del prompt SIMPLE non elimina più i ricordi recuperati per una domanda breve.

## Memoria degli esiti e limiti

La sezione persistente `decision_outcomes` conserva contatori per utente (chiave SHA256): tentativi, osservazioni completate, recuperi con risultati, errori e proposte provenienti da Decider. Non salva i testi delle domande né dei ricordi; massimo 128 chiavi utente. Le altre sezioni cognitive restano conservate. I contatori sono diagnostica operativa: non sono conferme dell'utente e non costituiscono apprendimento di una politica di instradamento. Non vengono usati per auto-promuovere ricordi, modificare personalità o confermare fatti.

Questo intervento collega un ciclo reale e limitato di recupero alla conversazione; non introduce un agente generale su tutti i moduli. Obiettivi persistenti su più turni, adattamento della politica in base a feedback espliciti, verifiche scientifiche indipendenti e scelta generale fra tutte le capacità richiedono ulteriori implementazioni e misure. Il limite di un'azione evita di aggiungere giri di inferenza senza evidenza di utilità.

## Verifica

- Prima selezione: 58 test passati su azioni, autorità, runtime e motore.
- Selezione finale mirata: 98 test passati su azioni, autorità, runtime, motore, fonti e continuità. Include i primi 58: non sommare.
- Include prove di isolamento degli utenti, rifiuto dei messaggi dell'assistente come ricordi, punteggi non validi, scadenza/revoca dell'autorizzazione, cancellazione, errore senza retry, ricerca vuota e persistenza dei soli contatori.
- Il 16 ottobre sono stati ripetuti e salvati stabilmente 98 test mirati (0,41 s) e 6 test di integrazione del core (11,37 s), tutti passati. I primi test del prompt usavano un Mock che esercitava il percorso legacy; corretto il motore simulato per usare davvero prepare_chat. Il risultato della precedente suite ampia non è attestato qui: i suoi log temporanei non sono più disponibili.

## Installazione e collaudo Android — 16 ottobre

Confermata sul telefono versione 0.9.0.0, codice 102483. APK verificata prima dell’installazione: payload coerente, runtime ARM64 llama-cpp-python 0.3.36 con supporto qwen35, SHA256 `5aaefad13c2d160051ffe6ace7b95ad4238167099c4dedf26a0a8827181eb786`.

Prova manuale sintetica LUNA-483: risposta corretta in entrambi i turni. Nei log il ciclo reale esegue una lettura per turno con tre record ammessi, rispettivamente 39,50 ms e 40,75 ms, zero inferenze aggiuntive del ciclo. Decider si astiene in entrambi i turni (6,038 s incluso primo caricamento; 1,419 s al secondo); l’azione è dunque proposta da `host_memory_policy`, non scelta con sicurezza da Decider. Generazione Qwen 17,983 s e 14,386 s. Nel secondo turno la somma decisore + recupero + generazione è circa 15,85 s, non una misura esatta end-to-end della UI.

La prova conferma integrazione del ciclo e risposta corretta, ma il codice era anche nella cronologia: non dimostra recupero esclusivo dalla memoria a lungo termine. Nessun traceback nei log selezionati del processo corrente. La lettura verificata non certifica il contenuto generale delle risposte. Non viene dichiarato un miglioramento percentuale, energetico o di velocità rispetto a un controllo assente.

Report sintetico e log dei test: `/Users/erikahu/ALLMA/analisi/2026-10-16/decider/`. Per verificare separatamente la memoria persistente servirà una nuova conversazione senza il codice nel contesto, idealmente anche dopo un riavvio.

## Richiamo dopo riavvio e nuova conversazione — 16 ottobre

Processo Android riavviato (21300 → 24584); caricamento nativo riuscito. Nuova conversazione `f12f8b14-bb8f-4936-8b28-d5b44f293531`, diversa dall’originale `8c599b60-c6fc-463a-ac46-9a367077e61d`, con zero messaggi precedenti nella cronologia durabile. Inviata soltanto «Quale codice di prova ti avevo indicato?», senza il valore atteso. Un primo invio è stato cancellato dall’interfaccia prima del recupero e non viene conteggiato.

Risposta completata: «Il codice di prova indicato in questa sessione è **LUNA-483**.» Il valore è corretto anche in assenza della conversazione originale nella cronologia corrente, dopo il riavvio del processo. È evidenza di richiamo persistente attraverso ALLMA in questo singolo caso; non una misura generale di affidabilità della memoria. Non è un recupero automatico di risposta confermata: `source=model_generated`; Qwen è stato utilizzato.

Decider: astensione, totale 6,146 s incluso nuovo caricamento (inferenza 0,901 s). Recupero deciso dalla politica di ALLMA, tre record ammessi, 37,39 ms, zero inferenze aggiuntive del ciclo. Qwen: 14,548 s, 128 token di ragionamento e 17 di risposta, stop normale. La somma decisore + lettura + generazione è circa 20,73 s, senza certificare la latenza UI completa. Nessun traceback nei log selezionati della prova.

Limite emerso: la formulazione «in questa sessione» attribuisce imprecisamente il dato alla chat corrente. Il prompt di memoria compatta le dichiarazioni senza esplicitare la distinzione fra conversazione di origine e conversazione corrente: va migliorata la provenienza temporale mostrata al modello. Non è stata inserita una correzione preconfezionata della risposta del test. Il richiamo è positivo; scelta autonoma del percorso da parte di Decider e precisione nell’attribuzione non sono ancora risolte.

Report: `/Users/erikahu/ALLMA/analisi/2026-10-16/decider/android-memory-after-restart.json`. Nessuna modifica al codice o nuova APK in questa prova.

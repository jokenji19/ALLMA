# Piani proposti, adozione e verifica dei passi — build 102560

## Percorso

Il modello può proporre un piano per un obiettivo persistente già registrato. ALLMA controlla struttura, fonte e revisione della proposta; i passi diventano stato operativo soltanto dopo un comando esplicito dell'utente. Le descrizioni dei passi non diventano chiamate a strumenti o nuove autorizzazioni.

Esempio:

```text
Nuovo obiettivo: Preparare una lista di viaggio
Criterio: tre categorie controllate

Proponi un piano per questo obiettivo

Adotta questo piano

Risultato del passo: prima categoria controllata

Confermo il risultato del passo
```

Il controllo del risultato e la conferma sono due eventi distinti. L'indice del piano avanza solo dopo la conferma. Per un esito errato si usa `Risultato del passo sbagliato: …`: il passo rimane aperto e conserva il riscontro nella cronologia.

Anche dopo la conferma di tutti i passi, il criterio complessivo dell'obiettivo richiede ancora il percorso `Risultato obiettivo: …` e `Confermo il risultato dell'obiettivo`. Chiudere esplicitamente l'obiettivo non inventa verifiche dei singoli passi rimasti aperti.

## Controlli

- Una proposta ha da due a cinque passi numerati consecutivamente, senza duplicati, sottoliste o continuazioni intermedie che il parser dovrebbe scartare. Introduzioni diverse dalla semplice intestazione ed eventuali osservazioni finali sono conservate in note esplicite, per un massimo di 600 caratteri; oltre il limite la proposta non viene ammessa. Le note sono mostrate nel piano adottato e attribuite alla proposta del modello anche nel contesto successivo. L'accettazione della struttura non certifica fattibilità o correttezza del contenuto.
- La proposta viene salvata nella risposta della conversazione, con identificatore, hash del testo e riferimento all'obiettivo/revisione. Non esiste un secondo archivio persistente dei piani proposti.
- Per adottarla, ALLMA verifica risposta durevole, proprietà dell'utente, stato valido, hash e revisione. Un testo alterato, un'altra identità o un obiettivo corretto impediscono l'adozione.
- La ricerca iniziale considera gli ultimi 64 messaggi disponibili dell'utente, anche tra chat diverse. Se una nuova richiesta di piano fallisce o viene interrotta, il sistema non adotta silenziosamente una proposta precedente.
- Il piano adottato entra nello stesso stato `GoalProgress` della build 102558. Contiene passi, indice corrente, risultati dichiarati e riferimenti alle conferme. Le fonti restano `model_proposal`, `user_admitted_model_proposal` e `user_report`; non diventano osservazioni fisiche verificate.
- Correzioni a obiettivo, criterio, progresso o prossimo passo mettono il piano in revisione. I vecchi passi non continuano a guidare l'iniziativa. Il piano precedente resta documentato nella cronologia.
- La conferma di un passo usa lo stesso registro di recupero e checkpoint atomico dell'obiettivo. Un arresto fra scrittura e conferma del registro non deve far avanzare due volte.
- I backup verificati controllano anche la struttura dei piani e la provenienza dei risultati/conferme. Gli archivi precedenti senza piani restano compatibili.

## Adattatore e prestazioni

Il vecchio `PlanningSystemAdapter` restituiva compiti generici e durate fisse pur non disponendo dei vincoli necessari. Ora fornisce soltanto indicazioni di pianificazione, con `has_plan=False`, nessun compito inventato e nessuna durata stimata. Il piano concreto usa il modello e lo stato persistente già esistenti.

La richiesta di proposta effettua una sola generazione, senza tentativi nascosti. Adottare, registrare il risultato e confermare un passo sono operazioni del core che non richiedono Qwen o Decider. I richiami delle risposte dipendenti dall'obiettivo includono identificatore/revisione; la proposta di piano non usa una vecchia risposta appresa.

La memoria e l'identità di ALLMA restano indipendenti dal GGUF. Non vengono introdotti un altro pianificatore persistente, un altro modello residente o strumenti esterni.

## Misure

La diagnostica condivisa `Obiettivi, piani e continuità` passa da 18 a **26 scenari sintetici**, aggiungendo proposta non adottata, adozione, conferma, rifiuto, revisione, fonte obsoleta, recupero e ricaricamento.

La diagnostica `Proposte di piano · 2 prove con modello` condivide il solo motore già caricato e usa stato/persona/memoria temporanei. Ogni caso genera una proposta una sola volta e poi verifica il percorso di adozione/conferma, quando il formato è ammissibile. La qualità semantica resta da valutare separatamente; un formato valido non viene presentato come accuratezza generale.

Evidenze locali: `analisi/2026-10-24/pianificazione/`, esterna al repository. Suite desktop, arresti del processo, pacchetto Android e prove sul telefono sono registrati separatamente.

Verifiche della build 102560:

- Desktop: **2.496 test passati**, 15 saltati. Il totale unisce la suite ordinaria (2.491) e i cinque arresti reali del processo, eseguiti separatamente per i limiti OpenMP della sandbox.
- Android: **26/26 scenari obiettivi e piani** e **60/60 scenari generali** superati su Samsung S25 Ultra. Sono controlli software sintetici; il 100% dei casi superati non misura l'affidabilità generale o la qualità delle risposte.
- Sintassi JavaScript e `git diff --check`: superati.
- APK: contenuto Python, risorse iniziali e backend nativi coerenti con i sorgenti. SHA-256: `e0655c69d6b20f3b4705acc903d86784816dfe8576259d3dc9794d31ff069b0f`.

### Due proposte reali con Qwen 3.5 2B

Nella 102559 una proposta su due era adottabile: il primo testo conteneva tre passi seguiti da una domanda, che il parser respingeva per evitare di perderla. Nella 102560 le note diventano parte esplicita della proposta. Ripetendo gli stessi due obiettivi sintetici con gli stessi seed e budget, entrambe le risposte sono state salvate e adottate; in entrambi i casi il risultato del primo passo è rimasto in attesa fino alla conferma esplicita.

| Caso | Proposta completa, tempo totale | Proposta adottata | Passo avanzato solo dopo conferma |
|---|---:|---|---|
| Lista di tre oggetti | 27,04 s | Sì | Sì |
| Messaggio di ringraziamento | 11,92 s | Sì | Sì |

Il passaggio da 1/2 a 2/2 riguarda la compatibilità del flusso su questi due testi, non un aumento percentuale dell'intelligenza. Non è un confronto di velocità: i testi e le condizioni del dispositivo differiscono. Non sono stati aggiunti retry. I tempi comprendono tutta la pipeline; la sola generazione ha richiesto rispettivamente 14,88 e 9,91 secondi.

La valutazione umana dei testi trova ancora limiti: la prima proposta resta generica e la domanda finale parla impropriamente del «mio stato attuale»; la seconda contiene una formulazione poco naturale sul tono professionale. Le note sono visibili e attribuite al modello, ma il parser non ne certifica l'utilità. Nessun risultato fisico è stato osservato: il riscontro del passo era esplicitamente sintetico.

Qwen ha usato OpenCL; in questo giro Decider è ricaduto sulla CPU con motivo `npu_thermal_unavailable`. I backend GPU/NPU rimangono nel pacchetto, con il fallback previsto. Processo rimasto attivo, versione installata 102560, tempo di spegnimento ripristinato a 60 secondi. Nessun ricordo personale usato o modificato dalla diagnostica.

## Limiti

È pianificazione assistita con controllo documentato dei passi. L'esecuzione autonoma di strumenti, la verifica indipendente di risultati fisici e l'apprendimento generalizzato delle strategie fra compiti restano interventi successivi. Il modello può ancora proporre passi poco utili: l'utente ne valuta il contenuto prima dell'adozione.

# Apprendimento dagli esiti dei piani — build 102561

## Comportamento

Gli esiti degli obiettivi e dei passi alimentano ora una proiezione di esperienza persistente. Un risultato soltanto dichiarato resta in attesa: occorre la conferma esplicita, oppure una correzione che documenti il problema incontrato. La proiezione conserva il testo del riscontro, il passo e i riferimenti all'evento di dichiarazione e di revisione. La fonte è sempre `user_report`, non una verifica fisica indipendente.

Da una difficoltà riferita ALLMA ricava una precauzione contestuale: verificare se quel problema è rilevante prima di ripetere un compito simile. È un'ipotesi, non una causa dimostrata. Gli esiti positivi restano esempi documentati e non diventano automaticamente regole di successo. Il contenuto appreso cambia con i riscontri dell'utente; il meccanismo che seleziona e valuta i casi rimane una procedura scritta nel codice.

Quando si chiede un nuovo piano, il contesto può includere fino a due esperienze pertinenti di altri obiettivi dello stesso utente. Le istruzioni al modello distinguono precedenti, ipotesi e controesempi. I metadati della risposta riportano gli identificatori dei casi effettivamente forniti, senza certificare che il modello li abbia seguiti correttamente. Il piano resta una proposta da adottare.

## Uso

```text
Cosa hai imparato dai piani?

Lezione utile: IDENTIFICATORE
Lezione non utile: IDENTIFICATORE
Dimentica lezione: IDENTIFICATORE
```

La valutazione si collega al nuovo obiettivo attivo. Se è già completato o ci sono più obiettivi, usare il riferimento esplicito:

```text
Per l'obiettivo “Lista viaggio montagna”: Lezione utile: IDENTIFICATORE
```

Per un riscontro positivo occorre un risultato confermato del nuovo compito. Per quello negativo è ammesso anche un esito corretto esplicitamente. Il compito originario non può confermare la propria ipotesi. Lo stesso compito vota una volta sola, e la valutazione successiva sostituisce quella precedente. Descrizioni identiche di obiettivo e criterio non diventano esperimenti indipendenti cambiando chat o identificatore.

Tre compiti distinti con riscontro positivo permettono l'etichetta `supported_by_user_reports`. Non è una probabilità di correttezza né una prova causale. Un riscontro contrario rende l'ipotesi `contested`: rimane consultabile come cautela, ma il prompt vieta di presentarla come regola accertata. Il ritiro esplicito la esclude dal recupero. Correzione del compito originario, modifica del criterio, riapertura o annullamento ritirano le vecchie proiezioni; la riapertura di un compito che forniva supporto ritira anche il suo voto.

## Persistenza, integrazione e costo

- L'esperienza è una sezione opzionale `workflow.learning` nello stesso archivio di `GoalProgress`. Nessun nuovo database, modello residente o registro di conversazione.
- Avanzamento, esito e checkpoint del registro di recupero condividono la stessa scrittura atomica. Un arresto dopo il commit e prima dell'ack non ripete l'apprendimento.
- La conversazione resta la storia canonica. Per ogni obiettivo la proiezione conserva l'ultimo esito per passo/tipo, al massimo 12 slot, e fino a 32 valutazioni di ipotesi. I casi sostituiti restano nella conversazione; non si sostiene un recupero illimitato di tutte le strategie storiche. Il limite preesistente di 256 obiettivi non viene modificato.
- Casi, riferimenti, identificatori e valutazioni vengono controllati prima dell'uso e durante la verifica dei backup. Gli archivi precedenti senza la nuova sezione restano validi. Le prove includono esportazione cifrata e ripristino su un'installazione sintetica diversa.
- Registrazione, consultazione e valutazione non aggiungono inferenze Qwen/Decider. Il recupero avviene solo quando è richiesto un piano, non nei normali turni della chat. Gli estratti sono limitati a 120 caratteri per ambito/passo e 240 per riscontro.
- La proposta resta una singola generazione, con gli stessi budget del modello. Il contesto aggiunto può aumentare il tempo di preparazione del modello: non si presume un guadagno di velocità da questo intervento.

## Verifiche desktop

- **80 test mirati passati**, compresi chat completa, metadati di provenienza, riavvio, replay, esportazione/ripristino e diagnostica del modello isolata.
- **2.529 test complessivi passati**, 15 saltati: 2.524 nella suite ordinaria più cinque arresti reali del processo, eseguiti separatamente per i limiti OpenMP della sandbox.
- La nuova batteria condivisa desktop/Android contiene **22 scenari**; due attraversano anche il core della chat con modello simulato.
- Misura controllata prima/dopo una sola esperienza sintetica: recupero del caso su **5/5 nuovi compiti con lessico simile**, contro 0/5 prima dell'esposizione; **0/5 richiami nei compiti estranei**. Su tre parafrasi con vocabolario diverso il recupero resta **0/3**. Questo misura un trasferimento contestuale conservativo, non apprendimento generale.
- Su un archivio sintetico piccolo, lettura e selezione hanno richiesto in media **0,144 ms**, massimo 0,699 ms su 100 campioni Mac. Non è una stima per archivi grandi o per il telefono.

Evidenze: `analisi/2026-10-24/apprendimento_piani/`, esterna al repository. I risultati Android e le risposte del modello reale sono registrati separatamente.

## Collaudo Android completato

Build **102561**, versione pubblica 0.9.1, installata sul Samsung S25 Ultra. Pacchetto e payload verificati, SHA-256 `8e20c04f33f070b5c11000708ee3ce5d46c0a43af1d5765d51ddc5b5b9a98378`.

- **108/108 scenari software passati:** 60 generali, 26 obiettivi/piani e 22 apprendimento dagli esiti. I nuovi casi comprendono chat completa, trasferimento contestuale, controesempi, ritiro, proprietà dell'utente, riavvio e scrittura atomica.
- Due proposte reali con Qwen 3.5 2B, ciascuna in un profilo temporaneo. Prima del nuovo obiettivo vengono registrati un esito errato sintetico e la relativa correzione, senza inferenze aggiuntive; la proposta avviene in una nuova conversazione. In **2/2** casi il modello ha ricevuto gli identificatori dell'esperienza negativa (`candidate`) e di quella positiva (`user_confirmed_result`).
- In **2/2** casi il piano era strutturalmente adottabile e il primo passo è avanzato solo dopo il risultato e la conferma sintetici. Questo verifica il percorso software, non la correttezza del piano né la realtà del risultato.

| Caso | Tempo totale proposta | Token prompt | Generazione | Esame umano |
|---|---:|---:|---:|---|
| Lista di tre oggetti | 22,05 s | 1.242 | 12,62 s | Non adeguato: propone di controllare almeno uno dei tre elementi, pur dovendoli controllare tutti. Riprende il tema degli elementi mancanti, ma non rispetta pienamente il criterio. |
| Messaggio di ringraziamento | 13,88 s | 1.255 | 11,67 s | Parzialmente pertinente: chiede il motivo specifico del ringraziamento, coerente con il problema precedente. Rimangono un passo generico e un errore grammaticale. |

Non è stato eseguito un confronto cieco equivalente senza esperienza: queste due risposte non dimostrano un miglioramento percentuale della qualità semantica. Il sistema rende utilizzabili i precedenti, ma il modello può ancora interpretarli male. La conferma diagnostica del passo è un dato sintetico per collaudare lo stato, non una valutazione umana di queste risposte.

Qwen ha usato OpenCL. Decider è ricaduto sulla CPU con motivo `npu_thermal_unavailable`; budget e backend non sono stati modificati in questa fase. Nessun crash, processo rimasto attivo, spegnimento dello schermo ripristinato a 60 secondi. La diagnostica non ha usato i ricordi personali dell'utente.

## Limiti

La pertinenza usa un filtro lessicale: almeno due termini significativi condivisi e rapporto di sovrapposizione minimo. Il recupero semantico fra formulazioni completamente diverse rimane da sviluppare. Non vengono inventati sinonimi per far passare gli esempi del benchmark.

Il sistema non apprende automaticamente cause fisiche, non riscrive il proprio codice e non riaddestra Qwen. Le regole generali non emergono ancora in modo aperto: questo intervento introduce precedenti documentati, precauzioni verificabili e revisione mediante esiti successivi. L'esecuzione di strumenti conserva le autorizzazioni preesistenti.

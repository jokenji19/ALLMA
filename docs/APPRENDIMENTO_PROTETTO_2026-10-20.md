# Apprendimento protetto — 20 ottobre 2026

Il perfezionamento parte dal recupero sicuro delle risposte confermate. L’archivio AnswerRecall resta distinto dalla memoria autobiografica, dalle preferenze e dai pesi del modello linguistico.

## Difetti corretti

1. Un archivio parzialmente danneggiato veniva caricato per i record ancora validi; una successiva osservazione poteva riscriverlo eliminando gli altri record. Ora il caricamento valida l’intero candidato prima di pubblicarlo. In caso di errore il file resta intatto e le normali scritture sono bloccate.
2. JSON troncati, formato errato e versioni non supportate non autorizzano più la creazione implicita di un archivio nuovo. Anche una versione booleana viene rifiutata.
3. La conservazione usa il meccanismo condiviso di copie private: due corruzioni diverse producono due copie distinte. Se la copia non riesce, l’originale resta comunque protetto dalla sovrascrittura.
4. Un ricaricamento fallito conserva lo stato precedente in RAM ma ne sospende il richiamo automatico. Dopo il ripristino di un file valido, `load_state()` riabilita l’archivio; i nuovi aggiornamenti possono ripartire dal punto persistito.
5. Le voci precedentemente salvate vengono ricontrollate anche rispetto all’attuale regola di ammissibilità: domande temporali o personali escluse dal richiamo non tornano utilizzabili solo perché presenti in un vecchio file.
6. Se l’utente conferma o rifiuta una risposta mentre l’archivio richiede recupero, ALLMA dichiara che il riscontro non è stato registrato. Non chiama il modello per inventare una conferma di salvataggio. Il messaggio contiene metadati distinti e non dichiara conoscenza integrata.

Le risposte normali possono continuare con il modello. L’apprendimento derivato che dipende dall’archivio non disponibile resta esplicitamente in attesa nel giornale degli aggiornamenti: non viene dichiarato completato né saltato silenziosamente. Le protezioni non ricostruiscono dati mancanti e non riparano automaticamente il contenuto corrotto.

## Evidenze

I primi dieci scenari sono stati scritti ed eseguiti prima della modifica: un caso passava e nove fallivano. Dopo la correzione passano tutti e dieci, senza regressioni in quel campione. Sono riproduzioni note che hanno guidato lo sviluppo, non una stima dell’affidabilità universale.

- 342 test di integrazione superati: persistenza, ammissione delle risposte, apprendimento, ripartenza, personalità, continuità, backup e controlli del core.
- 60/60 scenari della batteria operativa standard sul Mac, con archivi temporanei e generazione simulata. Nessuna misura di qualità del GGUF, temperatura o batteria viene dedotta da questi test.
- Le nuove prove comprendono corruzione parziale e completa, conservazione degli originali, copia non riuscita, ricaricamento dopo riparazione, file rimosso, compatibilità con archivi senza checkpoint e comportamento dei turni reali del core.
- Il primo giro delle prove di arresto improvviso è stato impedito dalla memoria condivisa OpenMP nel sandbox; il giro autorizzato successivo ha superato tutti i casi. Il fallimento dell’ambiente è conservato e non viene contato come difetto corretto.
- Inventario statico: 208 moduli, 135 raggiungibili dalle tre radici principali, nessun errore sintattico e nessuna base di import locale assente nei percorsi principali. Il riferimento storico a `allma_model.data.vocabulary_data` resta fuori da questi percorsi. La raggiungibilità statica non dimostra che ogni componente sia operativo né autorizza a eliminare gli altri 73 moduli.

Evidenze complete in `/Users/erikahu/ALLMA/analisi/2026-10-20/apprendimento-protetto`: confronto per caso, XML, batteria standard, inventario e verifica del pacchetto.

## Prossime priorità

- Qualità su domande nuove: separare correttezza fattuale, rispetto delle istruzioni, attribuzione all’utente e utilità della risposta; confrontare ALLMA e modello con le stesse condizioni.
- Continuità: prove combinate di correzioni, revoche, nuove chat, cambi di modello e ripartenze, su archivi sintetici progressivamente più grandi.
- Apprendimento: misurare quali risposte diventano recuperabili e con quali fonti, senza trasformare la sola ripetizione del modello in verità.
- Prestazioni Android: misurare attesa del primo testo, durata totale, memoria e condizioni termiche in un confronto controllato. Le prove software non sostituiscono queste misure.

Le modifiche non costituiscono una migrazione generale della storia JSON a un archivio paginato. Quella resta un intervento separato per volumi molto grandi. Nessun nuovo commit, push o rilascio GitHub in questo intervento.

## Consegna Android

Build **102528** compilata, verificata e installata senza disinstallare ALLMA. Il contenuto incorporato e le risorse iniziali corrispondono ai sorgenti. Le impronte dei due componenti modificati sul telefono coincidono con quelle locali; modello, WebView e consegna della schermata di avvio risultano inizializzati, senza indicatori tecnici di errore nel controllo. Le prove di corruzione sono state eseguite su archivi sintetici del Mac: nessuna modifica o corruzione intenzionale dei dati personali sul telefono.

SHA-256 APK: `e6f9c223249b23be36f0a2d4c6495248bf0fbdda6eaa8212af354f6df1c8d6c5`. Il riepilogo finale consolida **342 test distinti superati**; i 17 ricontrolli finali non vengono sommati di nuovo.

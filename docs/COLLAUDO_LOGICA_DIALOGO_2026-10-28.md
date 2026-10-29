# Logica del dialogo: collaudo Android del 28 ottobre 2026

## Comportamento introdotto

ALLMA prepara il turno distinguendo richiesta attuale, scopo, riferimento alla precedente domanda dell’utente, dichiarazioni documentate e testo già prodotto. Gli strumenti esatti e il recupero dei ricordi restano nei percorsi esistenti. Un errore rilevato può avviare una sola revisione mirata del modello, prima di tornare a pubblicare una risposta.

La frase «Ho bloccato una risposta ... Riprova» è stata rimossa dal percorso dei candidati scartati. Un esito irrisolto è uno stato tecnico separato, non una battuta attribuita ad ALLMA; non viene letto dalla voce. Il microfono torna disponibile anche quando la sintesi non deve partire.

Una revisione accettata conserva l’origine di generazione del modello e una ricevuta di controllo, mostrata nella voce Origine. Può ricevere le conferme dell’utente e seguire il normale percorso di apprendimento. La bozza scartata non entra in quel percorso. La sola validazione di formato e attribuzione non dimostra correttezza fattuale.

## Correzioni emerse sul telefono

- Il divieto esplicito di ripetere i punti già detti viene verificato anche quando il nuovo testo aggiunge dettagli. Prima due frasi copiate potevano passare perché seguiva un punto nuovo. La risposta reale della 102582 riprodotta nel controllo aggiornato è ora rifiutata per quelle due frasi.
- Negli approfondimenti il riferimento ricostruito dalla storia entra anche nella richiesta corrente inviata al modello: non rimane soltanto nei metadati del sistema. Il testo originale dell’utente continua a essere conservato senza riscritture.
- La revisione conserva il testo precedente come contesto **già comunicato e da non riproporre**, esplicitamente distinto dalle prove fattuali. Il materiale aggiuntivo della bozza scartata non viene reinserito. Togliere tutto il testo precedente impediva al modello di capire quali punti dovesse evitare.
- Se Decider è assente, una forma esplicita di spiegazione generale non attiva automaticamente ricordi personali. Le richieste personali e i riferimenti ambigui mantengono il recupero: è verificato anche il caso di un oggetto descritto con parole diverse.

## Risultati e valutazione umana

| Build / prova | Risultato osservato |
|---|---|
| 102582, tre scenari naturali | I controlli software accettano i testi, ma la lettura individua errori storici, due frasi ripetute nonostante il divieto, una risposta troncata ed errori nella spiegazione scientifica. Il quarto scenario è rinviato per stato termico Android 2. |
| 102583, copia iniettata e revisione reale | La copia viene intercettata e la revisione parte; chiede però quale sia il soggetto, già presente nella conversazione. Esito utile non raggiunto. |
| 102584, riferimento nella richiesta corrente | Il modello si riferisce alla bussola; riformula comunque la stessa spiegazione e aggiunge imprecisioni. Non è considerato un miglioramento semantico riuscito. |
| 102585, primo tentativo | Stato termico 2 prima della generazione: zero scenari eseguiti, nessun successo dedotto. |
| 102585, dopo raffreddamento, senza reinstallare | Un solo caso completato: copia intercettata, riferimento alla bussola presente, revisione eseguita. Il nuovo testo ripete lo stesso concetto con parole diverse e aggiunge affermazioni non attendibili sulle «borse magnetiche». **Valutazione qualitativa negativa**, anche se i controlli disponibili lo accettano. |

Il caso controllato inietta esplicitamente un primo testo ripetuto con un piccolo dettaglio aggiuntivo; la revisione usa il vero Qwen 3.5 2B Q4_K_M su OpenCL. Questa prova controlla l’attivazione e la qualità del recupero, non misura il tasso naturale di errori del modello.

## Verifiche software e conservazione

3.075 casi desktop distinti superati, 15 saltati. Il totale deduplica le ri-esecuzioni per classe/nome. Dopo i cambiamenti sul riferimento sono stati eseguiti 336 controlli mirati; l’ultima variante del contesto già comunicato ne ha superati 330, oltre alla verifica specifica della provenienza. La suite completa precedente e i casi interessati restano documentati nei rapporti XML.

Gli scenari sul telefono usano archivi temporanei sintetici. La storia personale non è esportata né usata per il benchmark. Modello e backend sono verificati dalle preferenze persistenti e dai metadati del motore; l’etichetta temporanea «Modello locale» nell’interfaccia non viene usata come prova di un cambio del modello. Il tempo di spegnimento viene ripristinato al valore iniziale.

Rimane da valutare separatamente la correttezza dei contenuti e il riconoscimento delle parafrasi che non aggiungono informazioni. Il passaggio di un controllo software non viene presentato come intelligenza perfetta o autonomia generale.

Directory delle evidenze: `/Users/erikahu/ALLMA/analisi/2026-10-28/logica-dialogo`.

## Stato finale

La build **102585** è installata sul telefono. Payload Python e asset controllati corrispondono ai sorgenti. Le preferenze prima/dopo conservano Qwen 3.5 2B Q4_K_M con ragionamento attivo; Qwen rimane su OpenCL e Decider è stato caricato su Hexagon durante la prova. Processo sopravvissuto, nessuna operazione nativa residua, spegnimento dello schermo ripristinato a 60 secondi.

Il caso finale ha richiesto 15,78 secondi complessivi, di cui 8,78 per la revisione. Il primo candidato era iniettato dal test: questi tempi non sono un confronto di velocità con una conversazione normale, né una misura statistica. La batteria è stata letta a 35,6 °C; il telefono era collegato al cavo, quindi non viene stimato il consumo energetico.

I tre controlli DOM aggiuntivi sul telefono sono stati rinviati perché la pagina non risultava visibile e libera. Non sono conteggiati come superati; i 12 controlli unitari del nuovo stato dell’interfaccia e i test del percorso voce sono documentati a parte.

**Conclusione del collaudo:** il circuito di richiesta, controllo, revisione e archivio è operativo e non sostituisce il testo con la vecchia frase «Ho bloccato ... Riprova». La selezione del riferimento è migliorata. La novità semantica e la correttezza dei contenuti **non sono risolte**. I controlli di ALLMA lasciano passare parafrasi e fatti non verificati; il modello può produrli anche al secondo tentativo. Non si attribuisce l’intero problema a un solo componente senza un confronto ulteriore.

Un ulteriore giro casuale dello stesso modello non costituisce una verifica indipendente. Il lavoro successivo deve distinguere il confronto semantico fra affermazioni, le prove disponibili e la verità del contenuto. Le decisioni del controllo devono essere valutate separatamente dalla capacità del modello di generare una risposta utile.

Tutto è salvato localmente; questo intervento non esegue commit, push o pubblicazione di una release.

SHA-256 APK: `b686e21a8c746b9fc571c987e635af8721bf0b05b7639e5aac28d27ca1bfc058`.

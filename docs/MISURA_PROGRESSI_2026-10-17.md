# Progressi ALLMA: confronto misurato del 17 ottobre 2026

**43 condizioni che prima fallivano sono ora superate. Nessuna regressione nel campione confrontato.** La misura riguarda le correzioni dell’ultimo audit, non l’intelligenza generale di ALLMA.

## Risultato del confronto appena eseguito

Ho eseguito la stessa batteria di 47 casi sulla copia dei sorgenti precedente alle correzioni e su quella attuale. Entrambe le esecuzioni usano lo stesso ambiente Mac, rete esterna disabilitata, archivi temporanei e risposte del modello simulate. I file delle prove hanno gli stessi hash nelle due esecuzioni; anche i sorgenti confrontati sono identificati tramite hash.

| Misura | Prima | Dopo | Progresso |
|---|---:|---:|---:|
| Controlli direttamente confrontabili superati | 1/44 | 44/44 | **43 condizioni recuperate** |
| Quota superata su questi 44 casi | 2,27% | 100% | **+97,73 punti percentuali** |
| Fallimenti su questi 44 casi | 43 | 0 | **100% dei fallimenti riprodotti risolto** |
| Casi precedentemente superati che ora falliscono | — | 0 | Nessuna regressione rilevata |
| Altri controlli API | 3 bloccati da dipendenza mancante | 3/3 superati | Funzionamento ora verificabile |
| Intero campione mirato | 1 superato, 44 falliti, 2 errori di preparazione | 47/47 superati | I tre casi bloccati restano separati dal confronto di correttezza |

Un test API fallito e due errori di preparazione dipendevano dall’importazione di `flask_cors`, assente nell’ambiente precedente. Sono tre casi esclusi dal denominatore 44, non tre risposte sbagliate. Il backend attuale non richiede quella dipendenza e supera le tre prove.

**Questo è un campione costruito per riprodurre debolezze note, scritto dopo la loro identificazione.** Il risultato misura la chiusura dei difetti e non è una valutazione indipendente su casi nuovi. Il valore iniziale 2,27% non rappresentava l’affidabilità precedente dell’intero prodotto; il 100% finale non rappresenta l’affidabilità dell’intero prodotto attuale.

## Altri risultati confermati

- **17 difetti D01–D17 corretti**, con prove mirate e limiti descritti nel [rapporto delle correzioni](/Users/erikahu/ALLMA/ALLMA_V4/docs/CORREZIONI_AUDIT_2026-10-17.md).
- Suite complessiva verificata e ricontrolli consolidati: **1.495 superati, 15 saltati, nessun fallimento residuo**. I 47 casi di questo confronto sono gli stessi delle regressioni già conteggiate: non vengono aggiunti di nuovo al totale.
- Batteria operativa Android sulla build **102508: 60/60**. Misura il software sul dispositivo con modello simulato, non le risposte del GGUF.
- La batteria operativa era già 60/60 prima di queste riparazioni: su quella batteria la variazione è **zero punti**. Le nuove riproduzioni hanno individuato difetti che i 60 casi non coprivano.

## Metodo da mantenere per i prossimi confronti

1. **Fissare il punto di partenza.** Conservare sorgenti, modello e quantizzazione, versione dei test, domande, seed e limiti di generazione. Ogni esecuzione deve identificare esattamente cosa è stato provato.
2. **Usare gli stessi casi prima e dopo.** Confrontare ogni caso tramite il suo identificatore. Mostrare quanti passano da errore a successo e quanti regrediscono. I nuovi casi entrano in una versione separata della batteria; non cambiano retroattivamente il denominatore.
3. **Tenere separati i guasti noti e la qualità su casi nuovi.** Le regressioni confermano le correzioni. Domande ulteriori, non usate per costruire le regole o le risposte, misurano la generalizzazione. Per il modello reale servono valutazioni di correttezza, memoria, attribuzione delle esperienze, emozioni e formato, ognuna con il proprio risultato.
4. **Misurare le prestazioni a condizioni confrontabili.** Stesso telefono, modello, budget di risposta, stato iniziale e modalità di alimentazione. Distinguere avvio a freddo e richieste a modello caricato. Registrare attesa iniziale e tempo totale mediani, tempi peggiori, token prodotti e temperatura. Il consumo energetico deve avere un’unità e una lettura effettivamente disponibile; non va dedotto dalla sola temperatura.
5. **Lasciare visibili ciò che manca e gli errori d’ambiente.** Un caso saltato non è riuscito; un import bloccato non è una risposta errata. Niente percentuale unica ottenuta mescolando correttezza, velocità e numero di test.

Per un progresso giornaliero si confrontano due misure complete dello stesso giorno o di giorni diversi sul medesimo campione. Senza una nuova misura la percentuale resta invariata: non cresce per il semplice passare del tempo o per il numero di modifiche al codice.

## Riproducibilità

- [Risultati numerici e transizione di ogni caso](/Users/erikahu/ALLMA/analisi/2026-10-17/progressi/confronto.json).
- [Manifest con hash dei test e dei sorgenti](/Users/erikahu/ALLMA/analisi/2026-10-17/progressi/manifest.json).
- [Esito precedente](/Users/erikahu/ALLMA/analisi/2026-10-17/progressi/prima.xml) e [attuale](/Users/erikahu/ALLMA/analisi/2026-10-17/progressi/dopo.xml).
- [Calcolo ripetibile dei risultati](/Users/erikahu/ALLMA/analisi/2026-10-17/progressi/confronta.py).

Le copie delle prove ammettono, solo nel codice di test, l’assenza dei nuovi nomi delle eccezioni; il vecchio codice non riceve implementazioni sostitutive. In questo modo l’assenza di un contratto viene rilevata nel caso specifico senza interrompere tutta la raccolta. I confronti dello stato usano anche maturità e stabilità già presenti prima, così l’assenza del nuovo contatore non basta a causare un fallimento. Queste variazioni del banco di prova sono identiche per entrambe le versioni e dichiarate nel manifest. I sorgenti applicativi non sono stati modificati in questo intervento di misurazione.

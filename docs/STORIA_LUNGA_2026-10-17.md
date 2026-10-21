# Storie lunghe, continuità e indice leggero — 17 ottobre 2026

Questo intervento mette alla prova storie più lunghe e combinazioni diverse da quelle della precedente batteria. Corregge cinque famiglie di problemi: finestra della cronologia, interferenze fra codici, richieste ripetute che nascondono fonti, costo dell’indice e revoche nel percorso alternativo. Le prove restano sintetiche: non equivalgono a mesi di utilizzo reale o a una misura della qualità del GGUF.

## Cambiamenti verificati

| Problema | Comportamento corretto |
|---|---|
| Una lettura con limite prendeva i primi messaggi della chat. | Restituisce gli ultimi messaggi, mantenendoli in ordine cronologico. Filtra le date prima del limite; rifiuta limiti negativi, booleani o non interi. |
| Una frase incerta su un codice di accesso impediva di ricordare un codice di prova già dichiarato. | L’incertezza riguarda la categoria nominata. Un’incertezza generica continua a impedire una scelta arbitraria. Parlare di programmazione non diventa una revoca di un identificatore. |
| Molte richieste di ricordo, formulate diversamente, occupavano i primi risultati di ricerca. | Le richieste pure di richiamo riconosciute vengono filtrate prima di limitare i risultati. Le dichiarazioni miste a domande restano disponibili, così come le domande precedenti quando sono proprio ciò che si vuole richiamare. La storia non viene cancellata. |
| La cache numerica occupava spazio per ogni coppia documento/parola. Nuovi inserimenti copiavano in SQLite anche vettori densi e l’intero vocabolario. | Vettori sparsi e liste inverse conservano solo i termini presenti. I nuovi record salvano testi e metadati autorevoli, senza riscrivere copie dense derivate. |
| Il percorso alternativo poteva riproporre record revocati o superati. | Le revoche vengono rispettate anche quando non viene utilizzato il backend vettoriale. |

Esempio: una dichiarazione «Il codice di prova è NUOVO_007», seguita da 350 messaggi e da un dubbio sul codice di accesso, viene ora richiamata dal core come `NUOVO_007`, senza usare il modello. I dubbi sullo stesso codice continuano a richiedere chiarimento.

La crescita emotiva è stata verificata anche con 70 aggiornamenti in attesa: il recupero li completa in tre giri limitati, con 38, 6 e infine 0 residui. Ripetere il recupero non aumenta nuovamente le osservazioni.

## Confronto dei nuovi casi

Prima di modificare il codice sono stati definiti 34 controlli su questi comportamenti. **10 passavano e 24 fallivano; dopo le correzioni passano tutti e 34.** Sono casi di sviluppo che diventano regressioni, non un campione indipendente per stimare l’affidabilità generale.

Un primo test numerico confrontava erroneamente il punteggio ibrido con il solo coseno lessicale. L’errore del test è stato corretto prima di modificare la produzione e non viene contato come difetto di ALLMA. Gli artefatti preliminari sono conservati separatamente. Altri sei controlli, aggiunti durante l’integrazione, portano a 40 i nuovi test; non vengono mescolati al confronto iniziale.

[Piano](/Users/erikahu/ALLMA/analisi/2026-10-17/storia-lunga/piano.json), [confronto dei 34 casi](/Users/erikahu/ALLMA/analisi/2026-10-17/storia-lunga/new-cases-comparison.json), [prove di integrazione](/Users/erikahu/ALLMA/analisi/2026-10-17/storia-lunga/integrazione-finale.xml).

## Misure dell’indice

Stesso corpus sintetico di 3.000 documenti con 9.001 termini, stesse richieste, processi separati sul Mac. Una sola esecuzione per versione, con altre verifiche attive; i tempi sono indicativi.

| Misura | Prima | Dopo | Riduzione sul campione |
|---|---:|---:|---:|
| Ricerca con indice caldo, mediana di 30 richieste | 12,57 ms | 1,10 ms | 91,3% |
| Buffer numerici della cache, inclusi i nuovi indici inversi | 108,01 MB | 0,24 MB | 99,78% |
| Inserimento dei 3.000 documenti | 7,69 s | 1,36 s | 82,3% |
| File SQLite nuovo, dopo checkpoint | 57,16 MB | 0,39 MB | 99,31% |

La ricerca fredda con ricostruzione passa da 144,42 a 124,58 ms sullo stesso corpus. La riduzione della cache numerica non rappresenta quella di tutta ALLMA: esclude oggetti Python, vocabolario, moduli e modello linguistico. La misura del file riguarda un archivio appena creato; gli archivi esistenti conservano i vecchi blob e non vengono compattati automaticamente. Nessuna percentuale di autonomia o temperatura deriva da queste prove.

Un confronto separato con il codice precedente, 120 documenti e 32 richieste lessicali generate con seed fissato, mantiene **lo stesso ordinamento in 32/32 richieste**; la differenza massima dei punteggi è 5,96 × 10⁻⁸. Il nuovo indice conserva il significato del recupero lessicale, senza introdurre un altro modello.

[Misure prima](/Users/erikahu/ALLMA/analisi/2026-10-17/storia-lunga/index-before.json), [dopo](/Users/erikahu/ALLMA/analisi/2026-10-17/storia-lunga/index-after.json), [confronto degli ordinamenti](/Users/erikahu/ALLMA/analisi/2026-10-17/storia-lunga/cosine-comparison.json).

## Verifica e build

La nuova voce in Diagnostica è **«Storia lunga · 24 scenari»**. Usa archivi temporanei e codice di produzione, senza modificare i ricordi personali o misurare risposte del GGUF. Le batterie precedenti rimangono separate, con il loro numero di casi invariato. Il programma di esecuzione temporanea viene condiviso fra le due batterie di memoria.

- 130 regressioni iniziali superate.
- 241 controlli di integrazione superati dopo le correzioni finali.
- 46 controlli sulla nuova diagnostica e sulla batteria precedente superati.
- Suite generale completata in copia isolata: **1.595 test distinti superati, 15 saltati, zero fallimenti**, su 1.610 raccolti. I sorgenti e gli asset corrispondono ancora alla copia congelata. I casi saltati non vengono contati come successi.
- Batteria standard invariata: **60/60 scenari sul Mac**.
- Sul Samsung SM-S938B, build 102510: **24/24 scenari completati**, in 8,13 secondi. Piano e programma di prova incorporati corrispondono ai sorgenti verificati. [Riepilogo Android](/Users/erikahu/ALLMA/analisi/2026-10-17/storia-lunga/android-summary-102510.json).
- [Riepilogo complessivo verificabile](/Users/erikahu/ALLMA/analisi/2026-10-17/storia-lunga/validation-summary.json).

La build **102510**, versione 0.9.0.0, è compilata, verificata e installata. Il pacchetto corrisponde al payload dei sorgenti e conserva runtime ARM64 e supporto Qwen 3.5. SHA-256: `5d12100d538b525ec683707bfe973bd940aa5270a4a501a8aef6f558f349b46d`.

[Verifica APK](/Users/erikahu/ALLMA/analisi/2026-10-17/storia-lunga/apk-check-102510.json), [APK](/Users/erikahu/ALLMA/ALLMA_V4/bin/allma_prime-0.9.0.0-arm64-v8a-debug.apk).

## Limiti ancora aperti

La ricerca concettuale rimane basata su un vocabolario delimitato. I nuovi filtri comprendono forme chiuse di domande locative e richieste di codici, non ogni possibile richiesta naturale. Le correzioni riconosciute dei fatti personali hanno il proprio percorso; non è ancora presente una gestione universale di qualunque fatto espresso liberamente.

L’indice cresce con i termini effettivamente presenti, ma viene ancora ricostruito dopo modifiche: archivi molto grandi e scritture frequenti richiedono ulteriori misure e possibili aggiornamenti incrementali. Le storie simulate non dimostrano stabilità per mesi, né eliminano gli errori del modello nella formulazione delle risposte. Rimangono separati i collaudi lunghi di voce, cambi di modello, temperatura e batteria.

Le modifiche sono salvate localmente; nessun nuovo commit, push o rilascio GitHub è stato eseguito in questo intervento.

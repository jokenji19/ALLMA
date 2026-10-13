# Analisi del benchmark Android — 13 ottobre 2026

Profilo rapido, sei casi nuovi N1–N6, sessione a8865850d21b4c2bbaf8a3cb1bde27c1. Report originali conservati; questa è una valutazione dell’assistente, non di un revisore indipendente. Nessuna risposta riscritta per migliorarne il risultato.

| Caso | Tempo | Valutazione |
|---|---:|---|
| N1 | 10.54 s | Conclusione logica No corretta; vincolo solo sì/no violato e pesci marini citati erroneamente come mammiferi. |
| N2 | 16.12 s | 42: calcolo corretto e formato rispettato. |
| N3 | 18.66 s | JSON corretto, totale 8 e booleano true; formato rispettato. |
| N4 | 22.70 s | Riconoscimento di joy+fear corretto nei metadati; testo in prima persona attribuisce ad ALLMA il lavoro e la preoccupazione dell’utente. Due frasi rispettate, ma supporto poco personale e generico. |
| N5 | 28.36 s | Termine glii inesistente in questa spiegazione; ruolo delle branchie espresso in modo impreciso, cause ulteriori non sufficientemente giustificate. Non considerata una spiegazione scientifica affidabile. |
| N6 | 19.29 s | Non inventa il colore; riconosce l’assenza di dati ma la spiegazione sul non accedere a esperienze individuali è fuorviante rispetto alla memoria di ALLMA e aggiunge dettagli inutili. |

Media 19.28 s, contro 14.74 s della prima prova rapida: +30.8% di tempo in questa esecuzione. Mediana 18.98 s. Due prove non dimostrano una regressione stabile. Dataset e semi uguali, ma carico, temperatura iniziale e cache diversi; non è un confronto controllato.
Token complessivi quasi uguali: 814 → 801. Attesa media del primo token generato: 5.50 → 9.73 s. Il primo token è spesso del ragionamento, non della risposta visibile. Gran parte della differenza temporale è prima del primo token; la causa non è dimostrata dai dati disponibili.
Il calcolo N2 genera 64 token di ragionamento e 2 di risposta; un percorso di budget più proporzionato può aiutare, da provare senza eliminare il ragionamento richiesto dall’utente. Il seed fisso non ha prodotto output identici, coerentemente con la mancanza di determinismo garantito fra stati di esecuzione.
Batteria 37.7 → 39.3 °C (+1.6 °C), telefono in carica. Letture CPU durante le richieste fino a 69.1 °C; sono campioni, non un picco continuo verificato. Nessuna stima di consumo energetico. Il livello batteria nel manifest è mancante: _conditions cerca battery_level, mentre MetabolicState espone energy_level; da correggere nella telemetria.
Esiti chiusi: N2 e N3 passano, N1 fallisce. Il successo automatico di N4 verifica solo il riconoscimento delle famiglie emotive nei metadati, non il testo di conforto. N5/N6 hanno criteri aperti da valutare. Non si ricava una percentuale generale di intelligenza o qualità da questi sei casi.

Interruzione e stabilità: report della prova interrotta con cancelled=true, conferma dell’utente, stesso PID 26221 rimasto attivo. Nuova esecuzione completata senza nuova JavaException di chiusura nelle finestre di log osservate. Il crash di thread della WebView risulta risolto nel collaudo nativo.

Priorità emerse: contratto di formato per risposte chiuse senza nascondere errori di contenuto; separazione utente/ALLMA nella generazione; correttezza scientifica e gestione dell’incertezza; misura dell’attesa del primo token e budget per richieste brevi. Il benchmark misura la pipeline: non consente di attribuire tutti gli errori al solo GGUF o di separare automaticamente limiti del modello, prompt e budget.

Nessuna modifica applicativa eseguita durante questa analisi. Risultati e valutazioni salvati localmente.

# Collaudo esteso — 6 ottobre 2026

## Esito automatico finale

- **530 test superati, 15 saltati**, suite completa sullo stato finale dei sorgenti; i test saltati non sono considerati verificati.
- **23 controlli browser passati**, comprendenti una raffica di circa 10.000 caratteri consegnati in singoli frammenti: nessuna perdita, massimo due rendering nel burst, nessun rendering aggiuntivo durante il silenzio, gestione del finale e della coda dei dettagli al cambio chat.
- Test aggiuntivi con 40 segmentazioni casuali di testo Unicode, 80 combinazioni di segmentazioni/affermazioni personali, stati JSON malformati e scritture concorrenti delle preferenze per 80 utenti. Questi casi sono inclusi nei 530, non sommati una seconda volta.
- APK verificata: payload identico ai sorgenti, librerie arm64-v8a, KivyMD 1.2.0. SHA256 `65dd6a680a04f292271536f9dae96db80223f8521286bc2beebf3e7c9938e297`.

## Difetti trovati e corretti

1. Uno spazio iniziale o un a capo tra «Mi» e «chiamo», o tra «Ho» e «visitato», poteva aggirare la verifica della preview. La verifica normalizza ora gli spazi, e un semplice a capo non basta a liberare un segmento incompleto. La formattazione originale del testo resta conservata. Anche il controllo finale normalizza gli spazi.
2. Un `mode` salvato come lista/oggetto produceva un errore di tipo durante il caricamento delle preferenze. Viene scartato; rimane la modalità predefinita.
3. Prefissi combinati, come «ALLMA, da ora in poi…» e «Per favore, ALLMA,…», non venivano riconosciuti. Ora vengono rimossi in sequenza prima di analizzare il comando completo.
4. Le istanze del core condividevano lo stesso singleton dei momenti emotivi: il collaudo completo ha rilevato una riflessione sui martedì e sulla tristezza ereditata da altre prove. Il core ora possiede uno storico separato; le aggiunte emotive successive alla generazione passano anche i controlli sulle affermazioni personali.
5. I metadati di generazione erano restituiti dal core ma esclusi dai messaggi persistenti. Ora vengono salvati: modalità, motivo della scelta, tempi e arresto sono disponibili dopo il riavvio. Il nuovo salvataggio è coperto da un test d'integrazione.

Le prime prove più severe avevano 64 fallimenti: sono varianti di confini dei frammenti e stato malformato, non 64 difetti indipendenti. Sono state mantenute come regressioni, correggendo il codice. Un successivo fallimento della suite completa ha fatto emergere la condivisione dello storico emotivo. Gli esiti iniziali sono conservati insieme a quelli finali.

## Prove sul Samsung collegato

Prove eseguite attraverso la vera UI di ALLMA, con il GGUF del telefono; nessuna risposta sostitutiva predisposta per le domande di prova.

| Prova | Esito | Generazione LLM | CPU rilevata |
|---|---|---:|---:|
| Come ti chiami? | «Mi chiamo ALLMA.»; percorso identitario, nessuna generazione | Non usata | Non misurata per questo turno |
| Preferisco le risposte progressive | Preferenza salvata per user_default, senza LLM | Non usata | Non misurata per questo turno |
| Bicicletta in tre frasi | Preview visibile prima del finale; termini e spiegazione meccanica non affidabili | 17,23 s, 174 token, stop | 42,0 → 57,9 °C |
| 17 × 8, invio completo | Calcolo corretto: 80 + 56 = 136; nessuna risposta visibile nel campione a 8 s, risposta finale nel campione successivo | 10,44 s, 98 token, stop | 45,5 → 66,4 °C |
| Storia delle biciclette | Limite raggiunto; risposta incompleta e terminologia debole | 18,46 s, 256 token, length | 42,8 → 67,5 °C |
| Differenze tra mezzi, interruzione a 3 s | Richiesta annullata e UI tornata disponibile; nessuna risposta assistente salvata per quel messaggio | Interrotta | Non confrontabile con un completamento |

Il primo tentativo di annullamento della storia delle biciclette era arrivato dopo il completamento: non viene contato come prova riuscita di cancellazione. Il tentativo successivo ha premuto Interrompi prima del primo risultato. La UI mostrava ancora «Interruzione…» nel campione a circa 8,8 secondi dal comando ed era disponibile nel controllo seguente. Quindi la cancellazione funziona, ma non è istantanea durante il prefill nativo. Non è stata ricavata una latenza esatta da questi campioni.

Nella prova bicicletta, la temperatura batteria campionata via Android è passata da 37,0 a 37,1 °C in 24 secondi; il monitor dell'app ha riportato 37,3 °C all'inizio e alla fine delle generazioni. Differenti istanti/fonti di campionamento non vanno confusi con la temperatura CPU. Al controllo successivo la batteria era 38,1 °C. Il telefono era collegato USB e il livello è passato da 99 a 98: non è una misura controllata di autonomia, consumo dell'app o risparmio rispetto alla vecchia build.

Le prove di generazione e annullamento precedono l'installazione finale delle correzioni appena emerse. La versione finale è stata compilata e aggiornata con installazione sostitutiva, conservando i dati. La modalità automatica iniziale è stata ripristinata prima dell'aggiornamento.

## Audit statico e limiti residui

189 moduli Python analizzati, nessun errore di sintassi. 91 sono raggiungibili dalle radici principali attraverso import statici; il numero non misura quanti moduli siano inutilizzati, perché esclude import dinamici e altri entry point. Restano sette basi di import mancanti in due demo e nel vecchio `vocabulary.py`: non sono state confuse con un errore di avvio della pipeline Android attuale.

La qualità generale del GGUF resta variabile: un calcolo riuscito non dimostra competenza generale e la spiegazione della bicicletta mostra errori concreti. Servono ulteriori confronti di qualità su domande nuove, del budget di ragionamento e del modello; non inserire risposte precostituite alle domande del benchmark. Anche la classificazione della richiesta lunga come SIMPLE e la troncatura a 256 token richiedono valutazione.

Cancellazione durante il prefill, riscaldamento CPU e consumo prolungato restano da ottimizzare e misurare. Non effettuato collaudo vocale umano in questa sessione: i test dei motori voce sono automatici. Non effettuato un ciclo onirico notturno prolungato. Questi limiti non sono coperti dalla percentuale di test automatici passati.

Log, screenshot, metadati e verifica APK: `analisi/2026-10-06/collaudo-esteso`.

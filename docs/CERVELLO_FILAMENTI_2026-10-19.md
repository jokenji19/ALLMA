# Cervello anatomico a filamenti — 19 ottobre 2026

## Richiesta e risultato

Sostituire la sagoma arrotondata della 102524 con una forma chiaramente riconoscibile come cervello umano, nello stile delle due immagini fornite: trama trasparente, filamenti chiari sulle pieghe, piccoli punti luminosi e sfondo scuro.

La nuova geometria deriva dalle superfici corticali fsaverage5 distribuite da Nilearn: due emisferi con solchi effettivi, ridotti sulla sfera di registrazione per evitare di saldare insieme le due pareti di un solco. La conversione mantiene una scala uniforme. Dai dati di profondità dei solchi si estraggono filamenti curvi continui. Cerebellum e tronco completano la sagoma con strutture a filo create per questa visualizzazione; sono approssimazioni, non geometrie cliniche.

Vista iniziale di tre quarti; rotazione completa, zoom, selezione dei moduli e percorsi osservati restano disponibili. La rete anatomica resta una rappresentazione visiva: la posizione dei moduli è simbolica, non una localizzazione biologica. L’attività evidenziata viene ancora dagli eventi della pipeline ALLMA, senza chiamate aggiuntive al modello o attività inventata.

## Dimensioni e prestazioni

6.640 vertici strutturali, 17.388 connessioni, 195 filamenti continui. Le risorse della geometria sono locali e inferiori a 300 kB; nessun download durante l’uso e nessuna libreria scientifica aggiunta al runtime Android. `tools/build_brain_geometry.py` genera la risorsa a partire dai GIFTI di origine; hash e revisione della fonte sono conservati nel dossier.

Il disegno anatomico viene riutilizzato quando camera ed evidenziazione non cambiano. Gli impulsi viaggiano su un livello separato. Il disegno è raggruppato per ridurre le chiamate grafiche; restano il limite di frequenza, la pausa, la sospensione in background e la pulizia alla chiusura. Non è stata misurata una riduzione della temperatura o della batteria sul telefono.

## Verifiche

- Geometria finita, collegamenti validi, proiezione a 360°, riutilizzo del disegno, ridimensionamento e rilascio: superati.
- Contratto eventi e ciclo di vita della pagina: superati.
- 14 test Python su risorse, navigazione e attività: superati.
- 23 verifiche browser della pagina di produzione con dati sintetici: superate.
- Anteprima mobile reale del browser salvata nel dossier; non è uno screenshot del telefono.
- Build 102525 compilata, contenuto incorporato verificato, installata e avviata sul telefono. Tutte e sette le risorse controllate (geometria, disegno, pagina, stile, licenza e bridge Android) corrispondono ai sorgenti. Nessuno degli errori tecnici cercati è emerso nel campione recente dei log. La valutazione estetica sul dispositivo resta all’utente.

La somiglianza estetica alle immagini rimane da valutare con l’utente; non è una riproduzione identica delle immagini.

## Fonte e licenza

Fonte: [Nilearn fsaverage5](https://github.com/nilearn/nilearn/tree/e9c2196f09a4a12cc2e74e7473f67647e7fe5a26/nilearn/datasets/data/fsaverage5), template corticale FreeSurfer fsaverage. Licenza Nilearn BSD-3-Clause, attribuzione e testo completo in `assets/web/licenses/brain-geometry.txt`, incluso nel pacchetto. Il modello di BrainBrowser scaricato durante l’esplorazione non è stato usato né incluso nell’app.

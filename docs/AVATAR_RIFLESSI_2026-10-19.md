# Avatar ALLMA: contorni di luce e riflessi

Build Android: **102520**, versione 0.9.0.0.

## Risultato visivo

Il nuovo trattamento riprende lo stile della seconda immagine di riferimento: fondo nero, interno del volto in ombra, contorni bianchi e argento, filamenti sottili e pochi bagliori diagonali. Le frange leggermente prismatiche compaiono soltanto sui raggi dei riflessi; la superficie del viso non viene colorata di blu.

Restano il busto infantile di circa sei mesi, la scelta femminile/maschile/neutra, l’impronta persistente, la rotazione completa, la pausa e l’accesso al cervello esistente. Il riferimento orienta la luce e le particelle, non trasforma l’avatar in un adulto.

## Realizzazione

- 100.000 particelle della geometria anatomica esistente; superficie usata esclusivamente per la profondità, mai come pelle dipinta.
- Collegamenti sottili e fino a 96 brevi riccioli luminosi attorno alla testa, ancorati alla stessa geometria e ruotati insieme al volto.
- Fino a 144 punti di riflesso con variazione lenta dell’intensità. Le ancore rivolte verso il retro non producono bagliori davanti al volto.
- Cinque buffer statici e quattro passaggi grafici: profondità, filamenti, particelle e riflessi. Nessun caricamento dei buffer a ogni fotogramma.
- Movimento lento delle particelle e segnali dei moduli esistenti conservati. Nessuna richiesta aggiuntiva al modello linguistico.
- Alternativa Canvas 2D con circa 6.250 punti, contorni chiari e massimo dieci piccoli riflessi. Pausa, chiusura e sospensione in background mantengono il comportamento esistente.
- Uniforme condivisa `uPoints` con precisione coerente nei due shader; ripristino dello stato di profondità dopo il passaggio dei riflessi.

## Verifiche

41 test Python superati per presenza, risorse web, navigazione interna e attività del cervello. Superati anche i controlli Node di geometria, renderer e vista del cervello.

Nel browser reale sono stati verificati il salvataggio della scelta, le tre presentazioni, gli errori di salvataggio, la rotazione, lo zoom, il tasto Indietro, la pausa, la sospensione, la riapertura e il renderer Canvas reale. Nessun errore WebGL nel controllo. Superate anche le prove della navigazione e della chat con dati sintetici.

L’APK è stata verificata: contenuto incorporato corrispondente ai sorgenti, ARM64 e dipendenze native previste. Installazione con aggiornamento e avvio riusciti sul Samsung collegato; versione installata 102520 e nessuno degli errori tecnici cercati nei log recenti.

Le anteprime delle tre varianti e del profilo sono in `analisi/2026-10-19/avatar-riflessi` nella cartella superiore del progetto. La verifica visiva finale sul display Android rimane affidata al riscontro dell’utente. I tempi CPU raccolti nel browser non misurano costo GPU, consumo di batteria o prestazioni Android.

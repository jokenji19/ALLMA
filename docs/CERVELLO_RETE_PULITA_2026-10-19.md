# Cervello di ALLMA: rete pulita — 19 ottobre 2026

Richiesta: tornare a una visualizzazione più pulita, con i collegamenti chiaramente visibili.

## Modifica

Eliminata la superficie grigia piena. Il cervello è rappresentato da una rete tridimensionale trasparente: due emisferi, cervelletto e accenno del tronco, composti da 584 punti e 781 connessioni locali. La forma è simbolica; non rappresenta neuroni biologici né una localizzazione neuroscientifica dei moduli.

I passaggi realmente osservati dalla pipeline vengono sovrapposti con linee più chiare, frecce e impulsi. Restano visibili anche dopo il termine del turno. La selezione di un modulo evidenzia i suoi collegamenti; una legenda distingue struttura simbolica e percorso osservato.

Conservati accesso diretto dal titolo ALLMA, rotazione a 360°, zoom, centratura, selezione dei 24 sistemi, riproduzione del percorso, domanda inviata alla chat, pausa e ritorno. Nessun caricamento del vecchio avatar o richiesta di genere/età.

Il disegno usa Canvas 2D per proiettare la rete 3D: nessuna dipendenza da WebGL, geometria riutilizzata, massimo 24 fotogrammi al secondo, rendering sospeso in pausa/background/chiusura. Non è stata misurata una variazione di batteria o temperatura sul dispositivo.

## Verifica

- Controlli della geometria e del ciclo di vita JavaScript: superati.
- 14 test Python su risorse web, navigazione interna e attività cognitiva: superati.
- 22 controlli browser su interfaccia reale con dati sintetici: superati, inclusi disegno effettivo, collegamenti osservati, rotazione, zoom, pausa, background e riapertura.
- Anteprima mobile ispezionata e salvata in `anteprima-mobile.png`; non è uno screenshot del telefono.
- APK 102524 compilata; verifica del contenuto incorporato corrispondente ai sorgenti: superata.
- Build 102524 installata e avviata su Android dopo il ricollegamento USB. Verificati gli hash delle quattro risorse grafiche installate: tutti corrispondono ai sorgenti. Nessuno degli errori tecnici di avvio cercati è emerso nel campione recente dei log. La verifica estetica sul dispositivo resta all’utente.

Le prove tecniche non sostituiscono il giudizio estetico dell’utente. Non sono stati modificati né letti ricordi o conversazioni personali per queste prove.

## Artefatti

`analisi/2026-10-19/cervello-rete-pulita/`: risultati, log di compilazione, verifica APK e anteprima. `esito-finale.json` registra hash delle risorse e stato d’installazione.

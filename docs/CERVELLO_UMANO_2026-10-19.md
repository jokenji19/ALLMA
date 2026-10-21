# Cervello umano 3D, senza ritratto iniziale

Build **102523**, versione Android 0.9.0.0.

Toccando ALLMA si apre direttamente il cervello. La schermata non presenta più
il busto, la scelta dell’aspetto o dell’età e non carica le librerie del ritratto.
La raccolta degli stati dei moduli non crea e non legge più l’identità visiva.
Gli archivi precedenti rimangono conservati.

## Forma e attività

La nuova illustrazione procedurale rappresenta due emisferi con una fessura
mediana, pieghe corticali e solchi, due porzioni del cervelletto e il tronco.
Non deriva da una scansione medica: è una forma umana artistica. La geometria
ha 18.480 vertici e 36.224 triangoli, compatibili con indici WebGL1 a 16 bit.

La superficie ha una luce morbida, contorni azzurri e violetto e una trama
puntiforme. I sistemi osservabili sono sovrapposti alla forma e condividono
la stessa camera. La loro posizione è simbolica, come specificato nella UI.
Selezionare un sistema ne evidenzia la zona; l’attività in esecuzione produce
un’evidenziazione distinta. I collegamenti e gli impulsi provengono dagli eventi
osservati della pipeline; non vengono inventati per decorare il cervello.

Sono conservati tutti i 24 sistemi, dettagli e stati, informazioni sulla
personalità, cronologia del turno, riproduzione del percorso e invio di domande
alla chat. La camera ruota a 360°, permette di avvicinare e ricentrare la vista.
Un solo Indietro torna alla chat.

## Risorse e ciclo di vita

La superficie usa due buffer statici e due passaggi grafici. Il disegno dei
collegamenti resta sul livello Canvas sovrapposto. Non ci sono chiamate al
modello o download aggiuntivi. Il rendering continuo è limitato ai turni in
elaborazione o agli impulsi da mostrare; a riposo vengono ridisegnati solo gli
aggiornamenti e le azioni dell’utente. Gli aggiornamenti del motore onirico
mantengono il proprio stato osservabile senza una rotazione decorativa continua.

Pausa e background fermano i fotogrammi; il tempo trascorso in background non
viene integrato al ritorno. Chiudere libera i buffer GPU, interrompe il
monitoraggio della vista e le animazioni e cancella la riproduzione pendente. Il renderer gestisce perdita
e ripristino del contesto. Senza WebGL è disponibile una forma a punti Canvas.

## Verifiche

Controlli Node su geometria, normali, regioni anatomiche, indici, buffer statici,
contesto e dismissione; test della vista su aggiornamenti, testo sicuro,
cronologia, invio, pausa e riapertura. Il collaudo nel browser verifica apertura
senza avatar, rendering WebGL senza errori, 24 sistemi, rotazione, zoom,
selezione, riproduzione, background, Indietro e alternativa Canvas reale.
Risultati e anteprime con dati sintetici sono nella cartella superiore
`analisi/2026-10-19/cervello-umano`.

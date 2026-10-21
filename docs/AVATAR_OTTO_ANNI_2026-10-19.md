# Avatar di circa otto anni e capigliature 3D

Build Android **102522**, versione 0.9.0.0.

## Aspetto

Il busto passa alle proporzioni artistiche di circa otto anni. Il generatore
usa i target CC0 MakeHuman `baby` e `child` con pesi 2/9 e 7/9, anziché i pesi
della precedente versione di tre anni. Viso e parte inferiore della testa
risultano più sviluppati; la linea degli occhi è ricentrata per conservare
le espressioni del renderer. La zona della bocca è aggiornata alla nuova forma.

Le tre rappresentazioni ora hanno capigliature effettivamente diverse:

- **Maschile:** corta e folta, con 28.800 particelle aggiuntive.
- **Femminile:** lunga, fino alla zona delle spalle, con 38.400 particelle.
- **Neutra:** taglio intermedio, con 28.800 particelle.

La capigliatura segue una mappa ricavata dalla superficie della testa personale.
Le curve, gli strati e il volume sono tridimensionali e deterministici rispetto
all’impronta salvata. La versione lunga mantiene libera la zona del viso e
scende lungo i lati e dietro la testa. Un piccolo sfalsamento dei campioni
evita file di punti allineate orizzontalmente lungo le ciocche.

## Rendering e persistenza

Restano lo stile di luce bianca e argento, i riflessi, il movimento lento, la
rotazione completa, la pausa e lo zoom nel cervello. La luce centrale è
leggermente aumentata per rendere più leggibili i tratti e la trama dei capelli.

Le 100.000 particelle anatomiche sono conservate, con un totale massimo di
138.400 punti. I capelli condividono il passaggio grafico delle particelle,
senza nuove chiamate al modello linguistico o caricamenti di rete. Le superfici
di profondità restano invisibili e nascondono le parti posteriori. I buffer
rimangono cinque e vengono caricati solo alla creazione o variazione del busto.
L’alternativa Canvas usa circa 7.330 punti complessivi e mantiene la capigliatura.

Il ritaglio del busto è applicato anche nelle coordinate finali, eliminando
parte del torso che sarebbe rimasta fuori dalla vista con la nuova età.

Il dato di presenza è ora `visual_age_months: 96`, stadio `child`. Non viene
aggiunto l’invecchiamento automatico. Impronta, scelta dell’aspetto, ricordi e
stato di apprendimento restano quelli già salvati.

## Controlli

Le prove della geometria verificano anche volume laterale e posteriore dei
capelli, differenze di lunghezza fra gli aspetti, densità locale delle
palpebre, determinismo, indici della profondità e limiti della variante Canvas.
Il controllo del renderer verifica caricamenti statici, pausa, recupero del
contesto e conteggio effettivo dei punti. I risultati e le anteprime con dati
sintetici sono in `analisi/2026-10-19/avatar-otto-anni`, nella cartella superiore
del progetto. I costi GPU e di batteria non sono misurati dalle prove CPU.

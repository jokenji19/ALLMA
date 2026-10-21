# Ritratto a particelle bianche · build 102519

## Richiesta e risultato

La build precedente funzionava ma l’effetto di pelle blu e gli occhi vetrosi
rendevano il bambino inquietante. Questa revisione segue il riferimento visivo
dell’utente: fondo nero e moltissimi punti bianchi vicini che disegnano il volto
in tre dimensioni, senza mostrare una superficie dipinta.

Il busto conserva proporzioni infantili, approssimativamente sei mesi, scelta
femminile/maschile/neutra, impronta personale, crescita da evidenze consolidate,
rotazione completa, zoom sul cervello e navigazione esistente. Non modifica
identità nominale, ricordi, preferenze o genere scelto. Le sfumature delle tre
presentazioni restano lievi, coerentemente con una rappresentazione infantile.

## Geometria e resa

- 100.000 punti distinti, rispetto ai 24.000 della 102518.
- Una suddivisione Catmull–Clark offline leviga la base anatomica CC0.
- Cranio superiore meno allungato e guance armonizzate.
- Palpebre curve chiuse, ricostruite e raccordate alla pelle, senza sfere,
  iridi o pupille. Pieghe valorizzate dalla luce locale dei singoli punti.
- Campionamento CDF stratificato evita sia addensamenti in righe sia zone
  prive di punti su piccoli triangoli, in particolare nelle palpebre.
- 22.047 vertici e 38.256 triangoli usati esclusivamente per la profondità:
  nessun triangolo colora il viso. Nascondono i punti sul lato opposto.
- 2.400 sottili collegamenti, bagliore morbido dei punti e pochi punti esterni
  in movimento, senza cambiare il colore del volto in blu o viola.

Fonte dei dati e licenze: `assets/web/AVATAR_ASSET_LICENSE.txt`.
La forma e l’età sono una rappresentazione artistica; il risultato non è una
scansione fotografica e non riproduce il volto dell’utente.

## Animazione e risorse

Movimento lento dei punti lungo la superficie, piccoli spostamenti normali e
respirazione sono calcolati nello shader. Memoria, emozioni/coalescenza e modello
modulano lievemente la luce e il movimento solo per nuovi eventi osservati.
L’osservazione non chiama il modello linguistico e non genera apprendimenti.

Il buffer denso è caricato una volta per impronta/forma/aspetto. Espressioni e
fotogrammi non trasferiscono nuovamente 100.000 posizioni dal processore alla
GPU. Rendering: 16 fps a riposo, 20 durante attività, 8 nel ripiego Canvas da
6.250 punti; DPR limitato a 1,5. Chiusura, background e modifica dell’aspetto
sospendono il ciclo. Restano attivi preferenza movimento ridotto e Pausa.

Corrette due regressioni: Pausa non azzera più bruscamente respirazione e posa;
gli eventi conservati in una vecchia istantanea non riattivano moduli già
osservati. Una risposta nativa tardiva non riavvia il rendering in background.

L’asset derivato pesa 2.109.880 byte. Qualità e costo grafico aumentano rispetto
alla versione precedente; non sono stati misurati consumi di batteria o GPU
sul telefono. Non viene aggiunto un altro modello AI.

## Verifiche

I risultati completi, le immagini e gli hash sono in:
`/Users/erikahu/ALLMA/analisi/2026-10-19/avatar-particelle/`.

- 136 test Python passati: risorse offline, scelta, persistenza, profili,
  backup, navigazione, memoria e crescita esistenti.
- Tre verifiche Node: geometria e densità locale delle palpebre, pipeline GPU
  simulata, cache, recupero del contesto, pausa e ciclo dell’osservatorio.
- Browser reale: compilazione WebGL e confronto visivo delle tre presentazioni
  dalla vista frontale, a tre quarti, di profilo e sul retro.
- Due catture della galleria durante il movimento hanno 198.949 pixel diversi
  oltre soglia 5/255 nel ritaglio di verifica; due in Pausa sono identiche.
  È una verifica di animazione/congelamento, non una misura di bellezza.

La valutazione estetica dell’utente resta distinta dai controlli funzionali.

## Esito del collaudo e installazione

Browser: 38 avatar, 52 navigation, 70 chat; tutti passati.
Il test Indietro ora attende il completamento di popstate, senza assumere
un ritardo fisso di 60 ms. Controllato anche dopo la chiusura del ritratto.
APK 102519 installata conservando i dati; versione confermata da Android,
processo attivo e nessun errore tecnico d’avvio nei log filtrati. La conferma
estetica sul telefono è stata chiesta all’utente e resta separata dai test.

SHA256 APK: `3688821d457b7e769b4866826d022bd92a8a5ecf339635f9a9aef9d7554a1d9f`.

# Avatar infantile e scelta iniziale · build 102518

## Comportamento

Toccando ALLMA in alto, prima del primo ritratto si sceglie esplicitamente fra
Femminile, Maschile e Neutra. Nessuna opzione è preselezionata. Il ritratto si
inizializza soltanto dopo la conferma del salvataggio nativo. Errori e timeout
lasciano la scelta modificabile, senza simulare un successo. «Aspetto» permette
di modificarla in seguito; Indietro annulla una modifica non confermata.

La scelta riguarda la rappresentazione di ALLMA, non il genere dell’utente.
Resta separata dal nucleo nominale, dalla personalità e dalla memoria.
La sezione versionata `avatar_appearance` del cognitive_state.json usa il
profilo attivo del backend; l’interfaccia non può indicare un proprietario.
È inclusa negli stessi backup dello stato cognitivo. Le impronte precedenti
sono conservate, ma un vecchio profilo deve comunque scegliere l’aspetto.

## Qualità grafica

Il precedente campione adulto è sostituito da un busto infantile completo:
24.000 punti, 4.841 vertici di superficie e 9.588 triangoli. Occhi con volume,
iride e riflesso, palpebre più aperte, naso piccolo, guance piene e cranio grande.
Superficie con illuminazione morbida, punti più fini, normali illuminate dopo
la rotazione e bordo del busto sfumato anche lateralmente. La rotazione
orizzontale è libera e periodica a 360°; quella verticale resta limitata per
mantenere il busto leggibile. «Vista frontale» ripristina l’inquadratura.

Si conserva lo zoom sul cervello con tutti i 24 moduli, pausa e Indietro.
L’espressione segue soltanto segnali recenti sufficientemente affidabili; la
forma mantiene le variazioni personali e quelle consolidate della coalescenza.
Il genere visivo non viene ricavato dalle emozioni o dalla storia dell’utente.

L’età iniziale è una direzione artistica di circa sei mesi. Non è un modello
biologico: i target upstream «baby» corrispondono a circa un anno e ricevono
ulteriori adattamenti locali delle proporzioni. Questa modifica non aggiunge
invecchiamento automatico né misura l’intelligenza tramite l’aspetto.

## Risorse e prestazioni

Dati geometrici derivati dagli asset CC0 ufficiali MakeHuman: base hm08 e sei
target baby, mediati. Nessun codice MakeHuman o servizio grafico remoto.
Fonti e licenze: assets/web/AVATAR_ASSET_LICENSE.txt. I target originali e
l’inventario dei risultati restano nell’archivio di analisi, fuori dall’APK.

- Asset derivato: 510.211 byte, senza modello AI aggiuntivo.
- WebGL 1, sette attributi, tre passaggi GPU come nel ritratto precedente.
- Un unico ciclo di fotogrammi; 12 fps a riposo, 20 durante attività osservata.
- Rendering sospeso con pagina chiusa, nascosta, in pausa o durante la scelta.
- DPR limitato a 1,5 e ripiego Canvas con 6.000 punti se WebGL manca.
- Nessuna generazione LLM causata dal ritratto.

Non sono state misurate variazioni di batteria, temperatura o velocità GPU.

## Verifiche

- 136 test Python passati: scelta, isolamento dei profili, persistenza,
  salvataggio fallito, dati invalidi, backup/ripristino, memoria, crescita,
  navigazione, risorse offline e ponte Android.
- Due verifiche Node passate: geometria e ciclo dell’osservatorio.
- Browser, dati sintetici: 33 verifiche avatar, 52 navigazione, 70 chat passate.
- Controllo visivo mobile 390×844: ingresso, fronte, profilo e retro.
- APK verificata: payload aggiornato coincidente, ARM64 e runtime esistenti.

Archivio delle prove:
`/Users/erikahu/ALLMA/analisi/2026-10-19/avatar-infante/`

La qualità estetica resta una valutazione visiva: questi risultati misurano
il funzionamento dei flussi e delle regressioni, non un punteggio di bellezza.
La conferma visiva sul dispositivo da parte dell’utente è separata dai test
browser. Nessuna scelta è stata effettuata nel suo profilo reale.

## Installazione

Build 102518 installata con aggiornamento conservativo, codice versione
confermato dal sistema Android. Processo attivo e nessun errore tecnico
d’avvio nei log filtrati. Collaudo estetico dell’utente richiesto separatamente.

APK SHA-256: `5b64417b47297f37092ea0f782ef601ace357a4be68b72894ff9866b4c1cfc9e`.

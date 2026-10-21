# Presenza di ALLMA e zoom sul cervello · 19 ottobre 2026

## Esperienza

Toccando il titolo ALLMA si apre prima un busto tridimensionale di particelle, dalle spalle al viso. Il comando «Esplora il cervello» entra nell’osservatorio dei moduli già esistente; «Torna ad ALLMA» e Indietro Android riportano al ritratto. Un altro Indietro torna alla chat. Invio, annullamento, risposta e memoria della chat usano gli stessi percorsi precedenti.

Il ritratto può essere ruotato con trascinamento o frecce. Lo sguardo, le sopracciglia, gli angoli della bocca e i piccoli movimenti del capo sono simbolici; il lieve movimento a riposo è un’animazione ambientale, non attività cognitiva inventata. Le pulsazioni colorate derivano soltanto dai nuovi eventi effettivamente osservati dei moduli.

## Identità, espressione e crescita

- `AvatarPresence` conserva un seme casuale locale per profilo nella sezione `avatar_identity` di `cognitive_state.json`. Non dipende da nome, età, sesso, fotografia, dispositivo o modello GGUF. L’identità è inclusa nel backup dello stato cognitivo e viene recuperata al ripristino.
- Mascella, guance, naso, distanza degli occhi e sopracciglio hanno piccole variazioni iniziali determinate da quel seme. Sono una base grafica, non ricordi o tratti psicologici attribuiti alla nascita.
- Empatia e curiosità apprese dalla coalescenza, insieme alle sole tendenze di stile consolidate, modulano lentamente morbidezza e apertura del ritratto. Una richiesta isolata o una tendenza ancora sospesa non viene trattata come carattere consolidato. La forma viene ricalcolata dall’evidenza attuale: una correzione che ritira l’evidenza può ritirarne l’influenza visiva.
- Gli indizi emotivi recenti dello stesso profilo, con confidenza almeno 0,6, influenzano temporaneamente il sorriso, l’attenzione e la tensione dell’espressione. L’effetto si attenua entro tre minuti; dati scaduti, futuri, incerti o appartenenti ad altri utenti non guidano l’espressione. Non modificano il seme o la morfologia.
- Guardare il ritratto non genera interazioni apprese, non aumenta l’esperienza e non interroga il modello. Alla grafica arrivano solo parametri numerici, conteggi e stati, senza testi dei ricordi o della conversazione.
- Dati identitari non validi non vengono sostituiti silenziosamente. Un problema del ritratto lascia disponibile l’osservatorio del cervello.

Questa è una corrispondenza artistica progettata per ALLMA. Non stabilisce un legame scientifico fra genetica del volto, felicità e tristezza e non misura sentimenti soggettivi di ALLMA. Non è una ricostruzione dell’aspetto fisico dell’utente.

## Grafica e costo

Base anatomica neutra MakeHuman, risorsa grafica CC0: vengono inclusi soltanto campioni di testa, collo e spalle, senza texture o codice applicativo MakeHuman. Attribuzione e provenienza sono in `assets/web/AVATAR_ASSET_LICENSE.txt`; il generatore riproducibile è `tools/build_avatar_mesh.py`.

Il pacchetto contiene 16.000 punti e fino a 1.500 collegamenti, con una piccola superficie usata solo per la profondità, che nasconde i punti sul retro del volto. L’asset compresso come dati JavaScript pesa circa 323 KiB. WebGL nativo del WebView, senza Three.js, librerie remote, nuove reti neurali o download all’apertura. I buffer vengono aggiornati quando cambia la forma; le deformazioni animate sono eseguite dallo shader. La risoluzione dei canvas viene ricavata dal contenitore, indipendentemente dallo zoom CSS.

L’animazione punta a 12 fotogrammi/s a riposo e 20 durante il turno, solo nell’avatar visibile; il cervello conserva il proprio limite di 24. Esiste un fallback Canvas 2D con meno punti e obiettivo 8 fotogrammi/s. Pausa, «riduci movimento», chiusura e passaggio in background interrompono il ciclo; il ripristino del contesto WebGL ricrea i buffer. Un’unica gestione dei fotogrammi coordina avatar e cervello.

Un ritratto animato consuma più di un’immagine ferma. Nessuna riduzione percentuale di batteria o temperatura è stata misurata. La prova nel browser Mac ha rilevato una mediana di circa 0,1 ms per l’invio dei comandi di un fotogramma (10 campioni): non misura il tempo GPU, il consumo energetico o le prestazioni Android.

## Verifiche

- 120 test Python distinti passati: suite di 119 casi più il nuovo controllo degli asset offline. Inclusi persistenza, isolamento dei profili, affetto temporaneo, tendenze consolidate e ripristino da backup.
- Due controlli Node passati: geometria deterministica e contenuta, indici validi, coordinate finite, fallback, lifecycle dell’osservatorio e contratto dei messaggi.
- 144 controlli nel browser: 22 sull’avatar (inclusa la risoluzione indipendente dallo zoom), 52 sulla navigazione, 70 su chat/voce/sogni. Tutti passati. Le prove usano dati sintetici.
- Controllo responsive a 320 × 568 e 390 × 844. Anteprime salvate con soli dati sintetici.
- Sulla build Android 102516 l’utente ha confermato: «Ritratto, zoom, pausa e Indietro funzionano».
- La build finale 102517 aggiunge la correzione della risoluzione dei canvas nello zoom e il contrasto finale dei punti. Stesso percorso funzionale; pacchetto verificato prima dell’installazione. La resa visiva finale richiede ancora riscontro sul telefono, distinto dal collaudo funzionale della 102516.

APK finale: versione `0.9.0.0`, build `102517`.
SHA-256: `685e9bc5495f1c20e5fc28fd7003c3b6612fd6b0c96f20cf66fe8c48fe29e8cd`.
Artefatti: `../../analisi/2026-10-18/avatar-allma/`.

## Riferimenti consultati

- [Face and context integration in emotion inference (Nature Communications, 2024)](https://www.nature.com/articles/s41467-024-46670-5): interpretazione delle espressioni nel contesto; non una mappa universale carattere-volto.
- [Facial Action Coding System, Paul Ekman Group](https://www.paulekman.com/facial-action-coding-system/): descrizione dei movimenti facciali; nessun manuale o classificatore FACS è incorporato.
- [MakeHuman, licenza ufficiale](https://github.com/makehumancommunity/makehuman/blob/master/LICENSE.md): distinzione fra codice applicativo e asset grafici CC0.
- [WebGL specification, Khronos](https://registry.khronos.org/webgl/specs/latest/1.0/): contesto, preferenza energetica e perdita/ripristino del contesto.
- [W3C C39](https://www.w3.org/WAI/WCAG22/Techniques/css/C39.html): rispetto della preferenza per il movimento ridotto.

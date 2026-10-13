# Modalità vocale: restyling e ottimizzazioni

La sfera neurale e lo sfondo cosmico restano il centro della schermata. La nuova composizione usa luce azzurra, titolo leggibile, trascrizione in un riquadro scorrevole e controlli SVG coerenti. Le posizioni non sono più ancorate a distanze fisse dal fondo: status, trascrizione e pulsanti seguono il flusso del layout. Verificato nel browser anche a 320 × 640 CSS pixel, senza sovrapposizioni. La schermata chiusa è nascosta anche all’albero di accessibilità.

## Riduzione del lavoro

- Animazione al massimo a 30 FPS, 20 durante il ragionamento e 5 con movimento ridotto; nessun disegno quando il documento è nascosto.
- Risoluzione canvas limitata a un rapporto pixel di 1,5; 120 neuroni invece di 170 e 28 particelle invece di 50.
- Aggiornamenti del livello microfono al massimo 20 volte al secondo, riducendo i passaggi Python–WebView.
- In modalità vocale il prompt chiede frasi naturali e concise. Per domande semplici il limite passa da 256 a 192 token; per quelle complesse resta 512. I budget di ragionamento e tutti i controlli identitari restano invariati. Limiti metabolici più restrittivi continuano a prevalere.
- La modalità della richiesta viene catturata prima di avviare il worker: chiudere la schermata durante il lavoro non cambia la richiesta già partita e impedisce la successiva lettura.
- Domande autobiografiche dirette precedute da un saluto o dal vocativo ALLMA/Alma vengono riconosciute dal nucleo identitario. «Ciao Alma Come ti chiami», prima elaborata dal modello in circa 35 secondi nella prova del 2 ottobre, ora usa la risposta documentata del nucleo senza inferenza LLM. Una domanda composta o narrativa continua a passare al modello.

Queste riduzioni non sono percentuali misurate sulla latenza, temperatura o consumo dell’intera app. La velocità delle domande generali rimane legata al modello e alla temperatura del telefono. La lettura inizia dopo la validazione finale: non si anticipa audio da bozze che potrebbero venire corrette.

## Verifiche

- Suite completa: 367 superati, 15 saltati.
- Dopo l’aggiunta del controllo di integrazione UI: 27 test mirati superati, compresi cattura della modalità e assenza di riproduzione dopo la chiusura.
- Sintassi JavaScript e verifica della corrispondenza APK/sorgenti superate.
- SHA-256 APK: `4aaf1b915a0be1f7e9703a560e83c56a1ff2df01b16eea41aa8dabf54943991a`.
- APK installata con aggiornamento senza cancellare dati; motore TTS italiano pronto. Schermata controllata sul Samsung e acquisita in `telefono.png`. Nei log la modalità vocale apre il riconoscitore locale e la chiusura invalida correttamente l’ascolto.

Non è stato eseguito un nuovo confronto end-to-end parlato: non viene dichiarata una percentuale di miglioramento della velocità. Log e anteprima in `/Users/erikahu/ALLMA/analisi/2026-10-06/voce-restyling/`.

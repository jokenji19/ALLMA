# Restyling ALLMA — 1 ottobre 2026

## Implementato
- Palette azzurro cielo e bianco ghiaccio, testo blu scuro, variante scura.
- Logo vettoriale pianeta con orbita e stelle, testata con menu e nuova conversazione.
- Font Inter variabile incluso offline, con licenza OFL del repository ufficiale rsms/inter. Nessun SF Pro incorporato.
- Messaggi ALLMA senza grandi schede; bolle utente azzurre; schermata iniziale senza conversazioni fittizie.
- Composer con invio visibile, modalità vocale e interruzione durante generazione.
- Dettagli del ragionamento chiusi per impostazione predefinita, pulsante accessibile e tempi spostati nel pannello.
- Nuova chat dalla testata senza apertura involontaria del menu; aggiornamento dello stato dei pulsanti anche con dettatura.
- Supporto layout stretto, pannelli e tema scuro; riduzione animazioni secondo preferenza di sistema.

La fase `miglioramenti_prestazioni` resta separata. Nessuna modifica al motore di generazione in questa fase.

## Verifiche
- 72 test Python di regressione passati. Il runtime OpenMP ha emesso avvisi SHM nell'ambiente ristretto al termine; nessun test fallito.
- 16 controlli JavaScript nel browser sulla pagina reale con bridge di test: doppio invio, testo finale autorevole, rilascio backend, token obsoleti, annullamento, nuova chat, sanificazione Markdown e dettagli richiudibili.
- Ispezione visiva a 320×640 e 412×892, menu, impostazioni, tema chiaro/scuro.
- Sintassi JavaScript verificata con Node.
- `pack_brain.py`, build Android debug e verifica APK completati.
- SHA256 APK: `f18283e1031ca88663f0d23a2a9ef07cf98cd0105e2ea9be29172030b7d7269e`.
- APK installato con `adb install -r` sul dispositivo R3CY80QWZ9B; installazione riuscita.
- Presenza del modello (1.834.426.016 byte) e della memoria persistente verificata dopo aggiornamento. Nessuna disinstallazione o cancellazione dati.
- Collaudo visivo Android e tastiera ancora da completare: dispositivo bloccato, richiesto sblocco manuale all'utente.

## File principali
- `assets/web/index.html`
- `assets/web/sky.css`
- `assets/web/script_v24.js`
- `assets/web/fonts/InterVariable.woff2` e `Inter-LICENSE.txt`
- `tests/regression/chat_web_checks.js`
- `buildozer.spec` (inclusione woff2)
- `main.py` (payload rigenerato)

Log e anteprima sono in `/Users/erikahu/ALLMA/analisi/2026-10-01/restyling/`.
L'anteprima browser contiene una risposta simulata solo nel server di collaudo esterno al progetto: non è inclusa nell'APK.
Le modifiche sono salvate localmente, senza commit o push.

## Correzioni dopo segnalazione sul telefono

La schermata reale mostrava HTML nuovo con CSS precedente: logo enorme, testi sovrapposti e pulsanti privi di dimensioni. Il caricatore installato incorporava solo `style_v24.css` e `settings_ui.css`, eliminando il collegamento a `sky.css`. La correzione `web_assets.inline_stylesheets` incorpora tutti i fogli nell'ordine originale e il font WOFF2 come risorsa dati offline. È stata verificata anche la corrispondenza del modulo estratto sul dispositivo.

Il collaudo con tastiera ha poi evidenziato che `FLAG_LAYOUT_NO_LIMITS` faceva traslare tutta la pagina e nascondeva la testata. Il bridge ora riserva le barre di sistema e usa `SOFT_INPUT_ADJUST_RESIZE`, con inset CSS nativi a zero per non contare due volte le barre.

10 test mirati passati (asset offline e regressioni ciclo di vita/build), compilazione e verifica payload riuscite. APK aggiornato SHA256: `de35a981c7eb8a959e4923213fcaff9da09f44f35d5a51839fc3fe0892c1c4b5`.

APK corretto installato con successo. Verifica visiva sul dispositivo: testata, logo, messaggi e composer corretti, anche durante generazione. L'utente sta usando la chat durante il collaudo: sospese le interazioni automatiche e richiesto di lasciare la tastiera aperta per verificare il ridimensionamento senza interferire.
Verifica finale: conversazione reale correttamente allineata dopo risposta, dettagli chiusi e invio visibile. La verifica della tastiera resta non conclusiva: nelle ultime acquisizioni Android la segnala chiusa; successivamente compare un benchmark in corso. Non dichiarato superato il collaudo IME.

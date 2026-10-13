# Layout condiviso: avvio, chat e voce

La schermata vocale è ora il riferimento visivo anche per avvio e chat: blu profondo, luce azzurra, testo Inter, pianeta con stelle, bordi morbidi e superfici discrete.

## Avvio

- Rimossa la vecchia schermata viola con «ALLMA SYSTEM» e un’emoji non supportata.
- Pianeta e stelle disegnati con primitive native: nessuna immagine generata, connessione o animazione continua necessaria.
- Font Inter regolare e semibold derivati dal font già distribuito nel progetto; licenza conservata in `assets/web/fonts/Inter-LICENSE.txt`.
- Indicazioni in italiano, testo adattabile e barra basata sull’avanzamento reale del download. Non si finge una percentuale durante il controllo dell’integrità del modello.
- Layout centrato con dimensioni esplicitamente collegate alla schermata; verificato a 360 × 800 nel rendering Kivy.
- Anche la breve schermata prima dell’estrazione dei componenti usa la palette e un titolo semplice, senza il vecchio logo bitmap. In questa fase, prima che Inter sia estratto, resta il font nativo.

## Chat e schermate principali

- Tema cosmico iniziale quando non è stata salvata una preferenza. Il tema chiaro resta disponibile e un’eventuale scelta precedente viene rispettata.
- Chat, messaggi utente e ALLMA, compositore, menu, pannelli e caricamento WebView condividono la palette.
- Conservati pianeta e stelle nel marchio, pulsanti SVG e disposizione della chat.
- Barre Android scure con icone chiare nel tema cosmico; il cambio tema aggiorna anche le barre native.
- Nessuna modifica alla memoria, al modello o ai controlli della pipeline per questo restyling.

## Verifiche

- Suite completa: 368 test riusciti, 15 saltati.
- Controlli mirati di asset web e ciclo di vita/build: 10 riusciti.
- 16 controlli interattivi della chat nel browser: invio, doppio invio, interruzione, nuova conversazione, dettagli, messaggio finale e rendering sicuro.
- Layout nativo costruito realmente con Kivy e Inter; esportazione della schermata per verificarne la centratura.
- Chat verificata sul Samsung: una conversazione reale appare con il nuovo tema e le barre scure.
- Versione finale installata con aggiornamento e payload verificato. SHA-256 APK: `9697fb282f8ed0a86a01f1f24517060bad66ad398f9793122a0c0262e0e04370`. Il telefono è tornato bloccato prima della seconda acquisizione dell’avvio; la centratura finale è verificata nel rendering nativo, mentre la chat è stata acquisita sul dispositivo.

Anteprime e log in `/Users/erikahu/ALLMA/analisi/2026-10-06/layout-cosmico/`. Gli esempi generati nel browser restano in una pagina temporanea e non entrano nella memoria di ALLMA. Modifiche salvate localmente; nessun nuovo commit o push effettuato per questa richiesta.

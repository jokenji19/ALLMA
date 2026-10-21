# ALLMA · Paper

Restyling richiesto prendendo come riferimento l'app mobile Claude. Screenshot
pubblici ufficiali consultati sull'App Store e scheda Google Play. Nome,
identità e funzioni restano ALLMA; nessun logo o asset di Claude distribuito.

## Interfaccia

- Tema chiaro avorio #faf9f5, testo caldo #292722, accento terracotta #ad5135.
- Tema scuro grigio caldo #262624, testo #eeece5, accento #e3a28a.
- Inter locale per comandi e messaggi utente; serif di sistema per risposte,
  titolo e schermata iniziale. Nessuna dipendenza da font scaricati a runtime.
- Risposte su sfondo pagina, bolle utente neutre, niente riflessi o blur.
- Campo multilinea con crescita fino a 140px, invio, voce e scelta del modello.
  Invio da tastiera invia; Maiusc+Invio va a capo; composizione IME non invia.
- Sidebar sobria con icone vettoriali; pannelli centrati con sola dissolvenza.
  Aprire le impostazioni dal compositore non apre più la sidebar sullo sfondo.
- Voce con testo serif, trascrizione separata, anello animato soltanto durante
  ascolto/elaborazione/risposta. Preferenze di movimento ridotto rispettate.
- Avvio Kivy e bootstrap con palette avorio/terracotta e avanzamento reale
  per fasi, senza percentuali inventate sul caricamento del modello.
- Barre Android sincronizzate con i due temi.

## Verifiche

20 test Python mirati passati: risorse offline, font incluso, avvio asincrono,
dispatch chat, voce e thread benchmark. Verifica sintattica JS e compilazione
Python riuscite. 70 controlli browser completi passati sul DOM reale sia a
390x844 sia a 320x560 CSS pixel: streaming, annullamento, sanitizzazione,
revisioni oniriche, stato vocale, animazioni e centratura dei tre pannelli.
Campo multilinea verificato a sei righe: altezza massima 140px e nessuna
fuoriuscita orizzontale. Tema chiaro e scuro controllati visivamente.

Un controllo browser era obsoleto: pretendeva il benchmark nelle impostazioni
avanzate, mentre era stato già reso direttamente accessibile per richiesta
dell'utente. Il controllo ora verifica questa posizione e mantiene la verifica
dello stato motori nelle impostazioni avanzate.

Anteprima di chat con testo sintetico e fixture browser servite soltanto dal
server di collaudo esterno in /private/tmp; non incluse nell'APK o nella memoria.

## APK

Build finale 102470, versione 0.9.0.0. Payload corrente verificato, runtime ARM64
llama-cpp-python 0.3.36 con supporto qwen35 conservato.
SHA256 APK: 9afac21a83e6202573f1bc864cc10b0beef4606151130d2e7bc22833dcfb38fa.
Installazione adb install -r riuscita. Modelli e archivi personali preservati.
Controllo visivo Android richiesto all'utente: al primo tentativo il telefono
mostrava NotificationShade, non ALLMA. Nessuna schermata del sistema conservata.

Telefono sbloccato dall’utente: intro nativa verificata visivamente, con
palette avorio/terracotta, testi e avanzamento senza sovrapposizioni.

Chat Android verificata a 384x783 CSS pixel: nessun overflow. Pannelli
impostazioni, memoria e sogni centrati e contenuti nella finestra. Variante
scura verificata sul telefono; eliminate l’ultima superficie bianca del
vecchio pulsante vocale e l’emoji del sonno, sostituita da un’icona SVG.
Tema chiaro originale ripristinato dopo la prova. 20 test mirati ripetuti
sulla build finale, tutti passati (0,23s).

Eliminata anche la palette duplicata della WebView per le barre Android:
entrambi i percorsi usano AndroidBars.color_hex(), evitando il ritorno
all’azzurro dopo il caricamento.

Verifica conclusiva: installazione 102470 confermata sul dispositivo,
inizializzazione Llama riuscita alle 11:54:41. Schermata finale acquisita
con tema scuro attivo: barre Android coerenti, microfono senza superficie
bianca e nessuna sovrapposizione visibile. Screenshot:
../analisi/2026-10-15/restyling-paper/android-finale.png (rispetto alla radice ALLMA_V4).

## Ritocchi richiesti dopo il collaudo

Build 102473: sottotitolo a riposo eliminato (stato di generazione conservato),
nuova chat con icona finestra/più, profilo ridisegnato con etichette associate,
età facoltativa, chiusura esplicita/Escape/sfondo e contenimento del focus.
Sidebar chiusa prima del popup. Profilo non salvato durante il controllo.
Palette scura del popup corretta per eliminare la vecchia variabile blu.
Navigazione Android nascosta con barre transitorie richiamabili dal bordo;
layout ridimensionato senza riservare spazio alla navigazione nascosta,
rispettando invece lo spazio della barra di stato. Contrasto e divisore inferiori automatici disattivati.

20 test mirati passati (0,26 s), sintassi JS/Python valida, payload APK corrente.
SHA256: 6d97d7ed213f8261ca443c7f894727e34892bda723258ad7e423e74785990e7d.
Installazione con mantenimento dati riuscita.

Verifica finale sul telefono: viewport 384x798 CSS pixel, titolo interamente
visibile, nessuna striscia o maniglia di navigazione inferiore, nessun overflow.
Popup contenuto nello schermo, colore avorio corretto, chiusura Escape riuscita;
variante scura già verificata con la correzione della palette. Schermata
principale ripristinata al termine. Evidenze: android-refined.png e
android-profile.png nella cartella di analisi restyling-paper del 2026-10-15.

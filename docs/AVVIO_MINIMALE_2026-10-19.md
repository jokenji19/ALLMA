# Avvio minimale — 19–20 ottobre 2026

Richiesta: semplificare la schermata «Uno spazio per pensare insieme», aggiungere un cerchio che si completa con percentuale sotto e un’immagine ispirata alle due mani, umana e robotica, dei riferimenti.

## Risultato

Composizione unica per bootstrap, verifica del modello, caricamento nativo e apertura della chat: marchio ALLMA, illustrazione delle mani, titolo breve, cerchio sottile, percentuale sotto e una sola riga di stato. Rimossi slogan aggiuntivo, elenco delle fasi, pallini e barra orizzontale. I dettagli compaiono per download ed errori.

`startup_ui.py` è condiviso dalla prima schermata, disponibile prima dell’estrazione, e dalle schermate interne. Immagine, font e modulo grafico sono aggiunti esplicitamente agli asset dell’APK. Prima di avviare la schermata, il bootstrap li recupera dal pacchetto installato in una propria cartella di codice, riutilizzando i file identici e sostituendo quelli cambiati con scritture atomiche. Non viene decompressa una seconda volta l’intera applicazione. La breve schermata web segue la stessa composizione, con immagine incorporata: nessuna richiesta di rete per il caricamento grafico.

Il progresso è basato su checkpoint completati, non su una stima del tempo rimanente: preparazione file fino al 20%, verifica del modello fino al 40%, sistemi e memoria 60%, modello caricato 80%, preparazione dell’interfaccia 90%, documento pronto 100%. Durante il caricamento nativo la percentuale resta sul checkpoint noto; un piccolo indicatore di attività si muove senza aumentare la percentuale. Per i download con dimensione nota, la fase 20–40% usa il progresso comunicato dal downloader. Se la dimensione non è nota, non viene inventata una percentuale del download.

Pausa e chiusura fermano l’animazione; un aggiornamento tardivo non la riattiva. La ripresa è esplicita e rispetta la preferenza Android per le animazioni ridotte. Errori e cancellazione non mostrano 100%.

## Illustrazione

Generata con lo strumento integrato imagegen: due mani che si avvicinano, una umana e una robotica, disegno editoriale sottile e quasi monocromatico, sfondo trasparente. Risorsa finale: `assets/web/images/startup-connection.png`. Prompt completo: `analisi/2026-10-19/avvio-minimale/prompt-immagine.txt`. L’immagine viene caricata localmente e resta statica.

## Verifiche

22 test Python su avvio asincrono, risorse e navigazione: superati. Controllo nativo con Kivy effettivo: illustrazione e testi renderizzati, percentuale monotona, errore senza falso completamento, pausa persistente e ripresa corretta. Layout verificato a 390×844, 320×480, 844×390 e 320×320, anche con dettaglio di errore. Test della preparazione iniziale: prima copia, riutilizzo della cache, recupero di file corrotti, aggiornamento APK, rifiuto di risorse mancanti prima dell’import e percorso desktop. Sei controlli browser: immagine caricata, risorsa offline, vecchio spinner rimosso, cerchio e numero coerenti, numero sotto il cerchio e nessuna fuoriuscita orizzontale.

L’anteprima nativa nel dossier è prodotta dal widget di prova, non da una cattura dello schermo personale. Lo stato della build e dell’installazione è registrato in `esito-finale.json`.

## Installazione del 20 ottobre

Build 102526 compilata e installata sul telefono. Verifica APK superata, incluse le quattro risorse specifiche del primo avvio. Le dieci risorse controllate dopo l’avvio corrispondono ai sorgenti, inclusi modulo grafico iniziale, illustrazione e font nella cache effettivamente preparata dal bootstrap. Nessuno degli errori tecnici cercati è emerso nel campione iniziale dei log. La valutazione estetica sul telefono resta all’utente.

Controllo finale sul dispositivo: inizializzazione del modello, creazione della chat e caricamento della WebView completati. Nessuno degli errori tecnici cercati nei log di avvio.

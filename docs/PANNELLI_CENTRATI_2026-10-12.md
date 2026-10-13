# Correzione pannelli sidebar — 12 ottobre 2026

L’animazione allma-appear aggiunta ai pannelli sovrascriveva translate(-50%, -50%) con translateY(0), lasciando l’angolo superiore sinistro al centro dello schermo. Risultato: Impostazioni, Memoria e Diario spostati verso il basso a destra.

Corretta con una keyframe dedicata allma-panel-appear: centratura mantenuta sia all’inizio sia alla fine; spostamento introduttivo limitato a 6px verticali. Animazioni delle bolle chat invariate e preferenza movimento ridotto preservata.

Il test iniziale riproduce FAIL: Pannello settings centrato dopo l’animazione. Dopo la correzione, **70 controlli web superati** a 390×844 e **gli stessi 70 a 320×568**. Tre regressioni nuove misurano le coordinate reali dei pannelli alla fine dell’animazione. Verificata anche l’apertura di Impostazioni tramite i pulsanti del menu: centro (195,422) su viewport 390×844. Screenshot da fixture locale con dati sintetici, non cattura del telefono.

Compilazione riuscita, verifica payload_matches=true. Installazione adb install -r: Success; activity avviata e dati conservati. SHA-256: 14f742dc1a8ca9fd220260dc864787aff9ba6b4202d675b9855db3acdf136b26. Impronta dell’APK installata identica alla build locale. Modifica limitata al CSS; non ripetuta la suite Python perché non cambiato codice Python. L’ultima suite completata prima di questa correzione resta 626 passed, 15 skipped.

Modifiche salvate localmente, nessun commit o push. Artefatti: /Users/erikahu/ALLMA/analisi/2026-10-12/pannelli-centrati.

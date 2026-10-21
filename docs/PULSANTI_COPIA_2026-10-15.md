# Pulsanti Copia nei messaggi

Piccole icone da 15px con etichetta Copia e area tattile di 40px: sotto la
risposta a sinistra e sotto i messaggi utente a destra. Colori del tema e
conferma Copiato per due secondi. In caso di errore, Riprova. Nessuna animazione
continua. Il testo copiato è il corpo originale del messaggio, con Markdown,
senza etichette UI, timer o dettagli del pensiero. Nello streaming il pulsante
si rende disponibile alla chiusura con il testo finale autorevole.

Android usa ClipboardManager sul thread UI e conferma solo dopo setPrimaryClip.
Il browser usa Clipboard API con fallback execCommand. Timeout e gestione
errori impediscono pulsanti bloccati; nessun testo di appunti nei log del bridge.

13 test mirati esistenti passati; sintassi JS/Python valida.
APK 102475 installata con mantenimento dati, payload verificato.
SHA256: ba752d277ba2526c415aa46b8eab313ab6b2f8273a1eb8c4e2f181bff6bdba34.

Prova Android con due messaggi sintetici temporanei, non persistiti:
copia nativa bot e utente confermata rispettivamente in 151 e 303ms;
testo inviato esatto, pensiero escluso, pulsanti riabilitati, nessuna richiesta
pendente. Elementi di prova rimossi al termine, nessun messaggio al modello.

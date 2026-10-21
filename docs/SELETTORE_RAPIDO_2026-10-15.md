# Selettore modelli senza letture GGUF durante l'apertura

L'inventario ModelManager.snapshot usava _valid per ogni modello e leggeva
completamente tutti i GGUF alla prima apertura. Ora usa metadati stat e indica
se il file è soltanto installato oppure già verificato. I file presenti non
sono certificati sulla base delle sole dimensioni: apply passa ancora dal
download verificato e dallo SHA-256 prima del cambio. L'interfaccia distingue
verifica, download e caricamento e richiede l'elenco già all'avvio della chat.

Le verifiche riuscite sono condivise tra istanze nel solo processo corrente,
vincolate a percorso assoluto, dispositivo, inode, dimensione, mtime, ctime e
hash atteso. Nessuna fiducia persistente aggiunta tra riavvii. Una modifica
anche a dimensione invariata invalida la verifica. Le scelte nel menu restano
selezionate quando un aggiornamento conferma lo stesso modello attivo.

31 test mirati passati: manager, download, asset e avvio. Coperti elenco senza
lettura dei byte, cache tra istanze, invalidazione, errore di download senza
cambio motore, ripresa trasferimenti e checksum. Sintassi JavaScript valida.

APK 102474, versione 0.9.0.0, installata con mantenimento dati.
SHA256: 1b12c75902c51eebd8e8186b1acb5ff5aac18a919de6c2ddfc7f5d3d020f9766.
Payload corrente e runtime ARM64 qwen35 verificati.

Collaudo Android: entrambi i modelli popolati automaticamente nella chat,
Qwen 3 1.7B attivo, Qwen 3.5 2B presente e non ancora verificato nella sessione.
Tre richieste reali elenco, inclusi bridge/polling/aggiornamento DOM:
104, 345 e 345 ms. Selezione alternativa conservata dopo i refresh,
pannello aperto dal pulsante del composer. Nessun cambio effettivo del modello
eseguito per questo collaudo. Dati e preferenza attiva conservati.

Queste misure riguardano l'elenco a chat pronta. Non misurano una riduzione
dell'avvio a freddo né dei tempi di inferenza o del cambio modello.

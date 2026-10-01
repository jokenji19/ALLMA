# Correzione chat del 30 settembre 2026

La schermata segnalata mostrava pensiero inglese nella risposta e testo ripetuto.

## Causa e modifiche

Il prompt termina con <think>, quindi la risposta nativa contiene solo il tag di chiusura. Il vecchio filtro rimuoveva esclusivamente blocchi con entrambi i tag e poi soltanto la prima frase inglese. Ora il wrapper interpreta anche l’apertura presente nel prompt. Il parser condiviso gestisce tag suddivisi in qualunque numero di token e mantiene separati pensiero e risposta nello streaming. Un ragionamento non terminato non viene promosso a risposta.

Rimossi i filtri euristici che cancellavano frasi inglesi legittime o paragrafi precedenti a tre ritorni a capo. Rimosso il secondo completamento automatico: costruiva una conversazione malformata sopra un pensiero ancora aperto e concatenava senza controllo un’altra risposta. Ora ogni turno effettua una sola generazione; una risposta esaurita per limite token non viene completata automaticamente.

Queste modifiche correggono la separazione e una fonte applicativa di ripetizioni; non garantiscono che il modello non produca da sé ripetizioni o contenuti incoerenti. Le risposte già memorizzate non sono riscritte: la verifica va fatta in una nuova chat.

## Verifiche

321 test passati, 15 saltati, nessun fallimento. Dieci nuove regressioni su separazione/streaming/wrapper/core. Corretto inoltre un test dei pattern temporali che falliva alle 10 o alle 15 perché ignorava gli eventi già registrati alla creazione delle memorie.

APK compilato e verificato: bin/allma_prime-0.56-arm64-v8a-debug.apk.
SHA256: 69ed70ac0f03f7294e02338f3d48ded6c0ef4a49a802c8be70d0f85960663ba3.

Log e XML: /Users/erikahu/ALLMA/analisi/2026-09-30/correzione-chat/.
Modifiche salvate localmente; nessun commit o push.

## Ulteriore difetto osservato sul telefono

Dopo il primo aggiornamento, la schermata mostrava pensiero separato e una sola risposta, ma una frase priva di soggetto. I filtri StructuralCore/Neuroplasticity cancellavano le auto-presentazioni. Ora le cinque forme «sono un…» previste dalle regole sono normalizzate in «Sono ALLMA», preservando soggetto e verbo. Un test attraverso la pipeline verifica la frase relativa completa.

La prima installazione correttiva è riuscita; verificati processo attivo, nuovo parser estratto sul dispositivo, archivi in files/allma_state e modello da 1.834.426.016 byte ancora presente. La schermata acquisita è avvio.png negli artefatti.

Installazione finale dell’APK con SHA sopra indicato: adb install -r concluso con Success, avvio dell’Activity richiesto con esito positivo. Archivi e modello ancora presenti dopo questo secondo aggiornamento. La correzione del soggetto è verificata dai test; resta da controllare una nuova risposta reale con quest’ultima build.

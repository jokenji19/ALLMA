# Scarta: comportamento visibile e aggiornamento Android — 6 ottobre 2026

La precedente interfaccia lasciava tutte le schede visibili dopo lo scarto. L’ipotesi era esclusa dalle risposte, ma il comportamento visivo risultava poco comprensibile sul telefono.

Ora le schede scartate spariscono dall’elenco principale dopo la conferma del salvataggio. Il pulsante Mostra scartate (N) permette di consultarne ancora origine e cronologia e di rivedere la decisione. Nessuna cancellazione definitiva. Se il salvataggio fallisce la scheda rimane visibile. Nascondi scartate ripristina l’elenco delle ipotesi attive.

## Verifica

- 45 controlli web superati, inclusi sparizione dopo salvataggio, recupero nell’archivio e assenza di ricomparsa al refresh.
- 42 test mirati onirici/persistenza/ponte/WebView superati in 1,33 s.
- Suite completa: 618 passed, 15 skipped, 12 warnings in 62,26 s, con diagnostica di aborti di sottoprocessi sul Mac. Non è un’esecuzione completamente priva di anomalie dell’ambiente. Una ripetizione fuori dal sandbox è stata interrotta dopo 170,17 s durante PyTorch: 125 passed, 1 skipped, 5 warnings fino a quel punto. Non conteggiata come suite completata. La modifica riguarda esclusivamente il frontend e i controlli mirati sono tutti superati.
- pack_brain.py, build Android e verifica payload completati. APK installata con adb install -r: Success. Impronta del base.apk sul telefono identica a quella locale: 4776195a1ec6edeceec812cd7a409076007622a916f7e1ee4f73a780a7819c09.
- Nuovo processo ALLMA 11831 e caricamento WebView verificati nei log.

Prima dell’aggiornamento il ciclo reale aveva generato tre ipotesi in 24,25 s. Nei log Android sono presenti conferme e scarti, con passaggio da revisione 0 a 1 e poi 2, inclusi tentativi ripetuti senza incremento dello stato. L’utente ha riferito che la correzione era visibile: nei log raccolti non è stato trovato il comando correct, quindi quella specifica scrittura non viene dichiarata verificata dall’agente. Il nuovo archivio popolato non è stato copiato, perché la revisione automatica ha richiesto un’autorizzazione specifica ancora pendente.

La verifica visiva finale sul telefono del pulsante Mostra scartate è stata richiesta all’utente; non è stata sostituita con una simulazione dichiarata reale. Restano da verificare il riavvio completo con revisione persistente e il suo effetto sulle risposte del modello. Le ipotesi generate sono ancora metafore vaghe: il prompt poetico del sistema onirico deve essere affrontato in una modifica successiva, senza confondere il risultato con fatti verificati.

Modifiche salvate localmente, nessun commit o push. Artefatti: /Users/erikahu/ALLMA/analisi/2026-10-06/scarta-ipotesi.

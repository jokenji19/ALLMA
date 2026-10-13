# Interfaccia più intuitiva — 12 ottobre 2026

Problema osservato: il Diario affiancava ipotesi, storico delle revisioni e log di generazione, mentre le Impostazioni iniziavano con temperature e mescolavano preferenze quotidiane e strumenti tecnici. Questa gerarchia rendeva difficile capire cosa fare.

## Modifiche

- Diario: titolo Le riflessioni di ALLMA, conteggio delle nuove riflessioni, istruzione breve e tre azioni allineate. Conferma evidenziata, Correggi con stato aperto accessibile e Scarta invariato nella semantica.
- Spiegazioni raccolte in Come funziona?, chiuso inizialmente. Distinzione conservata fra giudizio dell’utente e fatto verificato.
- Origine e revisione resta disponibile per ogni scheda. Mostra scartate conserva accesso alle ipotesi escluse, senza cancellazioni.
- Registro di generazione in Attività dei sogni, chiuso. Pulisci rinominato Svuota il registro visibile, per distinguere l’azione dalla cancellazione delle memorie.
- Impostazioni: sogni e preferenze chat prima; temperature, stato STT/TTS/LLM e benchmark in Impostazioni avanzate. Tutti gli ID e i controlli precedenti conservati.
- Diagnostica ancora nel menu, sotto Strumenti avanzati. Etichette più semplici nella memoria e nel menu.
- Descrizione delle condizioni dei sogni aggiornata alle soglie reali: in carica, almeno 72%, temperatura batteria entro 40 °C.

Nessun cambiamento al modello, agli algoritmi di apprendimento o ai dati personali; visione rinviata.

## Verifica

618 test Python superati, 15 saltati, 12 avvisi di dipendenze in 31,28 s, in modalità offline e con parallelismo limitato. 52 controlli web superati, inclusi conservazione dei controlli avanzati, registro chiuso, conteggio, assenza di ID duplicati e azione principale evidenziata.

Un primo controllo web ha rilevato lo script precedente nella cache del server di prova. URL dei fixture aggiornati: tutti i controlli ora eseguiti sulle risorse nuove. Nessuna modifica alla gestione di cache Android necessaria: i file sono incorporati nella build.

Verifica visiva a 390×844: Diario e Impostazioni leggibili, controlli avanzati apribili e nessuna fuoriuscita orizzontale del pannello Impostazioni. Screenshot con dati sintetici; non rappresenta una cattura del telefono. I valori sensori dell’anteprima browser non sono misure reali Android.

pack_brain.py, compilazione e verifica APK riusciti. Installazione con adb install -r: Success, mantenendo i dati. Activity avviata. SHA-256 della build: 0145b528973f2452c2ec8b0bfe19bf04b0853ffe634239c463cf5f25adfdb129.

Non è stato eseguito un nuovo collaudo manuale completo dei pannelli Android: installazione e avvio non sostituiscono quella prova. Modifiche salvate localmente; nessun commit o push.

Artefatti: /Users/erikahu/ALLMA/analisi/2026-10-12/interfaccia-intuitiva.

# Ripetizioni nella conversazione — 13 ottobre 2026

Esaminati i log del solo processo ALLMA 7065 e gli ultimi messaggi della conversazione `e3008bba-88d0-4fc2-9873-0250e6b81039`. L'archivio personale completo non è stato copiato; la lettura è stata filtrata sulla conversazione richiesta.

Sequenza osservata: saluto, domanda di ALLMA «Come stai?», risposta dell'utente «Bene, tu?», ulteriore domanda «Come ti senti?». Dopo che l'utente segnala di avere già risposto, ALLMA produce nuovamente, identica:

> Ciao! Sto bene, grazie. Il tempo è 20:13, in carica. Come ti senti?

## Evidenze

- Il duplicato esiste nei messaggi persistiti: non è soltanto rendering duplicato nella UI.
- Entrambe le risposte riportano source=model_generated, nuove request_id, seed differenti e una generazione completa. Non risultano risposte servite dal recupero confermato senza modello.
- Per la seconda generazione il log riporta quattro turni inseriti nel contesto; history_turns_removed=0. L'informazione «Bene, tu?» e la risposta precedente erano disponibili. La richiesta attuale viene aggiunta dopo la cronologia.
- La seconda risposta impiega 18,06 s di generazione, TTFT 10,94 s e primo testo visibile circa 16,09 s. La precedente impiega 14,84 s, TTFT 8,94 s e primo testo visibile circa 13,11 s.
- Le due risposte hanno 64 token di ragionamento e 28 di risposta; la fase di ragionamento termina per limite, quella finale con stop. Entrambe vengono marcate valide.
- Il repetition_guard attuale rileva cicli lessicali consecutivi dentro una singola risposta. Non confronta la nuova risposta con quelle dei turni precedenti. La penalità nativa di ripetizione non equivale a un controllo semantico della conversazione.

## Problemi distinti

1. Il modello ripete la stessa domanda dopo che l'utente ha già risposto.
2. Ignora una correzione esplicita dell'utente e riproduce l'intero messaggio precedente.
3. Riparte dal saluto nel mezzo della conversazione.
4. Inserisce orario e stato di carica senza che siano stati chiesti.
5. La validazione non considera questa ripetizione fra turni: lo scambio errato entra nella cronologia come valido, potendo rinforzare il comportamento nelle richieste successive. Non è una prova di modifica dei pesi GGUF o di apprendimento confermato.

La cache del modello ha corrispondenze del prefisso, ma i log mostrano nuova valutazione e generazione: non provano un replay della risposta causato dalla cache.

## Intervento suggerito

Gestire esplicitamente la continuità del dialogo e le correzioni; usare cronologia recente per evitare domande già soddisfatte; aggiungere un controllo conservativo sui duplicati fra turni, rispettando richieste legittime di ripetizione, traduzione e risposte uguali corrette a domande diverse. Un semplice divieto globale di testo uguale sarebbe errato. Contenere la comparsa dei dati tecnici nelle risposte generali. Valutare la comprensione della correzione su casi nuovi senza inserire risposte preconfezionate alla conversazione corrente.

Analisi soltanto: nessuna modifica alla pipeline, al modello o alle memorie effettuata in questo intervento.

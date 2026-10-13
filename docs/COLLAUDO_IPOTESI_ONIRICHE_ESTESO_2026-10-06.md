# Collaudo esteso delle ipotesi oniriche — 6 ottobre 2026

## Risultato

Suite completa finale: **618 passed, 15 skipped, 13 warnings in 52.52s**. Nessun fallimento. Gli avvisi riguardano la deprecazione return_all_scores di transformers; i test saltati restano non verificati. La prima ripetizione della suite esistente aveva dato 606 passed, 15 skipped, 11 warnings in 60.73s.

Aggiunti 12 test permanenti rispetto alla suite precedente, tutti eseguiti con archivi temporanei separati. Nessuna modifica al codice di produzione è stata necessaria in questo collaudo.

## Nuove prove di persistenza e stress

- 300 revisioni distribuite su 12 ipotesi, con riapertura dell’archivio a ogni passo, ritrasmissione di ogni richiesta e controllo della versione utente. Conservati tutti i 300 eventi, revisioni consecutive e integrità SQLite ok. La UI riceve solo gli ultimi cinque eventi per ipotesi.
- 32 client indipendenti su otto thread confermano simultaneamente la stessa ipotesi: una sola revisione e un solo evento, senza duplicazioni.
- Arresto reale di un sottoprocesso dopo la scrittura delle tre tabelle ma prima del commit: nessuna promozione parziale, integrità ok e riprova riuscita.
- Database bloccato da un altro scrittore: errore esplicito, stato invariato e salvataggio riuscito dopo il rilascio del blocco.
- Correzione: il testo precedente non viene più recuperato. Riconferma esplicita: ripristina l’originale. Revoca: esclude il recupero.
- Archivio di 230 ipotesi: le 30 non valutate rimangono in testa anche dopo aver scartato 200 elementi; nessun record perso per il limite di visualizzazione.

## Ponte WebView / Python

Eseguito il callback reale di ChatView senza avviare Kivy. Verificati identità fissata alla sessione, ordine salvataggio→lettura→conferma, errori del core, archivio indisponibile, salvataggio riuscito seguito da errore di lettura e codifica JSON di testo potenzialmente eseguibile. Non viene restituito un falso successo o esposto il dettaglio degli errori interni.

## Interfaccia

**42 controlli web superati** nel browser su DOM e funzioni di produzione, con ponte simulato e dati sintetici. Oltre ai controlli precedenti: riconferma dell’originale esplicita, cronologia come testo sicuro, correzione vuota bloccata, Unicode e nota conservati, doppia revisione bloccata, bozza preservata dopo conflitto, riprova con revisione aggiornata, bozza eliminata solo dopo salvataggio e stato vuoto senza azioni residue. Screenshot e output test salvati negli artefatti.

## Telefono e APK

Samsung SM_S938B, processo ALLMA PID 13836. Nei log di avvio e nella successiva lettura non sono comparsi Traceback, FATAL EXCEPTION, Uncaught o errori SQLite. La scansione dei log non equivale a un collaudo completo delle azioni dell’app.

Il nuovo archivio dream_journal.json.reviews.db esiste sul dispositivo. Copia locale autorizzata esplicitamente dall’utente: apertura in sola lettura, PRAGMA integrity_check = ok, presenti le tre tabelle previste, zero ipotesi, zero revisioni e zero eventi orfani. L’archivio è ancora vuoto: non dimostra un ciclo onirico completo né una revisione manuale sul telefono. Non sono stati inseriti dati di prova nella memoria reale. La copia è conservata localmente negli artefatti con permessi 0600.

APK verificata nuovamente: payload_matches=true, arm64-v8a, KivyMD 1.2.0. SHA-256 20de5df28fe4e3421f56f35166d8cf11443ded67bcaae264607077e9c8f2f1c0. È la build già installata: i nuovi file di test non richiedono un’altra installazione. Nessun cambio al modello o alla visione.

## Limiti

Restano da collaudare sul telefono un ciclo onirico reale, conferma/correzione/revoca tramite la UI Android e il relativo effetto sulle risposte del modello. Nessuna nuova misura di temperatura, consumo o qualità generale. I risultati automatici non dimostrano veridicità delle ipotesi, apprendimento nei pesi del modello o operatività universale di tutti i moduli.

Modifiche ai test e report salvati localmente, nessun commit o push. Artefatti: /Users/erikahu/ALLMA/analisi/2026-10-06/collaudo-ipotesi-oniriche-esteso.

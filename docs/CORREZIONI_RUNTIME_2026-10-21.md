# Consegna dell'iniziativa e validità dei sensori

Questa modifica affronta F01 e F02 dell'audit del 21 ottobre. Non interviene
sui pesi del modello, sulla crescita dell'archivio o sugli altri difetti F03–F18.

## F01 — Un messaggio deve essere conservato prima di proporlo all'interfaccia

Il messaggio e il suo identificatore sono ora scritti nell'archivio della
conversazione prima del callback. Se il disco non accetta la scrittura,
il callback non viene eseguito. Non esiste un secondo archivio dei testi.

Una consegna interrotta rimane `pending`. Un controllo successivo può riproporre
lo stesso record entro la finestra di sei ore, senza chiamare nuovamente il
modello. Consenso, utente, primo piano e concorrenza con il turno restano
vincolanti; una dipendenza onirica modificata annulla la bozza.

Le bozze non consegnate non entrano nella cronologia usata per rispondere,
nell'indice dei ricordi o nei log di conversazione visibili. Dopo l'accettazione
del callback, lo stato diventa `queued` e il record entra nel recupero.
I messaggi precedenti, privi di questo nuovo campo, rimangono leggibili.

`queued` significa accettato dal collegamento all'interfaccia: non certifica
che JavaScript abbia completato il disegno o che l'utente abbia letto il testo.
La deduplicazione dell'interfaccia protegge le ripetizioni nella stessa sessione;
non è una garanzia di presentazione esattamente una volta attraverso qualsiasi
arresto del processo. L'archivio conserva comunque un unico record identificato.

Un evento sul bus richiede il controllo governato dell'iniziativa: non può
inviare direttamente un testo aggirando consenso e salvataggio.

## F02 — Un vecchio valore non diventa una nuova misura

Ogni lettura energetica dichiara provenienza, validità e istante monotono.
Un errore Android conserva i valori precedenti soltanto per diagnosi, marcandoli
non validi e senza aggiornarne l'età. Per il lavoro opzionale il campione deve
essere valido, non futuro e vecchio al massimo dieci secondi.

Il monitor legge anche il risparmio energetico Android. Sogni, iniziativa e backup
automatici condividono i controlli di ammissione, con le rispettive soglie.
Un errore della lettura RAM non invalida una lettura energetica riuscita.
I backup manuali mantengono il percorso esistente.

In assenza di un sensore desktop implementato, il valore è indisponibile:
non si simula una batteria in carica. L'indisponibilità non equivale a batteria
scarica, quindi non riduce il normale budget delle risposte in primo piano.
L'overdrive non può partire da una lettura vecchia o sconosciuta.

## Verifiche

Evidenze locali: `/Users/erikahu/ALLMA/analisi/2026-10-21/runtime-safety-fixes/`.

- `before`: due difetti riprodotti prima delle correzioni.
- `pending-history-before`: riprodotto il rischio di includere una bozza nella
  cronologia, poi corretto prima della build definitiva.
- `recovery-final`: 251 verifiche mirate superate, con disco indisponibile,
  consegna rifiutata, errore dell'acknowledgement, ricaricamento dell'archivio,
  pausa, consenso revocato, isolamento della chat e sensori simulati.
- `full`: primo controllo generale, 2.123 superati e 15 saltati.
- `full-final`: 2.140 casi sul codice definitivo: 2.124 superati, 15 saltati e
  un errore SQLite di accesso al disco sul Mac quasi pieno. Dopo la rimozione
  di cache di compilazione rigenerabili, lo stesso gruppo di 48 casi è passato
  senza cambiare codice o aspettative. Anche i 37 casi del modulo di recupero
  sono passati. `final-test-verification.json` distingue il primo esito dalla
  ripetizione: 2.125 casi superati dopo verifica, 15 saltati. L'errore originale
  rimane registrato; la ripetizione non dimostra che ogni errore I/O sia escluso.

Queste sono prove software sul Mac con dati sintetici e rete disabilitata.
Non misurano qualità del modello, risparmio percentuale di batteria o riduzione
della temperatura.

## Collaudo Android

La build 102540 (versione 0.9.1) è installata sul dispositivo con aggiornamento
in-place. I dieci moduli Python modificati coincidono byte per byte con i
sorgenti verificati. Avvio, collegamento WebView e arrivo alla chat riusciti;
nessuno dei marcatori tecnici di crash controllati è presente nei log del processo.

La diagnostica integrata ha superato 60 scenari su 60 in 2,25 secondi:
integrazione, recupero, isolamento, ciclo di vita/concorrenza, controlli delle
risposte e persistenza. Usa archivi temporanei e un modello simulato, non i
ricordi personali. La lettura della diagnostica attraverso il nuovo monitor
restituisce una temperatura batteria valida di 36,1 °C.

Questa prova Android conferma avvio e integrazione generale. Le nuove prove
specifiche di consegna proattiva interrotta e sensori guasti sono state eseguite
sul Mac con dipendenze simulate, non riprodotte fisicamente sul telefono.
Evidenze: `android-verification.json`, `android-summary.json`, `android-real-monitor.json`.

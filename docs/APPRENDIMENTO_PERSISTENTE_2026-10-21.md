# Conservazione delle risposte apprese

## Problema affrontato

F05 dell'audit: il vecchio deposito JSON eliminava la prima voce quando
superava 500 risposte, anche se l'utente l'aveva già confermata. La conversazione
originale restava conservata, ma il richiamo immediato poteva andare perso.

Il test `test_production_retains_confirmed_answers_beyond_500_entries` ha
riprodotto il difetto prima delle modifiche. Le evidenze iniziali sono in
`/Users/erikahu/ALLMA/analisi/2026-10-21/learned-answer-storage/before/`.

## Nuovo percorso operativo

Il core usa `answer_recall.db` come unica fonte attiva delle risposte apprese.
La cache conserva al massimo 500 record in RAM; eliminarne uno dalla cache non
lo elimina dal deposito. Il JSON precedente è mantenuto intatto per recupero
e compatibilità, ma non viene usato come alternativa automatica se il database
nuovo è danneggiato. In tal modo una vecchia copia non può riattivare una risposta
successivamente revocata.

- Osservazione e avanzamento del checkpoint di recupero avvengono nella stessa
  transazione SQLite. Un'interruzione non deve contare due volte l'apprendimento.
- Conferme, revoche, attribuzione all'utente e cambiamento della risposta
  conservano i controlli esistenti. Una risposta diversa perde le vecchie conferme.
- Ogni aggiornamento legge e modifica una sola voce, senza riscrivere tutte
  le risposte. Una revisione persistente invalida anche la cache di un'altra
  istanza che stia leggendo lo stesso deposito.
- La migrazione valida tutto il vecchio stato prima di pubblicare il nuovo
  file. Il checkpoint e ogni record migrano insieme; un errore non modifica
  l'originale e non pubblica un archivio parziale.
- Un archivio mancante o danneggiato richiede recupero. Il richiamo automatico
  si disabilita e il percorso ordinario può continuare a usare il modello.
- Backup interni, esportazione/ripristino e regole Android includono il nuovo
  deposito e ne controllano integrità, versione e contenuto. Il database non
  viene incluso nel codice dell'APK.

Il costruttore con percorso JSON resta disponibile per compatibilità e test
del formato precedente; il core operativo usa il percorso SQLite.

## Verifiche di crescita sul Mac

Sette inserimenti singoli e venti richiami dalla cache per dimensione; dati
sintetici e nessuna generazione del modello. Sono misure locali, non latenze
Android o percentuali di consumo energetico.

| Voci iniziali | Voci conservate dopo la prova | Inserimento, mediana | Richiamo dalla cache, mediana | Validazione all'avvio |
|---|---|---|---|---|
| 500 | 507 | 0,89 ms | 0,23 ms | 2,13 ms |
| 5.000 | 5.007 | 0,87 ms | 0,26 ms | 17,20 ms |
| 20.000 | 20.007 | 1,00 ms | 0,21 ms | 61,28 ms |

La validazione all'avvio legge ancora tutte le righe in modo progressivo, senza
trattenere in RAM tutti i testi. La prima migrazione JSON deve leggere il vecchio
snapshot. Non si dichiara una conservazione infinita: restano limiti fisici di
disco e dispositivo, oltre ai limiti espliciti del formato di backup.

## Collaudi e limiti

Gli esiti completi sono nei riepiloghi JSON della cartella di evidenza:
`integration-final`, `full-final`, `scale-measurements.json` e i report Android.
La diagnostica contiene «Risposte apprese · 8 scenari», con migrazione oltre
500 voci, cache limitata, revoche/isolamento, scrittura interrotta, migrazione
interrotta, cambio di risposta, backup e corruzione senza ripiego sul vecchio stato.
Usa soltanto archivi temporanei e non chiama il modello.

Questa modifica conserva il richiamo di ciò che è stato confermato. Non aumenta
la conoscenza generale del GGUF, non ne addestra i pesi e non generalizza
automaticamente una risposta a qualsiasi parafrasi. Rimangono separati F03
(salvataggio della cronologia conversazionale) e F04 (ricostruzione dell'indice).

## Incompatibilità Android individuata e corretta

Il primo collaudo ha identificato un rifiuto `PermissionError` (errno 13)
della creazione di hard link nello spazio privato dell’app. Il codice ora
pubblica il file mediante rinomina atomica, sotto blocco `flock` condiviso fra
le aperture del deposito. Il file di coordinamento non contiene dati ed è
escluso da backup e APK. Le prove verificano anche il rifiuto degli hard link,
le aperture concorrenti e un vero arresto del processo prima/dopo la rinomina.
L’impronta dell’archivio originale sul telefono è rimasta identica dopo il
tentativo fallito. Il report Android iniziale è conservato, non cancellato.

## Esito Android finale

Build 102543, versione 0.9.1: tutti gli otto scenari del nuovo deposito sono
passati sul dispositivo in 0,48 secondi; anche i 60 scenari generali di
regressione sono passati, in 2,67 secondi. Queste prove non generano risposte
con il GGUF. Il deposito reale è stato creato, l’impronta del JSON originale
è invariata e i nove componenti controllati sul telefono coincidono con i
sorgenti verificati. Nessun contenuto personale è stato copiato sul Mac.

Verifica finale del codice definitivo sul Mac: 2.154 casi superati e 15
saltati, nessun fallimento nella suite configurata (2.169 casi raccolti).
Il controllo mirato di compatibilità e recupero conta 254 casi superati.
Modifiche salvate localmente; nessun nuovo commit o caricamento GitHub in questo intervento.

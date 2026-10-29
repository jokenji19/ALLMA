# Controlli a riposo e pausa — 24 ottobre 2026

## Cambiamenti della build 102551

Il controllo dell'iniziativa usa ora un riepilogo transitorio della cronologia
validata: ultimo messaggio utente per data, data dell'ultima iniziativa e ultimo
messaggio ancora da consegnare nell'ordine dell'archivio. La prima consultazione
attraversa una volta i messaggi; le consultazioni successive della stessa fonte
non rileggono le pagine.

La riutilizzazione è ammessa soltanto per la cronologia canonica senza modifiche
in attesa. Ogni accesso controlla sul disco la generazione corrente. Anche la
firma dei file SQLite e WAL partecipa alla chiave, per rilevare scritture esterne
che non abbiano rispettato il protocollo della generazione. Le letture di questa
firma e del contatore sono lavoro costante rispetto al numero dei messaggi.

Correzioni, cancellazioni, cambi del proprietario, riordinamenti, modifiche dei
metadati, ricaricamenti, scadenze e arretramenti dell'orologio invalidano il
riepilogo. Un archivio non leggibile non può essere mascherato da una cache valida.
L'aggiornamento della fonte da un altro scrittore richiede prima un ricaricamento,
come negli altri lettori della cronologia.

Il riepilogo conserva al massimo otto utenti e due riferimenti a messaggi per
utente. Non crea un nuovo archivio persistente, non aggiunge colonne o indici
alla cronologia e non limita la storia consultabile. Un ricaricamento riuscito
rimuove i riferimenti alla generazione precedente. Gli adattatori precedenti
senza cronologia canonica usano la scansione singola senza riutilizzare il risultato.

Le consegne pendenti continuano a essere recuperabili senza modello. Una revoca,
invalidazione o sostituzione impedisce di riproporre il messaggio. La scadenza di
un candidato non deve nascondere un'altra consegna ancora valida. Il salvataggio
canonico aggiorna già l'indice: il successivo aggiornamento duplicato è ora
riservato al lettore precedente che ne ha ancora bisogno.

## Salvataggio dell'apprendimento in pausa

Le API che modificano l'apprendimento salvano sincronicamente prima di terminare
e annullano le modifiche in RAM se il salvataggio fallisce. Il passaggio in
background usa ora `flush_state`: acquisisce lo stesso lock e attende eventuali
commit in corso, senza riserializzare e riscrivere una copia già confermata.
Il normale salvataggio della cronologia resta nel percorso della pausa.

Non è stato introdotto un salvataggio differito in background. Un archivio che
non si è potuto caricare resta un errore anche durante il flush. Le modifiche
manuali agli oggetti esportati richiedono ancora una chiamata esplicita a
`save_state`, che conserva il comportamento precedente.

## Misure riproducibili

Il confronto usa componenti e dati sintetici sul Mac, senza GGUF. Non misura la
latenza dell'intera app, i consumi o la temperatura. Il caso di iniziativa conclude
`model_unavailable` in entrambi i programmi: non è stata eliminata una generazione
per ottenere il risultato.

| Operazione | Prima | Dopo |
|---|---:|---:|
| Primo controllo su 800 messaggi: righe decodificate | 2.400 | 800 |
| Secondo e terzo controllo, fonte invariata: righe ciascuno | 2.400 | 0 |
| Totale di tre controlli: righe | 7.200 | 800 |
| Tre pause su 800 argomenti: riscritture del JSON di apprendimento | 3 | 0 |
| Byte riscritti nel JSON nelle tre pause | 6.140.820 | 0 |

Nel campione, il primo controllo passa da circa 35–37 ms a circa 13 ms; i due
controlli successivi richiedono circa 0,13–0,15 ms. La parte di pausa misurata con
gli altri sottosistemi sostituiti passa da circa 24–29 ms a circa 0,07–0,11 ms.
Sono tre campioni di componente, non stime del risparmio sull'intero telefono.

Evidenze: `/Users/erikahu/ALLMA/analisi/2026-10-24/idle-work/`.
`measure.py`, `before.json`, `after.json` e `comparison.json` conservano operazioni,
esiti e misure. `baseline-102550-code.zip` conserva quattro sorgenti applicativi
precedenti, copiati dal telefono senza dati personali. La prima prova mirata ha rilevato un'aspettativa errata della fixture:
il nuovo messaggio aveva una data reale precedente ai messaggi sintetici fissati
a mezzogiorno. La fixture ora assegna una data esplicita successiva; la scelta per
data non è stata sostituita con una scelta per posizione. Il primo risultato è
conservato in `targeted/`; le successive 198 prove sono passate in `targeted-final/`.

| Verifica locale conclusa | Esito |
|---|---:|
| Suite completa offline | 2.334 superati, 15 saltati, zero fallimenti su 2.349 raccolti |
| Prove mirate di integrazione | 198/198 |
| Verifica finale dei riepiloghi e della pausa, inclusa una scrittura WAL senza variazione del file principale | 38/38 |
| Pacchetto Android | Verificato, build 102551 installata |
| Android, lavoro a riposo | 12/12 |
| Android, regressioni generali | 60/60 |
| Android, pausa e rientro reali | Salvataggio completato, stessa istanza ripresa, zero nuovi errori |

Le prove mirate si sovrappongono alla suite; i conteggi non si sommano per stimare
una percentuale generale di affidabilità. Il collaudo del telefono è stato
completato il 24 ottobre 2026: nove sorgenti installati corrispondono alle impronte
del pacchetto, entrambi i report sono completi e privi di fallimenti. Il controllo
reale della pausa è stato eseguito con la chat inattiva e senza bozze, leggendo
soltanto marcatori tecnici; il salvataggio precede il rientro nello stesso processo.
Non sono stati esportati o ripristinati archivi personali.

## Limiti che restano

Aggiornamento: la successiva build 102552 introduce il database incrementale
dell'apprendimento; vedere [il relativo rapporto](APPRENDIMENTO_INCREMENTALE_2026-10-24.md).
La descrizione seguente conserva il perimetro della 102551.

Dopo una modifica della fonte, la prima ricostruzione del riepilogo costa ancora
una scansione completa. Gli aggiornamenti dell'apprendimento continuano a
riscrivere il JSON completo; questa modifica elimina la riscrittura ridondante
in pausa, non introduce ancora la persistenza incrementale di tutti gli argomenti.
Se un aggiornamento è in corso, la pausa attende il suo commit: quel tempo non
può essere dichiarato nullo.

I controlli di consenso, primo piano, attività, energia, temperatura e cancellazione
restano nel percorso dell'iniziativa. Il collaudo sintetico non misura la voce,
la qualità del modello o sessioni reali di anni. Le modifiche restano locali e
non sono state pubblicate su GitHub con questo intervento.

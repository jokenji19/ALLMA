# Coerenza della memoria e letture concorrenti — 22 ottobre 2026

## Problemi affrontati

Questo intervento riguarda A01 e A02 della revisione aggiornata. Non completa
le altre voci dell'audit e non cambia i pesi del modello linguistico.

La cronologia SQLite era già la fonte autorevole. La ricerca semantica conservava
però copie vecchie dopo alcune correzioni, invalidazioni, cancellazioni e modifiche
del proprietario. Inoltre un iteratore paginato sospeso lasciava aperta una lettura
SQLite: un salvataggio sovrapposto poteva attendere circa cinque secondi e fallire.
Nel caso alternativo con WAL la scrittura riusciva, ma il vecchio iteratore poteva
ripopolare la cache con posizioni precedenti a un riordinamento.

Le regressioni congelate prima della correzione hanno raccolto 19 casi:
17 fallimenti e 2 successi. Evidenze locali:
`/Users/erikahu/ALLMA/analisi/2026-10-22/memory-coherence/before/`.
L'archivio `baseline-102547-brain.zip` conserva i sorgenti applicativi precedenti.

## Proiezione di ricerca ricostruibile

- Ogni messaggio della cronologia usa una chiave di fonte stabile, separata dal
  contenuto: `history-message-v1:` seguito dal token già presente nell'archivio.
  Correggere il testo non crea una seconda identità del ricordo.
- Il salvataggio conferma prima la cronologia; poi aggiorna l'indice con le sole
  fonti modificate o rimosse. Una modifica del proprietario ritira anche la copia
  associata al proprietario precedente.
- La riconciliazione completa all'avvio usa la stessa validazione progressiva
  dell'intero archivio. Ritira le fonti assenti e i duplicati riconoscibili dal
  protocollo esatto della vecchia proiezione. Conserva le memorie anonime e quelle
  prodotte da altri domini.
- Le operazioni derivate sono transazionali. Un guasto dell'indice non annulla un
  messaggio già salvato nella cronologia. La proiezione viene segnata da riparare;
  il recupero avviene alla ricerca successiva o al riavvio. Se il guasto persiste,
  il percorso non usa copie obsolete come prova autobiografica.
- Il controllo della generazione della fonte avviene dopo aver riservato la
  scrittura dell'indice: una sincronizzazione vecchia e ritardata non può
  sovrascrivere la proiezione di un salvataggio più recente.
- Il recupero operativo verifica i candidati contro una breve fotografia della
  cronologia corrente: token, proprietario, ruolo, validità, visibilità, testo e
  data. I metadati pubblicati provengono dalla fonte autorevole. Un vettore
  estraneo non diventa un'esperienza dell'utente solo perché contiene una frase
  somigliante.

Un'incoerenza rilevata nel contenuto derivato viene esclusa dalla risposta corrente
e causa una riparazione al recupero successivo; non viene eseguita una seconda
generazione del modello. Le modifiche non salvate devono prima essere confermate.
Un proprietario storico ambiguo non viene indovinato.

Non è stato introdotto un nuovo archivio autorevole né cambiato lo schema della
cronologia. L'indice resta ricostruibile. L'eventuale interruzione fra commit della
fonte e sincronizzazione viene recuperata dalla riconciliazione iniziale.

## Letture paginate e scritture

Le scansioni leggono pagine di 64 righe mediante posizione. Ogni connessione e
transazione di pagina viene chiusa prima di consegnare gli elementi al chiamante:
un iteratore sospeso non conserva quindi quel blocco SQLite.

Il lettore congela la generazione dell'archivio e l'epoca della collezione. Dopo
inserimenti, rimozioni, riordinamenti, commit o ricaricamenti incompatibili, la
prosecuzione del vecchio iteratore solleva un errore esplicito che richiede di
riavviare la lettura. Il controllo precede la pubblicazione delle posizioni nella
cache. Non vengono mescolate due generazioni della storia e non viene promessa
la prosecuzione trasparente di un iteratore attraverso una mutazione.

Restano pagine di 64 elementi, cache di 128 e conservazione degli oggetti
modificati fino al commit. Le modifiche strutturali esplicite possono ancora
materializzare la collezione fino al salvataggio. Il journal di produzione non
è stato cambiato come scorciatoia per risolvere il problema.

## Verifiche e misure

Prima della compilazione sono passate 65 prove mirate finali, comprese due prove
del percorso completo del core: un candidato privo di fonte non entra nel prompt;
un testo corretto sostituisce quello precedente. Sei vecchie fixture del core
sono state aggiornate per creare fonti canoniche reali invece di candidati
inventati nell'indice; le loro asserzioni sul comportamento sono conservate.

La suite completa ha raccolto 2.283 test: **2.268 superati, 15 saltati, zero
fallimenti**. Download e rete esterna disabilitati, cache dei modelli isolata.
Questi numeri riguardano il software verificato, non un punteggio generale
d'intelligenza o affidabilità.

Il primo tentativo Android sulla 102548 ha scoperto un errore del banco di prova:
due gruppi usavano lo stesso nome di cartella temporanea, `revocation`. I test dei
singoli casi passavano ma non percorrevano il runner condiviso. Il nome è ora
univoco e una nuova regressione esegue l'intera batteria come sul telefono.
Le **39 prove mirate successive** passano: 38 casi singoli e un'esecuzione completa
del runner. Il primo esito fallito è conservato in `android-first-attempt-102548/`.

La build finale è la **102549**, versione pubblica invariata **0.9.1**. Il collaudo
è stato completato sul Samsung SM-S938B il **24 ottobre 2026**:

| Batteria nel runtime Python Android | Esito |
|---|---:|
| Memoria e coerenza: cronologia, indice, paginazione, fonti e avvio | 38/38 |
| Controlli generali: integrazione, recupero guasti, isolamento, ciclo di vita, controlli dell'output e persistenza | 60/60 |

Entrambi i report sono completi e non contengono fallimenti. Le batterie hanno
usato archivi temporanei e modelli/iteratori simulati, senza conversazioni
personali. Il 100% indica il superamento di questi scenari fissi; non rappresenta
una stima generale di affidabilità o di qualità delle risposte del GGUF.
Gli otto sorgenti applicativi controllati corrispondono alle impronte della build.

I risultati si trovano in `android-summary.json`, `android-results.json`,
`android-regression/android-summary.json` e `android-regression/android-results.json`
della cartella di evidenze. La verifica dell'APK e le impronte installate restano
registrate separatamente. Nessuna nuova modifica applicativa è stata necessaria
durante questo collaudo finale.

Confronto di avvio del solo componente sul Mac, dati sintetici e indice già
presente, mediana di tre campioni:

| Archivio | Prima, ms | Dopo, ms |
|---|---:|---:|
| 1.000 messaggi, proprietario esplicito | 13,90 | 13,75 |
| 20.000 messaggi, proprietario esplicito | 223,27 | 221,85 |
| 4.000 messaggi, 1.000 conversazioni, proprietario esplicito | 48,01 | 48,43 |
| 2.000 messaggi, 200 conversazioni, proprietario storico da risolvere | 28,11 | 27,80 |
| 4.000 messaggi, 1.000 conversazioni, proprietario storico da risolvere | 57,10 | 58,37 |

Il tempo resta sostanzialmente invariato in questo campione; non viene dedotto un
miglioramento significativo della velocità. Il beneficio verificato è la coerenza
del recupero e l'eliminazione della transazione mantenuta dal lettore sospeso.
Non sono misurati qui batteria, temperatura, qualità del GGUF o durata per anni.

## Limiti e lavoro successivo

L'avvio verifica ancora tutte le righe, pur senza trattenerle tutte in RAM. Una
modifica della proprietà di conversazioni storiche senza proprietario esplicito
può richiedere la riconciliazione completa. Una modifica o rimozione dell'indice
può richiedere la ricostruzione della sua struttura di ricerca in RAM.

La verifica delle fonti riguarda il recupero di dichiarazioni autobiografiche
dell'utente. Non cancella retroattivamente ogni effetto appreso nella personalità,
né modifica le copie di backup precedenti. Revoca della fonte, revisione degli
effetti appresi e conservazione dei backup restano responsabilità distinte.

Restano nell'audit le scansioni periodiche dell'iniziativa, le preferenze operative
escluse dal backup, la percezione e le lingue, il bilancio delle risorse e gli altri
rischi elencati. Tutte le modifiche sono locali; questo intervento non pubblica
commit, push o release.

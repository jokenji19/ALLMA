# Memoria, apprendimento e recupero — 17 ottobre 2026

ALLMA ora recupera alcune parafrasi funzionali che prima perdeva e può completare al riavvio gli aggiornamenti interrotti, senza contare nuovamente la stessa esperienza. La build **102509**, versione 0.9.0.0, è installata sul Samsung SM-S938B. La nuova diagnostica Android ha completato **16/16 scenari in 4,01 secondi**.

## Che cosa cambia nell’uso

- Se hai detto «L’ombrello è nell’armadio», una richiesta come «Dove ho messo ciò che uso per ripararmi dalla pioggia?» può recuperare quella dichiarazione originale. Il recupero mantiene proprietario, ruolo e provenienza; una corrispondenza non diventa una verità verificata.
- «Dove ho messo quella cosa?» resta una richiesta insufficiente: il nuovo percorso non sceglie un oggetto soltanto perché esiste un ricordo disponibile. Più fonti compatibili rimangono disponibili, senza una risoluzione artificiale dell’ambiguità.
- Se ALLMA salva una risposta ammessa ma si interrompe prima di aggiornare un componente, riprende il lavoro mancante al riavvio o all’interazione successiva. Se il componente era già stato aggiornato, il suo punto di avanzamento impedisce il doppio conteggio.
- Lo stesso recupero comprende le esperienze dell’utente che alimentano crescita emotiva, preferenze espressive e riscontri sull’utilità delle risposte. Una preferenza salvata come messaggio può essere recuperata anche se la successiva scrittura della coalescenza fallisce.
- Le risposte respinte e quelle non salvate non alimentano questo apprendimento derivato. Un messaggio dell’utente salvato resta invece una sua esperienza, anche quando la successiva risposta di ALLMA non riesce.

## Ricerca leggera e fonti

La ricerca combina TF-IDF normalizzato con un piccolo lessico esplicito di concetti e descrizioni funzionali. Comprende categorie come ombrello, forbici, torcia, penna, caricatore portatile, termometro, occhiali e bicicletta. Non scarica né carica un altro modello.

L’indice concettuale è ricostruibile dai testi originali in SQLite. I candidati sono filtrati per proprietario, ruolo, validità e revoche prima di applicare il limite dei risultati; le letture vengono suddivise per rispettare anche i limiti SQLite più restrittivi. È disponibile il percorso soltanto lessicale. Il recupero è collegato anche al prompt del core reale, verificato con generazione simulata.

Questo è **un vocabolario delimitato, non una comprensione semantica universale**. Il punteggio di rilevanza non è una probabilità calibrata. Le revoche marcate nei record sono escluse; il sistema di fatti personali mantiene i propri controlli su correzioni, conflitti e fonti. La qualità della risposta formulata dal GGUF rimane una misura distinta.

## Recupero degli aggiornamenti

Gli intenti vengono salvati insieme al messaggio originale nella cronologia canonica. Un giornale SQLite conserva riferimenti, ordine e azioni completate. Ogni componente salva il proprio punto di avanzamento insieme alla modifica; la conoscenza usa una ricevuta nello stesso inserimento SQLite. Un blocco rilasciato dal sistema operativo evita recuperi simultanei dello stesso giornale.

Per le risposte complete e ammesse il percorso comprende AnswerRecall, apprendimento incrementale, conoscenza attribuita, neuroplasticità e stato identitario. Per i messaggi dell’utente comprende la coalescenza. La verifica delle fonti controlla proprietario, conversazione, contenuto e ammissibilità prima di riprendere gli effetti.

Un giornale mancante può essere ricostruito dagli intenti della storia. I vecchi messaggi privi di intento non vengono trasformati retroattivamente in nuove esperienze. Una fonte modificata o cancellata non autorizza un nuovo apprendimento. I punti di recupero malformati non vengono azzerati silenziosamente: la componente interessata richiede recupero e conserva l’originale.

Si tratta di **recupero ordinato degli aggiornamenti**, non di una transazione unica fra tutti gli archivi. Un guasto persistente può lasciare lavoro in attesa, dichiarato nei risultati. Ogni giro esamina al massimo 32 eventi. Non è certificato l’uso di più core indipendenti, ciascuno con la propria copia in RAM, sullo stesso archivio. I percorsi storici e ogni aggiornamento accessorio non sono tutti inclusi nel giornale.

## Misure riproducibili

Confronto con i sorgenti conservati prima dell’intervento, stessi record e stesse richieste:

| Misura sul campione di sviluppo | Prima | Dopo |
|---|---:|---:|
| Ricordo originale al primo posto, 10 parafrasi funzionali | 1/10 | 10/10 |
| Nessuna associazione inventata, 6 richieste senza ancoraggio | 6/6 | 6/6 |

Il recupero delle dieci parafrasi passa dal 10% al 100%, **+90 punti percentuali su questo campione noto**. I casi hanno guidato lo sviluppo: non costituiscono una stima su tutte le possibili conversazioni. [Piano e sorgenti del confronto](/Users/erikahu/ALLMA/analisi/2026-10-17/rafforzamento-memoria/retrieval-plan.json), [risultati completi](/Users/erikahu/ALLMA/analisi/2026-10-17/rafforzamento-memoria/retrieval-results.json).

Tempi indicativi sul Mac, con altre verifiche attive:

| Operazione | Prima | Dopo |
|---|---:|---:|
| Ricerca con indice caldo, 1.001 record, mediana di 30 richieste | 0,89 ms | 1,34 ms |
| Prima ricerca con ricostruzione dello stesso indice | 10,91 ms | 36,23 ms |
| Turno della pipeline con risposta simulata, mediana dopo il primo turno | 17,71 ms | 24,65 ms |

La protezione aggiunge circa 7 ms in questa misura della pipeline. Non è un’accelerazione della generazione. La matrice numerica del campione occupa circa 4 MB in entrambe le versioni; l’indice concettuale aggiunge le proprie strutture Python. La matrice lessicale rimane densa: la crescita verso archivi molto grandi richiede un intervento separato. Questi tempi non dimostrano risparmio di batteria o calore. [Misura dei turni prima](/Users/erikahu/ALLMA/analisi/2026-10-17/rafforzamento-memoria/cost-before.json), [dopo](/Users/erikahu/ALLMA/analisi/2026-10-17/rafforzamento-memoria/cost-after.json).

## Verifiche e consegna

- Diagnostica Android **16/16**: otto scenari di ricerca e otto di recupero. Usa archivi temporanei e un modello simulato; non legge i ricordi personali. [Risultato Android 102509](/Users/erikahu/ALLMA/analisi/2026-10-17/rafforzamento-memoria/android-summary-102509.json).
- I controlli mirati comprendono scritture fallite, interruzioni fra salvataggio e conferma, ordine degli aggiornamenti, ricostruzione del giornale, fonti modificate, utenti separati e punti di avanzamento danneggiati.
- Due test separati terminano un processo con `os._exit`, senza eseguire `close` o `finally`: al riavvio l’apprendimento e l’esperienza emotiva risultano presenti una sola volta. [Verifica finale mirata](/Users/erikahu/ALLMA/analisi/2026-10-17/rafforzamento-memoria/arresto-reale.xml).
- Verifica generale completata: **1.555 test distinti superati, 15 saltati, nessun fallimento**, su 1.570 raccolti. La suite completa è stata eseguita in una copia isolata; le ultime protezioni sui punti di recupero sono state ricontrollate con le prove mirate finali, incluse le due terminazioni improvvise. Il riepilogo unisce gli identificatori, senza sommare le ripetizioni. I 15 test saltati riguardano limiti storici di API/dati e non sono contati come successi. [Riepilogo verificabile](/Users/erikahu/ALLMA/analisi/2026-10-17/rafforzamento-memoria/validation-summary.json).
- La batteria standard invariata continua a superare **60/60 scenari sul Mac**, con i sorgenti finali: [risultato](/Users/erikahu/ALLMA/analisi/2026-10-17/rafforzamento-memoria/operational-mac/summary.json).
- Sintassi Python/JavaScript e controlli dell’interfaccia superati. APK verificata: payload corrispondente, runtime ARM64 e supporto Qwen 3.5. [Controllo APK](/Users/erikahu/ALLMA/analisi/2026-10-17/rafforzamento-memoria/apk-check-102509.json).

APK: [allma_prime-0.9.0.0-arm64-v8a-debug.apk](/Users/erikahu/ALLMA/ALLMA_V4/bin/allma_prime-0.9.0.0-arm64-v8a-debug.apk), build 102509, SHA-256 `a501920bec22438a8721671541b34dbfb3dae630b75409a4d716e3e21a806bca`.

Le modifiche sono salvate localmente e installate sul telefono. Non è stato eseguito un nuovo commit, push o rilascio GitHub in questo intervento.


## Intervento successivo: storie lunghe

Il successivo [collaudo delle storie lunghe](/Users/erikahu/ALLMA/ALLMA_V4/docs/STORIA_LUNGA_2026-10-17.md) sostituisce la matrice densa citata fra i limiti di questo rapporto con un indice sparso, corregge altre interferenze di recupero e aggiunge la build 102510. Le misure sopra descrivono la precedente 102509; i risultati aggiornati sono nel rapporto separato.

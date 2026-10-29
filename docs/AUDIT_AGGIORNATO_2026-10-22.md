# Revisione aggiornata di ALLMA — 22 ottobre 2026

## Perimetro ed esito

Riferimento iniziale: sorgenti locali della build 102547. La revisione ha aggiunto
prove avversarie ai controlli già eseguiti, usando dati sintetici. Le riproduzioni
storiche seguenti sono conservate; l'intervento successivo corregge A01 e A02
nella build 102549; la 102550 completa A04 con le preferenze portabili e la
102551 riduce il lavoro di A03 e la riscrittura in pausa di A09. La 102552 introduce
la persistenza incrementale dell'apprendimento di A09. Dettagli, verifiche e limiti sono in
[Coerenza della memoria](COERENZA_MEMORIA_2026-10-22.md) e
[Backup portabile](BACKUP_PORTABILE_2026-10-24.md) e
[Lavoro a riposo](LAVORO_RIPOSO_2026-10-24.md) e
[Apprendimento incrementale](APPRENDIMENTO_INCREMENTALE_2026-10-24.md). Le altre voci restano
aperte. I risultati non certificano tutti gli interleaving o tutte le risposte
possibili.

| Controllo | Esito |
|---|---|
| Inventario statico dei Python destinati al pacchetto | 224 moduli |
| Raggiungibili dagli ingressi principali tramite import statici | 147; gli altri possono essere strumenti, compatibilità o ingressi alternativi |
| Errori di sintassi | 0 |
| Basi di import locali mancanti sui percorsi statici principali | 0 |
| Import mancante fuori da quei percorsi | `allma_model.data.vocabulary_data`, in `core/vocabulary.py:81` |
| Adattatori registrati provati con quattro scenari sintetici | 9, nessun fallimento; non equivale a eseguire tutti i 224 moduli |
| Suite completa dopo le correzioni A01/A02 | 2.268 superati, 15 saltati, zero fallimenti nei 2.283 casi raccolti |
| Ultima suite completa, configurazione finale della 102550 | 2.297 superati, 15 saltati, zero fallimenti nei 2.312 casi raccolti, il 24 ottobre 2026 |
| Suite completa della 102551 | 2.334 superati, 15 saltati, zero fallimenti nei 2.349 casi raccolti, il 24 ottobre 2026 |
| Collaudo della 102551 | Android: 12/12 scenari a riposo e 60/60 generali; pausa e rientro reali senza errori, il 24 ottobre 2026 |
| Suite completa della 102552 | 2.379 superati, 15 saltati, zero fallimenti nei 2.394 casi raccolti |
| Collaudo della 102552 | Android: 18/18 scenari di apprendimento e 60/60 generali; pausa e riavvio dell'app riusciti |
| Controllo aggiunto dopo l'errore del banco di prova Android | 39/39: casi singoli e runner completo; dettagli nel documento di coerenza |
| Collaudo finale della 102549, completato il 24 ottobre 2026 | Android: 38/38 scenari specifici e 60/60 generali; archivi sintetici, modello simulato, zero fallimenti |
| Collaudo della 102550, completato il 24 ottobre 2026 | Android: 28/28 scenari di conservazione e 60/60 generali; cifratura nativa, archivi sintetici, zero fallimenti |
| Collaudo storico della 102547, prima di questa revisione | Android: 28/28 scenari specifici e 60/60 generali, con dati sintetici e modello simulato |

Le nuove riproduzioni seguenti evidenziano casi non coperti dalla suite. Nessuna
nuova percentuale di affidabilità generale viene dedotta dal numero di test.

Evidenze: `/Users/erikahu/ALLMA/analisi/2026-10-22/audit-followup/`.
File: `static.json`, `runtime-modules.json`, `probe.py`, `probes.json`,
`additional.py`, `additional.json` e relativi log. La prima esecuzione di
`probe.py` si fermava proprio sul blocco SQLite: `probes.log` conserva quel
fallimento; la versione successiva registra anche l'errore e completa gli altri
scenari, senza cambiarne le operazioni.

## Difetti riprodotti e stato degli interventi

### A01 — Cronologia e proiezione di ricerca possono divergere

**Corretto nella 102549:** chiavi stabili, sincronizzazione delle fonti modificate
e ritirate, recupero dei guasti e verifica contro la cronologia corrente prima
dell'uso. Le memorie di altri domini restano distinte. La tabella seguente descrive
la riproduzione precedente alla correzione, conservata come evidenza.

Priorità iniziale alta. La cronologia è autorevole, ma l'indice conservava copie derivate
che non vengono sempre aggiornate o eliminate quando cambia il record sorgente.
La prova passa dal lettore operativo `retrieve_user_memory`, non soltanto da una
query SQL privata. Il modello linguistico non è coinvolto.

| Operazione sulla cronologia sintetica | Vecchio testo ancora restituito prima del ricaricamento | Dopo il ricaricamento |
|---|---|---|
| Correzione del contenuto | sì | sì; vecchia e nuova proiezione convivono |
| `revoked=True` | sì | no |
| `is_valid=False` | sì | sì |
| Cancellazione del messaggio | sì | sì, anche con cronologia ormai vuota |
| Cambio del proprietario da `u` a `v` | sì, a `u` | sì, a `u`, con due proiezioni persistenti |

Il richiamo letterale e altri percorsi che leggono e verificano direttamente la
cronologia possono continuare a funzionare: non dimostrano la sincronizzazione
di questo indice. Nemmeno i test che aggiornano direttamente il database dei
vettori coprono una modifica fatta nel database della cronologia.

Cause principali: la chiave di proiezione dipende da testo/data/ruolo e cambia
quando il testo cambia; `save_memory` conferma la cronologia ma non propaga tutte
le modifiche alla proiezione; la riconciliazione iniziale aggiunge/aggiorna le
fonti visibili ma non ritira tutte quelle precedenti diventate assenti o invalide.

Intervento consigliato: identificatore stabile della fonte, versione e
propagazione recuperabile di aggiunte, modifiche, revoche e rimozioni. Il lettore
deve verificare proprietario e validità della fonte corrente prima di usarla.
I ricordi vettoriali provenienti da altri sottosistemi vanno distinti, evitando
una cancellazione indiscriminata dell'indice. Sono necessarie prove della stessa
istanza e dopo riavvio, compresi guasti tra i due archivi.

Riferimenti: `conversational_memory.py:_message_index_rows`, `save_memory`,
`load_memory`; `agency_system/operational_actions.py:retrieve_user_memory`.

### A02 — Letture paginate aperte e scritture sovrapposte

**Corretto nella 102549:** la lettura di ogni pagina chiude la transazione prima
di restituire gli elementi. Generazione ed epoca invalidano i vecchi iteratori
prima che possano ripubblicare posizioni obsolete in cache. Non è stato cambiato
il journal di produzione. Le riproduzioni seguenti riguardano la 102547.

Priorità iniziale alta. Un iteratore conservava una transazione SQLite di lettura mentre
restituisce le righe al chiamante. La riproduzione non richiede migliaia di turni:
bastano tre messaggi, un iteratore ancora aperto e un nuovo inserimento.

- Modalità attuale: `store_message` fallisce con `database is locked` dopo circa
  5,24 s. Il rollback lascia tre messaggi sia in RAM sia nel database; il quarto
  non risulta salvato. La protezione dalla scrittura parziale funziona.
- Riordinamento durante una lettura ancora aperta: stessa contesa nella modalità
  attuale. L'ordine locale resta una modifica in attesa di un salvataggio riuscito.
- In una seconda prova sintetica con WAL, il commit riesce ma la prosecuzione
  del vecchio iteratore ripopola la cache con posizioni precedenti: cache
  `three, two, three`, database `three, two, one`. Cambiare solo il journal non
  risolve il contratto della cache.

Questa è una fragilità riprodotta dell'interfaccia di memoria; non dimostra che
ogni invio della chat normale fallisca. Intervento: definire vita delle letture,
gestione delle generazioni della cache e invalidazione degli iteratori durante
modifiche strutturali; aggiungere prove di sovrapposizione, cancellazione e
riavvio dei lettori. La scelta del journal deve accompagnare quei controlli.

Riferimenti: `paged_history.py:_row`, `__iter__`, `__reversed__`;
`history_store.py:stream`, `commit`.

### A03 — Scansioni complete nel controllo periodico dell'iniziativa

**Ridotto nella 102551:** un riepilogo limitato a otto utenti richiede una scansione
quando cambia la fonte; non ripete la scansione nei tick della stessa generazione.
Controlla generazione, firma SQLite/WAL, modifiche non salvate, scadenze e orologio.
Su 800 messaggi, tre controlli sintetici decodificano 800 righe invece di 7.200.
La prima ricostruzione dopo una modifica resta proporzionale alla storia; non è
stata introdotta qui una query indicizzata incrementale per ogni evento.

Riproduzione precedente: priorità media per CPU e crescita della storia. In primo piano, con la funzione
abilitata e fuori dalla modalità vocale, il tick è programmato ogni 60 s.
Nella prova con 800 messaggi il ramo che conclude `model_unavailable` ha già
decodificato 2.400 righe: ricerca delle consegne pendenti, ultimo messaggio utente
e controllo del cooldown attraversano l'archivio separatamente.

La misura locale è circa 37 ms per quel campione; non è una misura di batteria
o temperatura Android. Il costo cresce con la storia, anche quando non viene
generata alcuna iniziativa. Intervento: controlli economici anticipati e query o
aggregati mirati per ultimo evento, cooldown e consegne pendenti, aggiornati con
le transazioni. La cache limitata evita di trattenere tutti gli oggetti, ma non
elimina il lavoro delle scansioni.

Riferimenti: `utils/proactive_runtime.py:check_initiative`,
`ui/chat_view.py:_check_proactive_tick`.

### A04 — Preferenze operative escluse dal backup

**Corretto nella 102550:** i due file sono migrati e inclusi nelle copie e nelle
regole Android, con verifica dello schema. Il ripristino su un'altra installazione
conserva la scelta ma richiede un modello presente localmente; un file mancante
porta alla selezione nelle Impostazioni. Il consenso alle notifiche resta distinto
dal permesso del sistema corrente. Le copie precedenti restano importabili.
Verificato su installazioni sintetiche, anche nel runtime Android.

Riproduzione precedente alla correzione, su un backup sintetico valido: `model_binding.json` e
`notifications.json` esistono ma non sono nel manifest. La voce conserva invece
le proprie preferenze nel database dei moduli già incluso.

Intervento: includere le preferenze portabili con schema verificato. La scelta
del modello va risolta rispetto ai file disponibili sul nuovo dispositivo; il
permesso Android delle notifiche va richiesto/verificato nuovamente. La mancanza
di questi due file non implica che il backup perda la cronologia.

Riferimenti: `utils/runtime_storage.py:STATE_FILES`, `utils/state_backup.py:ALLOWED`.

### A05 — Segnali percettivi deboli e integrazione parziale

Riprodotti ancora i casi «Descrivi un fiore colorato» → urgenza media per il
frammento `ora`, e «Non è urgente e non serve rispondere subito» → urgenza alta.
Inoltre l'aggregatore lascia questo risultato in `raw_results` senza tradurlo
in istruzioni o prefissi. La percezione relazionale più recente è invece
collegata: non si conclude che tutta la percezione sia inattiva.

Intervento: confini delle parole, negazioni, soggetto, citazioni, affidabilità e
durata; successivamente un contratto condiviso con il piano del turno. Il
suggerimento attuale di sacrificare completezza per urgenza non va collegato
direttamente senza prima correggere il rilevatore.

Riferimenti: `core/perception_lite.py:_detect_urgency`,
`core/module_orchestrator.py:_merge_intelligent`.

### A06 — Copertura emotiva non uniforme fra lingue

Nelle nuove prove «Sono molto felice» e «I am very happy» producono gioia;
«Estoy muy feliz», «Je suis heureux» e «Ich bin glücklich» non producono una
sfumatura riconosciuta. Il rilevatore restituisce correttamente `uncertain=True`
in questi ultimi casi: non si presenta quel risultato come neutralità certa.

Intervento: copertura dichiarata per lingua, prove di negazione e attribuzione
insieme al lessico e uso prudente del contesto. La disponibilità di una lingua
nel riconoscimento vocale non certifica la stessa copertura emotiva locale.
Il GGUF può comprendere il testo anche quando questo rilevatore non lo comprende.

Riferimento: `emotional_system/emotion_analysis.py`.

## Rischi osservati nel codice e limiti da misurare

### A07 — Risorse del Decider e annullamento nativo

Il decisore viene liberato in vari passaggi, incluso il background, ma non ha
una scadenza di inattività in primo piano. La singola `native.eval(tokens)` viene
controllata prima e dopo: annullare il risultato non equivale a interrompere
immediatamente quella valutazione. Non è stato misurato qui il residuo di CPU
sul telefono e il peso del file non viene equiparato alla RAM usata.

Intervento: bilancio complessivo di modello, decisore, voce e indice; rilascio
adattivo misurato; interruzione nativa o valutazioni suddivise quando compatibili.

### A08 — Possibile doppia costruzione del modello nel recupero dell'import

Nel ramo `ImportError` recuperato, il wrapper costruisce `Llama` e può poi
raggiungere la costruzione ordinaria successiva. È una via del codice con
possibile doppio costo e picco di memoria; questa revisione non ha riprodotto
un arresto Android su quel ramo. Intervento: una sola risoluzione degli import,
una sola costruzione e chiusura esplicita dei candidati falliti.

Riferimento: `llm/mobile_gemma_wrapper.py`, costruzioni attuali alle righe 364 e 476.

### A09 — Altri stati crescono ancora come JSON e salvataggi sincroni in pausa

**Ulteriore intervento nella 102552:** il core salva l'apprendimento in SQLite con
unità, riscontri e progressi separati, aggiornando soltanto le code e i record
interessati. Migrazione immutabile, checkpoint atomico, copie e ripristino sono
verificati anche su Android. Restano la validazione completa al caricamento e
il costo delle copie in RAM delle strutture modificate. Il salvataggio JSON
completo resta soltanto per compatibilità e salvataggi manuali espliciti.

**Intervento parziale nella 102551:** la pausa attende i commit sincroni dell'API
di apprendimento tramite lo stesso lock senza riscrivere un JSON già salvato.
Nel campione di tre pause su 800 argomenti sono evitate tre riscritture da circa
2 MB ciascuna. `save_state` resta disponibile per modifiche manuali esplicite.
Gli aggiornamenti effettivi continuano a scrivere il JSON completo; la migrazione
incrementale di quell'archivio e le attese dei commit restano lavoro da misurare.

Situazione della revisione iniziale, prima di questi interventi: la paginazione
riguardava la cronologia, non tutti i dati del sistema.
`IncrementalLearner.save_state` riserializza conoscenze, riscontri e progressi in
un JSON completo; `on_pause` lo invoca direttamente. Non è una nuova misura di
blocco della UI, ma il lavoro e il suo costo crescono con lo stato appreso.

Intervento: misurare lo stato di apprendimento separatamente, evitare salvataggi
senza modifiche e introdurre persistenza incrementale con lo stesso livello di
rollback e recupero della cronologia. Il passaggio in background richiede una
politica esplicita di completamento, senza perdere modifiche per renderlo veloce.

### A10 — Protezione e conservazione su periodi lunghi

Le copie private restano sul telefono. Proteggono da vari danni locali, ma la
perdita del telefono richiede una copia cifrata salvata separatamente. Il formato
attuale ha limiti espliciti: 512 MiB per file, 2 GiB complessivi e 128 MiB per i
JSON sottoposti a verifica. Sono rifiuti di sicurezza, non eliminazione dei dati.

Intervento: stato delle copie comprensibile, verifica di ripristino indipendente,
avvisi prima dei limiti e un futuro formato versionato a parti per archivi grandi.
Le prove sintetiche attuali non certificano conservazione per anni o millenni.

### A11 — Apprendimento, coalescenza e curiosità hanno un perimetro definito

Sono presenti evoluzione persistente, significati personali, tendenze, riscontri
e correzioni. Lo stile usa assi espliciti; il richiamo confermato usa anche una
chiave di contesto precisa. La curiosità operativa seleziona fra pochi inviti
basati su segnali lessicali. Non addestrano continuamente i pesi GGUF o vocali.

Intervento: misurare trasferimento a nuove parafrasi e contesti, mantenendo la
provenienza; conservare questioni aperte utili collegate alle esperienze e ai
riscontri. La personalità deve poter cambiare gradualmente senza promuovere una
preferenza implicita a fatto certo né copiare ogni umore dell'utente.

### A12 — Voce: copertura e prove prolungate

Il percorso attivo usa STT/TTS dedicati, recupero di sessione, buffer audio
limitato e interruzioni; `VoiceSystem` è un componente precedente e non descrive
da solo la voce attuale. Questa revisione non ha riprodotto una nuova
disconnessione reale e non ne dichiara una inesistente.

Da misurare: sessioni lunghe, interruzioni durante sintesi nativa, chiamate
telefoniche/cambio uscita audio, lingue e servizi Android differenti. La voce
naturale selezionata è italiana; altre lingue dipendono dalla voce Android
disponibile. La percezione cognitiva usa la trascrizione: non è apprendimento
acustico di pronuncia, fonemi o intonazione.

### A13 — Iniziativa in background e vecchio servizio

La proattività corrente richiede primo piano e consenso. Il servizio dichiarato
nella build non ha un avvio trovato nei percorsi ordinari e conserva un modello
fisso Qwen 2.5, percorsi precedenti e un monitor non configurato per Android.
Le notifiche di sistema funzionanti non implicano iniziativa ad app chiusa.

Intervento: mantenere quel servizio fuori dal percorso operativo finché non
condivide archivio, binding e controlli energetici attuali. Un eventuale lavoro
in background va progettato come attivazione leggera, consensuale e limitata.

### A14 — Responsabilità concentrate e componenti precedenti

Il core ha circa 4.000 righe; il bridge circa 1.100. Sono presenti implementazioni
alternative di memoria, personalità, voce e generazione. L'inventario non trova
corpi lunghi esattamente identici, ma ciò non esclude sovrapposizioni funzionali.
L'import del vocabolario mancante è fuori dal grafo statico principale.
`avatar_mesh.js` è ancora impacchettato: 2.069.797 byte e nessun riferimento
nell'HTML corrente, un costo di distribuzione distinto dalla CPU di rendering.

Intervento: registro dello stato dei componenti e separazione graduale di
routing, recupero, prompt, controlli e persistenza. Rimuovere componenti soltanto
dopo aver controllato ingressi dinamici e compatibilità; visione ancora ultima.

### A15 — Test, modelli e release

Le nuove prove per A01/A02 sono state aggiunte; servono ancora casi di dialogo
non usati per tarare i controlli e misure dei rischi restanti.
I test saltati restano nel bilancio; i punteggi software e di qualità del GGUF
restano distinti. Per consumi e temperatura servono misure Android a condizioni
comparabili. Un GGUF nuovo richiede un profilo di compatibilità verificato.

La pipeline pubblica produce APK debug. L'immagine Docker è fissata per digest,
ma `p4a.branch=develop` non fissa la revisione della toolchain. L'impronta di
`build_android_safe.py` non comprende esplicitamente tutti i sorgenti Java,
gli AAR e gli hook nella radice di `libs`. Questo non prova che l'APK installata
sia vecchia: le impronte dei sorgenti della 102547 sono state confrontate.

Intervento: copertura completa degli ingressi, revisioni della toolchain fissate,
percorso di firma/release distinto dal collaudo e prove per capacità del modello.

### A16 — Spazio sul Mac e conservazione delle modifiche

Lettura durante questa revisione: circa 684 MiB liberi sul volume del progetto.
È poco margine per build, copie e ripristini, anche se gli ultimi controlli sono
terminati. Le modifiche applicative degli ultimi interventi sono salvate
localmente e molte non sono ancora in un nuovo commit/push.

Intervento: inventario dello spazio e recupero di margine da artefatti
ricostruibili, conservando dati, copie e release necessarie; poi snapshot Git e
pubblicazione concordati. Questa revisione non elimina file né pubblica modifiche.

## Ordine proposto

1. A01: corretto; mantenere le regressioni su proiezioni e fonti autorevoli.
2. A02: corretto; mantenere le regressioni su lettori sospesi e cache.
3. A04 corretto; A10 ancora aperto per conservazione esterna, grandi archivi e limiti del formato.
4. A03/A09 ridotti nelle 102551/102552; restano la ricostruzione del riepilogo dopo una modifica e i costi di caricamento/copia in RAM dell'apprendimento.
5. A05/A06 e A11: percezione prudente, copertura linguistica e apprendimento
   verificato su contesti nuovi.
6. A07/A08/A12: risorse e cancellazione dei motori con misure Android prolungate.
7. A13–A16: servizio, semplificazione, release e conservazione del progetto.

Lo spazio sul Mac va gestito prima di altre operazioni pesanti. Gli interventi
proposti non richiedono una riscrittura totale o un cambio immediato di modello.

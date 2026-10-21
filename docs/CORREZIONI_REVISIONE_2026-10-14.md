# Correzioni dopo la revisione approfondita — 14 ottobre 2026

Il rapporto iniziale è una fotografia **prima** delle correzioni. Questo documento distingue modifiche implementate, prove e lavoro residuo. Non dichiara tutti i 179 moduli operativi.

## 1. Turni concorrenti — Corretto nel percorso chat

Ammissione seriale nel core, cancellazione dei turni in attesa, rifiuto dopo chiusura; probe e cambio modello condividono il flag di attività.

**Limite o lavoro residuo:** Stress simultaneo su Android ancora da eseguire.

## 2. Aggiunte dopo i controlli — Corretto

Le milestone diventano metadati e non riscrivono la risposta dopo streaming e apprendimento.

**Limite o lavoro residuo:** Il controllo della qualità del modello rimane distinto.

## 3. Caricamento parziale della memoria — Corretto

Snapshot validato prima dello scambio; un caricamento fallito mantiene le collezioni correnti e blocca la sovrascrittura del file fino a un reload riuscito.

**Limite o lavoro residuo:** Il file danneggiato richiede recupero esplicito; non viene cancellato.

## 4. Manutenzione e crescita memoria — Migliorato; migrazione ancora aperta

GC senza LLM: libera solo cache ricostruibili sotto pressione RAM misurata. Nessuna riscrittura di tutti i blob alla ricerca. Duplicati indicizzati senza alterare IDF né forzare rebuild.

**Limite o lavoro residuo:** JSON dello storico ancora riscritto e indice TF-IDF ancora ricostruito: per archivi grandi servono storage incrementale, paginazione e migrazione con rollback.

## 5. Temperature inventate — Corretto nel software

Nessun valore casuale o CPU=batteria+10. Thermal zone selezionata per tipo; valori mancanti sono None con fonte e timestamp.

**Limite o lavoro residuo:** Accessibilità dei sensori da verificare sul dispositivo; alcuni telefoni non espongono CPU.

## 6. Recupero incrementale rotto — Corretto

Supporto ndarray/sparse, vocabolario unico riallineato all’aggiunta di nuovi termini e ricerca attribuita all’utente.

**Limite o lavoro residuo:** Refit cresce con i dati; ottimizzazione su corpus grande ancora da misurare.

## 7. TF-IDF e coordinate incoerenti — Corretto nei percorsi esaminati

IDF con smoothing, righe vuote/invalidi conservate, estrazione topic senza corrompere i topic conosciuti; confronto in coordinate lessicali condivise.

**Limite o lavoro residuo:** Hash lessicale non è comprensione semantica: collisioni possibili, qualità da misurare su casi nuovi.

## 8. Ripetizioni negate autorizzate — Corretto per i casi coperti

Negazioni, citazioni e codice non concedono l’eccezione; richieste affermative esplicite restano consentite.

**Limite o lavoro residuo:** Regola conservativa, non un interprete universale di ogni formulazione.

## 9. Personalità scollegata e falso diario — Migliorato e collegato al feedback

Delta reali nel diario. Adattamento piccolo e limitato dei tratti di risposta da feedback esplicito attribuito; eventi deduplicati e persistiti insieme ai tratti, rollback su errore. Le emozioni dell’utente non fanno crescere automaticamente la personalità.

**Limite o lavoro residuo:** Coefficienti sono una politica sperimentale di controllo, non misure di empatia o intelligenza; utilità da validare longitudinalmente.

## 10. Entropia non utilizzata — Corretto il collegamento

La stima lessicale precedente raggiunge compute_state del turno successivo.

**Limite o lavoro residuo:** È un indicatore di ripetizione lessicale, non una misura di intelligenza o coscienza.

## 11. Sogni revisionati fuori dalla proattività — Collegato e verificato con motore simulato

Solo user_confirmed/user_corrected dello stesso utente. Il prompt può proporre l’ipotesi come ipotesi; revisione cambiata durante inferenza annulla l’invio. Versione salvata per invalidare il contesto dopo revoca. Stessa revisione non proposta due volte.

**Limite o lavoro residuo:** Collaudo con il modello nativo sul telefono ancora da fare.

## 12. Pattern: init, keyword, cosine e RNG — Corretto nei casi riprodotti

Init raggiungibile, keyword conservate dopo alias, cosine matriciale coerente e hashing lessicale senza pseudo-embedding casuali/global RNG.

**Limite o lavoro residuo:** Riconoscimento a regole limitato; non equivale a riconoscere ogni concetto.

## 13. Diagnostica e percentuali fuorvianti — Migliorato il percorso UI

Tolto accesso interaction_metrics inesistente e indicatore di perfezione ricavato dai messaggi; mostra conteggio attribuito. Entropia recente esposta.

**Limite o lavoro residuo:** Metriche sintetiche in altri componenti legacy restano da sostituire; conteggi non sono qualità.

## 14. Lifecycle WebView e bus — Corretto nel software

Timer posseduto e unico, pause/resume/close, distruzione WebView sul thread Android, callback ritardate protette. Bus cancellato torna riavviabile.

**Limite o lavoro residuo:** Pause/resume ripetuti sul dispositivo ancora da collaudare.

## 15. Isolamento per utente — Rafforzato

Nessun fallback all’intera cronologia nel bridge; recupero personale filtrato e nuovi concetti della coalescenza separati per proprietario, senza assegnare arbitrariamente dati legacy.

**Limite o lavoro residuo:** Revisione completa di tutti gli endpoint legacy multiutente e migrazione dei record senza proprietario ancora aperte.

## 16. Componenti alternativi incompleti — Riparati diversi contratti; non tutti operativi

Lock reentranti, working memory con contesto, recall normalizzato, consolidamento verso destinazione esistente, deduplica di oggetti non hashable. Import ALLMACore del backend corretto.

**Limite o lavoro residuo:** Persistenza completa del backend di memoria alternativo, autenticazione Flask e TTS neurale non certificati. Visione rimandata come richiesto; non attivata.

## Altre correzioni riprodotte

- Feedback positivo su confidenza alta non può più produrre un delta negativo.
- Preferenza `style` letta coerentemente e aggiornamenti con `last_updated` richiesto dal database.
- Stile di personalità non fallisce con dizionario emozioni vuoto.
- `Project.from_dict` non modifica il dizionario passato dal chiamante.

## Verifiche

- Primo gruppo: 93 test superati.
- Controllo esteso intermedio: 715 superati, 8 saltati.
- Regressioni dopo collegamento feedback/sogni: 698 superati.
- Ultimi test mirati dopo le riparazioni alle memorie alternative: 126 superati.
- Controllo sintassi Python/JavaScript e `git diff --check` superati.
- Aggiunti **32 casi di regressione** rispetto ai 948 casi della revisione iniziale; il totale configurato ora è 980.
- Un precedente giro completo di questa fase è stato interrotto, senza riepilogo finale; non viene considerato superato. Il giro finale completo è terminato: **965 passed, 15 skipped, 5 warnings in 200.41s (0:03:20)**. Anche la migrazione SQLite passa.

Questi sono giri distinti e sovrapposti: **non sommare i conteggi**. I test nuovi usano dati temporanei e motori/sensori simulati dove dichiarato. Nessuna percentuale di qualità globale è ricavata dai test superati.

## Stato di consegna

Correzioni salvate nel codice locale; nessun commit, push, nuova release o nuova installazione APK in questa fase. Gli archivi personali non sono stati riscritti dai test. Le nuove impostazioni sul telefono richiedono compilazione e collaudo della nuova APK.

Le priorità rimaste sono storage incrementale con migrazione recuperabile, collaudo Android e verifica dei percorsi legacy ancora non canonici. La visione resta ultima.

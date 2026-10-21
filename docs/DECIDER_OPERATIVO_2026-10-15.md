# Decider operativo — 15 ottobre 2026

## Comportamento distribuito nella build 102482

Un solo `DecisionRuntime` condiviso governa le proposte del motore locale nelle parti seguenti:

| Percorso | Effetto operativo | Autorità conservata da ALLMA |
|---|---|---|
| Chat e voce | Instrada la richiesta tra calcolo, memoria, ragionamento e chiarimento | Identità e calcoli esatti restano percorsi del codice, senza inferenza aggiuntiva |
| Recupero dei ricordi | Una scelta sicura di ragionamento generale può evitare recuperi personali non pertinenti | Richieste personali esplicite protette; filtri di utente e provenienza invariati; nessuna risposta dichiarata vera dal punteggio |
| Contesto | Rimuove coppie amministrative non pertinenti dai prompt generali | Non cancella conversazioni, nomi, obiettivi o preferenze; mantiene i turni sostanziali |
| Sogni | Ordina le tre esperienze già ammesse dal sistema onirico | Non aggiunge ricordi, non conferma ipotesi e non amplia il ciclo; revisione utente e limiti energetici restano attivi |
| Iniziativa | Può suggerire di attendere dopo che i controlli di ALLMA sono passati | Non può attivare contatti senza consenso, anticipo temporale, disponibilità energetica e cooldown |

Il servizio è operativo, non un osservatore diagnostico. Non viene consultato per ogni funzione elementare: emozioni, coalescenza, apprendimento, identità, permessi e verifiche certe restano sistemi proprietari di ALLMA. Non introduce azioni esterne o scritture decise liberamente dal modello.

## Ciclo di vita e impostazioni

- Attivo per impostazione iniziale, come richiesto dall’utente; preferenza modificabile in Impostazioni → Decisore locale e salvata nel CognitiveStateStore.
- Caricamento pigro del GGUF verificato; una sola copia operativa residente e riutilizzata tra richieste, senza rileggere il checksum a ogni turno.
- Al massimo una valutazione di instradamento per turno ordinario, una di priorità per ciclo onirico e una di iniziativa dopo i controlli preliminari. Nessun retry automatico della generazione della risposta.
- Soglie di scelta del motore invariate: 0.80 di probabilità, margine 0.20. Non sono una misura universale di affidabilità.
- Astensione, file mancante, modello non disponibile, occupazione o contesto troppo lungo conservano il percorso ordinario. Nessun download nascosto nelle chat.
- Pausa a temperatura batteria ≥42°C; sogni e iniziativa conservano anche i limiti preesistenti più restrittivi.
- Rilascio su opt-out, background, fine del ciclo onirico e chiusura; il trasferimento ad altro modello di chat non modifica l’identità o i dati di ALLMA.
- Le prove isolate del decisore rilasciano prima l’istanza operativa. Il benchmark cognitivo condivide il servizio, senza possederlo o chiuderlo al termine: non carica una seconda copia.
- Le metriche `decision` del turno includono dominio, esito, scelta, probabilità, tempo di inferenza e tempo totale di preparazione. Nessun testo personale viene aggiunto ai log del coordinatore.

## Correzioni della conversazione

- Chiarito nel prompt che le risposte precedenti dell’assistente non costituiscono fonti.
- Aggiunto un controllo lessicale circoscritto per le dichiarazioni di consultazione/verifica esterna non effettuata, sia nel flusso sia nella risposta finale, nell’iniziativa, nelle ipotesi e nel recupero delle risposte apprese.
- Negazioni, citazioni anche incomplete durante lo streaming e codice non sono trattati automaticamente come verifiche effettuate.
- Le risposte generate hanno `factual_status=not_verified`. Superare il controllo strutturale non certifica la verità.
- Una continuazione richiesta non deve ricominciare le prime dieci parole già presenti nella risposta precedente. Il controllo evita questo caso circoscritto; non è un rilevatore universale di parafrasi. Codice recintato e richieste esplicite di riassunto restano distinti.

Non è stato aggiunto un verificatore storico o scientifico universale. Decider può classificare male o astenersi, e Qwen può ancora produrre fatti errati. Nessuna percentuale di incremento dell’intelligenza o di risparmio energetico viene dichiarata.

## Verifica

- Suite ampia: 176 test passati in 430,64 secondi (core, persistenza, crescita emotiva, benchmark, modelli, sogni e qualità).
- Ultima selezione mirata: 106 test passati (servizio operativo, fonti, continuazione, autorità, motore, bridge/assets, sogni e recupero appreso); comprende casi già presenti nella suite ampia, quindi i numeri non vanno sommati.
- Cinque nuovi test nel core hanno verificato instradamento operativo, protezione dei ricordi personali, percorso rapido identitario, blocco delle false fonti e veto dell’iniziativa.
- Sintassi Python e JavaScript verificata.
- Prova nativa sul Mac con il GGUF reale e soli dati sintetici: un percorso memoria accettato, quattro astensioni nei cinque tentativi contestualizzati. Nessuna soglia abbassata per forzare risultati. È evidenza del funzionamento e dei limiti del servizio, non una misura di qualità generale.
- Report nativo: `/Users/erikahu/ALLMA/analisi/2026-10-15/decider/operational-mac.json`. I tempi di quel giro non sono un benchmark di prestazioni: compilazione e suite di test giravano contemporaneamente.

## Build

Prima compilazione fermata da ENOSPC. Rimossi soltanto staging `.buildozer_local/android/app` e intermedi Gradle rigenerabili; conservati modelli, conversazioni, APK precedenti e sorgenti. Compilazione ripetuta, con controllo del payload prima dell’installazione.

### Artefatto verificato

APK 102482; SHA256 `e9c8ae7c931d24e2cf2f9e88bd871da3c314faf0793171c00fc8e8b8e1cd2265`; payload allineato ai sorgenti e runtime ARM64 llama-cpp-python 0.3.36 verificato. Installazione `adb install -r` completata con Success. Il collaudo live dei nuovi percorsi nelle conversazioni Android è distinto dalle precedenti prove native del solo motore.

## Collaudo Android: arcobaleno, due turni

Build 102482, SM-S938B, processo 2097. In entrambi i turni Decider ha selezionato `reason`, evitando il recupero personale non pertinente. Tempo totale del decisore: 6,524 s al primo uso (inferenza 1,189 s; restante preparazione/caricamento), 1,577 s al secondo. Generazione Qwen: 13,311 s e 18,897 s. Somma instradamento + generazione circa 19,84 s e 20,47 s: non è una misura completa della latenza UI. Il primo testo finale arriva 13,325 s e 16,039 s dopo l’instradamento, rispettivamente; il primo turno attende la validazione delle due frasi.

Il vincolo di due frasi è rispettato e il seguito conserva il tema. Nessun crash o errore di caricamento nei log circoscritti. Entrambe le risposte, però, contengono errori scientifici: Qwen attribuisce l’arcobaleno ai gas dell’aria e poi inventa un filtraggio delle lunghezze d’onda da parte dell’aria. La spiegazione deve coinvolgere rifrazione, riflessione interna e dispersione nelle gocce d’acqua. Il seguito propaga quindi una premessa errata della prima risposta. `is_valid=true` indica superamento dei controlli applicati, mentre `factual_status=not_verified` resta corretto. Il ragionamento raggiunge il budget in entrambi i turni; questi due casi non dimostrano che aumentarne il limite correggerebbe gli errori.

Risultato: servizio operativo e continuità osservati; correttezza fattuale insufficiente. Nessuna prova di accelerazione o risparmio energetico rispetto a un controllo senza Decider. Non sono state inserite risposte scientifiche preconfezionate per far passare questa prova. Report: `/Users/erikahu/ALLMA/analisi/2026-10-15/decider/operational-android-rainbow.json`.

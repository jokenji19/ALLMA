# Correzione delle ripetizioni — 12 ottobre 2026

La foto mostra una risposta salvata con molte ripetizioni consecutive di «ghiandole». Correzione generale, senza risposte preimpostate per il caso dei pesci e senza rigenerazione automatica.

- Compatibilità llama.cpp: `repeat_last_n` non è un parametro della chiamata nativa installata. Ora viene applicato attraverso `last_n_tokens_size` sotto il lock di inferenza. Il fallback elimina soltanto il parametro esplicitamente non supportato, mantenendo gli altri. Prima il fallback rimuoveva anche la penalità richiesta; llama.cpp conservava comunque la propria penalità predefinita, quindi non era totalmente disattivata. Penalità generale ora 1.10, finestra 128.
- Rilevamento conservativo di cicli lessicali consecutivi: sei ripetizioni di una parola di almeno tre caratteri, oppure quattro di una sequenza di 2–8 parole. Blocchi di codice, matrici numeriche e ripetizioni richieste esplicitamente con un numero restano consentiti.
- Arresto anticipato e chiusura del generatore. Metadati `finish_reason=repetition`; nessun retry automatico. Il controllo funziona anche su output non streaming. Conteggi dei token retokenizzati includono il testo generato prima del taglio, non soltanto quello conservato.
- La pipeline considera la risposta non valida e restituisce un avviso, evitando apprendimento e conferma nella cache. Anche una vecchia risposta ripetitiva già confermata non viene recuperata dalla cache.
- Le risposte storiche con cicli evidenti sono escluse dal contesto futuro. Nel pannello Memoria compare una segnalazione; il contenuto originale rimane salvato. Non sono stati cancellati archivi personali o pesi del modello.

## Verifica

Suite completa: 645 passed, 15 skipped, 12 warnings, 31.39 secondi. I warning riguardano un parametro deprecato di Transformers. Test nuovi su ciclo della foto, sequenze, contenuti legittimi, compatibilità parametri, arresto/chiusura generatore, streaming, output non streaming, invalidazione nella pipeline, apprendimento, cache precedente e contesto storico. Test automatici con backend simulato; non equivalgono a un benchmark reale del modello.

## Limiti

Questo controllo non è un verificatore scientifico: una risposta senza ripetizioni può ancora essere inesatta. Non elimina ogni forma di ridondanza semantica. Non vengono promessi miglioramenti percentuali di qualità, consumo o temperatura. Il caso reale deve essere riprovato sul telefono dopo l’installazione.

Modifiche salvate localmente; nessun commit o push richiesto per questa correzione.

## APK e prova sul dispositivo

Compilazione e verifica riuscite, payload_matches=true. Installazione `adb install -r`: Success, senza cancellare i dati. Impronta del base.apk installato identica alla build: 3f138f4ecca43479fa39966e2cd6f5ec33af9320163ab33e86216b4f2c70e5ef.

Avvio controllato nei log del solo processo ALLMA PID 28313: WebView caricata, TTS pronto; nessun Traceback/FATAL/Uncaught/[ERROR nella finestra letta. Prima generazione dopo aggiornamento terminata con finish=stop, 180 token, 23.00 secondi; questi dati non costituiscono un confronto prestazionale controllato. Alla ripetizione della domanda «Un pesce può morire senza acqua?» l’utente conferma «risposta corretta». Nessuna verifica indipendente del testo integrale: conferma manuale dell’utente e log di completamento.

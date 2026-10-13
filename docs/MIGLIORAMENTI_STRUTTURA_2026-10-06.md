# Miglioramenti strutturali ALLMA — 6 ottobre 2026

Questo intervento mantiene il modello GGUF e l'identità nominale ALLMA. Non addestra i pesi e non inventa una storia personale.

## Cambiamenti

- **Recupero appreso:** validazione dello schema e dei singoli record; record validi conservati, dati illeggibili salvati in `.invalid.bak` prima di nuove scritture. Restano necessarie due conferme esplicite distinte per il recupero senza modello.
- **Stato cognitivo:** maturità, stabilità, conflitti e regole neuroplastiche persistono in `cognitive_state.json` accanto al database principale. Sezioni indipendenti, valori numerici validati, scrittura atomica e isolamento tra directory di stato. Umore ed entropia della sessione rimangono transitori.
- **Coalescenza:** la classe locale `KnowledgeMemory` nascondeva quella SQLite e teneva i concetti in RAM. Rinominata la classe storica e collegata la coalescenza al database principale con API per i concetti. Eventuali database legacy sono importati una sola volta senza rimuovere l'originale. I concetti generati non diventano automaticamente conoscenza verificata.
- **Personalità e diario:** ripristino dei tratti, forza dei valori, bonus di resilienza e diario; diario nella directory persistente con scrittura atomica. Eliminata la seconda aggiunta della stessa voce. Non è possibile recuperare retroattivamente lo stato già perduto dalla vecchia RAM.
- **Contesto:** il wrapper rispetta `n_ctx`; conteggio con il tokenizer effettivo e rimozione dei turni storici più vecchi per riservare spazio alla generazione. Domanda attuale e istruzioni di sistema non vengono tagliate; un input che da solo supera il limite produce un errore controllato. Le richieste esplicite di dimostrazione possono avere 192 token di ragionamento su 512 totali, mantenendo una riserva per la risposta. Riconosciute anche «in dettaglio» e «passo per passo».
- **Lavori in background:** manutenzione e sogni richiedono alimentazione, energia almeno 72%, temperatura valida e non oltre 40 °C. La cancellazione cooperativa interviene per attività utente, chiusura o perdita dei requisiti energetici. Il controllo dei sensori durante la generazione è limitato a una volta al secondo.
- **Cronologia:** l'estrazione periodica usa soltanto messaggi dell'utente, conserva soltanto citazioni presenti nel testo e non sovrascrive fatti già presenti. Non cancella più conversazioni sulla base di un riassunto lossy. Questa scelta protegge la memoria ma non risolve la crescita del corpus: serve un archivio separato prima di reintrodurre rimozioni.
- **Duplicazioni:** nella pipeline principale il pulse legacy esegue soltanto il contesto sociale effettivamente utilizzato. Curiosità, metacognizione, creatività e meta-apprendimento legacy non producono più elaborazioni ignorate in parallelo ai moduli moderni. L'API completa rimane disponibile per altri chiamanti.
- **Sogni:** checkpoint persistente delle ultime 1.000 evidenze elaborate, separato per utente tramite chiave; successo soltanto dopo generazione e salvataggio delle ipotesi. Fallimenti e cancellazioni restano riprovabili. Ipotesi ancora non verificate, nessuna conferma automatica dell'apprendimento.
- **Visione:** senza VLM comunica l'indisponibilità direttamente, senza descrizioni simulate dal nome del file e senza passare una falsa osservazione al modello testuale.

## Limiti e attività successive

La persistenza copre i campi elencati, non ogni oggetto temporaneo del sistema. Non sono migrabili ricordi che non erano mai stati salvati. I sogni hanno una coda persistente, ma manca ancora un'interfaccia completa di revisione e verifica delle ipotesi. Non è stata eseguita una riorganizzazione generale dei 162 moduli di produzione: preservate le API e ridotta una duplicazione misurabile nel flusso principale.

La manutenzione e i sogni condividono criteri di priorità e il lock del wrapper, non un nuovo scheduler centralizzato. La cancellazione Python non può garantire l'interruzione immediata del prefill nativo. Cache e indice TF-IDF richiedono ancora misure su corpus grandi. Non sono dichiarati incrementi percentuali di velocità, qualità o autonomia senza un confronto sul dispositivo.

## Verifica

- Suite completa: **553 passed, 15 skipped**, 13 warning di dipendenze, nessun test fallito (48,52 s). Nessuno dei test saltati è conteggiato come superato.
- Verificate persistenza dopo riavvio, isolamento, schema corrotto, errore di scrittura atomica, importazione legacy idempotente, cancellazione, evidenza conservata, contesto e rimozione dei soli duplicati legacy; anche checkpoint dei sogni con riavvio e tentativi falliti.
- 11 file critici del payload confrontati byte per byte con i sorgenti; sintassi Python valida.
- Build Android completata; APK verificata per payload corrente, KivyMD 1.2.0 e librerie native ARM64.
- SHA256 APK: `af36471402f96f67bfb826ed337cf7d1ba1a4039af060216a8f9b79320625988`.
- Installazione aggiornamento su Samsung SM-S938B: `adb install -r` riuscita, senza disinstallazione o cancellazione dati.
- Log e verifica pacchetto in `/Users/erikahu/ALLMA/analisi/2026-10-06/miglioramenti-struttura`.
- Non eseguito un nuovo benchmark fisico di qualità, latenza, temperatura o batteria.

Avvio Android verificato nei log del processo 8307: coalescenza attivata, orchestratore con nove moduli, WebView e bridge caricati, TTS ready; nessun traceback Python o errore di inizializzazione rilevato nella finestra acquisita. Presenti warning della dipendenza requests e messaggi del driver Adreno sulla compilazione shader: il controllo di avvio non equivale a un collaudo grafico completo o a una prova di inferenza.

Il controllo di avvio precede la ricompilazione finale, che differisce soltanto per la rimozione di uno spazio finale nel sorgente. `git diff --check` finale superato.

# Decisore locale e ciclo agentico — 15 ottobre 2026

## Obiettivo
Separare identità/storia (ALLMA), ragionamento (modello di chat) e scelta/esecuzione/verifica delle azioni. Il motore decisionale è sostituibile.

## Implementato
- LocalDecisionEngine: Decider-0.8B Q4_K_M, 529297504 byte, revisione GGUF `48c1a1dfb87edda1fff62c037cf3cf559f6dbafd`, SHA256 `5cb5d042a236add5cde5459f8e8b8f8f80161ad4a1779a49377b70a64eb7b11a`. Conversione di terzi, non un rilascio GGUF dell’autore Mapika.
- Pesi locali verificati con dimensione e SHA256; nessuna libreria torch/transformers richiesta dal percorso di inferenza. Licenza Apache 2.0 inclusa.
- Prompt state-first in due segmenti, senza chat template; logits nativi delle lettere, temperatura upstream 1.03; massimo 8 opzioni, contesto 1024, niente generazione.
- Soglie sperimentali: probabilità ≥0.80 e margine ≥0.20, non una garanzia statistica né calibrazione italiana. Astensione esplicita.
- Stato nativo azzerato tra richieste, accesso esclusivo, gestione cancellazione prima/dopo eval, close idempotente. L’inferenza già in corso termina prima di scartare il risultato.
- ActionCycle: registro di strumenti del chiamante, argomenti chiusi nel codice, permessi, massimo 4 passi, azioni senza ripetizione, verifica esterna dell’osservazione. Nessun retry implicito o autoconferma.
- Integrazione Android via Diagnostica → Decisore sperimentale; download esplicito e verificato al primo avvio se il file non è già presente. Cancella trasferimento al successivo chunk; attesa rete limitata dal downloader.
- Blocco durante chat/sogni/cambio modello e sospensione a batteria ≥42°C prima dell’inferenza successiva. Il modello viene rilasciato alla fine.
- Separato dal catalogo dei modelli conversazionali. Nessuna attivazione nelle chat e nessuna modifica alla memoria personale.

## Verifica sul Mac
30 test software passati (20 nuovi; asset web, bridge benchmark e cambio modello inclusi). Ambiente nativo temporaneo `/private/tmp/allma-decider-venv`, llama-cpp-python 0.3.36.
Otto richieste sintetiche, quattro inglesi e quattro italiane. Sei scelte accettate corrette, zero scelte accettate errate, due astensioni; il primo candidato era quello atteso in tutti e otto. Campione molto piccolo: non è una misura di affidabilità generale.
Tempo mediano delle decisioni brevi: 382 ms sul Mac; non confrontabile con Android né con il tempo di una risposta completa.
Due cicli con strumenti sintetici: calcolo selezionato/eseguito/verificato; recupero del nome dalla memoria sintetica non eseguito, perché il modello ha selezionato stop. Questo fallimento resta nel report e impedisce di presentare l’esperimento come pronto a governare le chat.

## Limiti e passo successivo
Supporto dichiarato dal progetto: inglese. L’italiano e la quantizzazione richiedono un corpus separato e più ampio, anche con negazioni, correzioni, richieste personali, opzioni permutate e input ambigui.
Non misurati: consumo energetico, RAM con entrambi i modelli, beneficio end-to-end, qualità emotiva. Nessuna promessa di miglioramento percentuale.
Prima dell’uso nel dialogo: confrontare contro la pipeline attuale su casi non usati per impostare le soglie; accettare il decisore solo se il beneficio supera il costo e i falsi instradamenti. Nessuna sostituzione dei vincoli certi con giudizi probabilistici.

## Fonti
- https://huggingface.co/Mapika/decider-0.8b
- https://github.com/Mapika/decider
- https://huggingface.co/seongukjeong/decider-0.8b-GGUF

## APK
Version code 102480; payload verificato e runtime ARM64 llama-cpp-python 0.3.36. SHA256 APK `424c0290955e5010fe5f50bfe0c950cc55cf90a706201f5d32de1153660ddd67`. GGUF copiato nella cartella privata Android con SHA256 coincidente. Installazione e inferenza Android completate; esiti nella sezione seguente.

## Collaudo Android reale — 18:28–18:29
APK 102480, Samsung SM-S938B, processo 21041. Avvio manuale da parte dell’utente, report completato senza crash.

- Otto casi completati: sei scelte accettate corrette, nessuna scelta accettata errata, due astensioni. Non equivale al 100% di correttezza: due richieste sono rimaste senza decisione.
- Caso ambiguo inglese: chiarimento candidato principale, probabilità circa 0.625; astensione.
- Caso ambiguo italiano: memoria candidato principale (0.416) contro chiarimento (0.358); scelta errata potenziale, intercettata dall’astensione. La parità con Mac non è garantita: sul Mac il chiarimento era primo.
- Latenza mediana delle otto decisioni: 1113.7 ms; intervallo 1076.8–1153.3 ms. Totale 20.73 s, incluse preparazione/verifica/caricamento, otto decisioni e due cicli sintetici con strumenti.
- Ciclo calcolo: azione eseguita e verifica riuscita; arresto al limite di un passo (`budget_exhausted`), non prova di completamento autonomo di un obiettivo generale.
- Ciclo memoria sintetica: astensione, nessuna azione eseguita. Resta un caso non risolto; nessuna modifica alle soglie per farlo passare.
- Dopo la prova: processo vivo, nessun mapping del GGUF Decider in /proc/21041/maps; Qwen3.5 ancora mappato. Conferma rilascio del file mappato, non prova di assenza di ogni perdita di memoria futura.
- Campione memoria dopo la prova: PSS 1809466 KiB, RSS 1969360 KiB dell’intera app. Senza baseline e picco non misura il costo incrementale del decisore.
- Temperatura batteria rilevata dopo: 38.4 °C, carica 92%. Nessuna misura di energia né conclusione sul risparmio di batteria.

Report sintetico salvato in `/Users/erikahu/ALLMA/analisi/2026-10-15/decider/android-report.json`.

Conclusione: compatibilità nativa Android verificata su questo dispositivo. L’uso resta diagnostico; il campione è troppo piccolo e il caso memoria non riuscito impedisce di affidargli la gestione generale delle chat. Servono valutazioni di instradamento più ampie e un confronto end-to-end contro la pipeline attuale prima dell’attivazione.

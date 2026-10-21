# Supporto emotivo: risposta all’interlocutore

Il collaudo del 13 ottobre ha mostrato un riconoscimento corretto nei tre casi, ma due risposte bloccate perché il modello narrava l’esperienza dell’utente in prima persona.

La modifica del 14 ottobre esplicita nel prompt di sistema che ALLMA deve rispondere al messaggio, senza riscriverlo né continuarlo impersonando chi scrive. Il contesto emotivo richiama l’attribuzione degli eventi e distingue le emozioni dell’utente da quelle delle altre persone, mantenendo negazioni, incertezza e formato richiesto.

Non sono aggiunti retry, risposte precostituite o nuove inferenze. Il controllo subject_mismatch resta invariato. Sono aggiunte due prove di integrazione con risposte valide in seconda persona, accanto alla prova esistente che rifiuta l’appropriazione dell’esperienza e impedisce di apprenderla.

Verifica: 164 test superati (core_response, emotion_evidence, benchmark_metrics); git diff --check superato. I test usano un motore simulato: verificano il passaggio delle istruzioni e i controlli, non dimostrano che il GGUF reale le rispetti. Per questo serve ripetere sul telefono lo stesso profilo Supporto emotivo, con input, seed e budget invariati. Nessun incremento percentuale di qualità o velocità è ancora misurato per questa modifica.

APK compilata e verificata: payload corrente presente, KivyMD 1.2.0 e librerie native ARM64. Installazione con adb install -r riuscita, senza cancellare i dati; SHA-256 del base.apk sul telefono identico a quello locale: cef980681bfc8156f27ad6a69fc86a7610353c4df76527b82d9968c32c396f1d. Avvio activity richiesto; il dispositivo risultava in standby, quindi il completamento del caricamento e il benchmark reale restano da verificare manualmente. La release GitHub pubblicata non è stata modificata.

Collaudo reale completato alle 09:44:26: S4 e T1 bloccate per subject_mismatch; T2 passa, ma inventa sentimenti e un’esperienza condivisa. La modifica non dimostra un miglioramento qualitativo e il limite delle affermazioni indirette resta aperto. Tempi medi osservati 27,25→12,71 s, con telefono inizialmente molto più freddo: differenza non attribuibile causalmente al prompt. Analisi completa in /Users/erikahu/ALLMA/analisi/2026-10-14/supporto-emotivo/ESITO_TELEFONO.md.

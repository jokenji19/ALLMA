# Perché Qwen è rimasto sulla CPU — 26 ottobre 2026

## Risultato

La ricostruzione più solida è un'interruzione durante l'aggiornamento dell'APK, seguita da una quarantena GPU persistente troppo generica. Non è emerso un crash nativo registrato per l'evento correlato.

## Evidenze

1. Il report Android 102564 del 26 ottobre, salvato alle 11:53, contiene tre generazioni Qwen con backend `opencl`.
2. Il marcatore privato `files/allma_native_cache/gpu-pending.json` è stato modificato alle **11:58:38.785 +01:00**. Contiene soltanto il profilo e `stage=native_operation`.
3. Il registro Android riporta alle **11:58:40.996** la terminazione del processo ALLMA PID 15776 con motivo **16, PACKAGE UPDATED**, descrizione `killDueToPackageUpdate`. È lo stesso PID del collaudo 102564. Un ulteriore processo dell'app termina alle 11:58:41.743 con `USER REQUESTED / FORCE STOP`, descrizione `pkg removed`.
4. Il report successivo alla 102565 contiene backend `cpu`. Il medesimo marcatore sopravvive alle installazioni successive.
5. All'avvio della 102568 il log esplicita `backend=cpu reason=previous_gpu_operation_incomplete`. Decider seleziona separatamente `hexagon`.

Gli orari e il passaggio OpenCL → CPU concordano con un aggiornamento che ha interrotto un'operazione attiva. Il vecchio marcatore non contiene PID, identificativo dell'operazione o orario interno: l'associazione è quindi una forte inferenza dai registri, non una prova del proprietario ottenuta dal marcatore stesso. L'assenza di un crash registrato non costituisce una garanzia generale di assenza di difetti GPU.

## Causa nel codice

`NativeGuard.operation()` scrive il marcatore prima dell'operazione e lo elimina nel `finally`. La terminazione del processo da Android non esegue quel `finally`. `NativeGuard.blocked()` controlla l'esistenza del marcatore e la corrispondenza del profilo, senza distinguere crash, aggiornamento o arresto forzato.

`prepare_runtime()` seleziona quindi CPU. Le successive generazioni CPU non attraversano il guard GPU e non eliminano il marcatore: il blocco si conserva tra gli avvii e tra aggiornamenti con lo stesso profilo. Il meccanismo evita cicli di crash, ma può escludere stabilmente una GPU funzionante dopo una chiusura amministrativa.

## Intervento consigliato

- Registrare nel marcatore proprietario, operazione e orari, poi correlare la chiusura al processo corretto.
- Conservare il ripiego protettivo quando la causa è un crash nativo, un blocco o è sconosciuta. Un aggiornamento verificato può invece consentire un tentativo controllato, senza cancellazioni automatiche indiscriminate dei marcatori.
- Prima di installare un APK, attendere la fine delle operazioni native e l'assenza del marcatore oppure interrompere ordinatamente il lavoro.
- Rendere visibile in diagnostica il backend effettivo e il motivo del ripiego.
- Dopo l'intervento, verificare sul telefono una generazione OpenCL e la pulizia del marcatore, mantenendo le prove sintetiche di arresto nativo.

Durante questa analisi non sono stati cancellati marcatori, riavviata l'app o modificati i backend. Le evidenze tecniche sono in `/Users/erikahu/ALLMA/analisi/2026-10-26/protezione_gpu/`.

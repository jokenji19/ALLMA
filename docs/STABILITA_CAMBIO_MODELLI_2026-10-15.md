# Stabilità dei cambi di modello — 15 ottobre 2026

Collaudo eseguito su Mac e sul telefono SM-S938B con APK 102475. Il codice
applicativo non è stato cambiato in questa sessione; aggiunti tre test di
regressione per stress, stati occupati e richieste concorrenti.

## Test automatici

107 test distinti superati: 104 test esistenti di core, gestore, binding e
download; due nuovi test del core; un nuovo test del gestore. L'ultima
riesecuzione del gestore comprende 8 test, sette già contati nei 104.

Il nuovo stress test alterna 24 volte due motori simulati, verifica che non
siano caricati insieme, che ogni precedente venga chiuso una sola volta,
che ragionamento/DreamManager/ToT puntino al nuovo motore e che memoria,
identità e personalità restino le stesse. Verifica anche scelta persistente
e selezione ripetuta del modello già attivo senza ricaricamento.

Coperti anche blocchi durante risposta, benchmark, sogno e chiusura;
seconda richiesta concorrente respinta prima di avviare un altro download;
fallimento di download e ripristino del motore precedente dopo errore nativo.
Le prove di errore nativo sono simulate sul Mac, non iniettate nei GGUF reali.

## Sei cambi reali su Android

Modello iniziale dell'utente: Qwen 3.5 2B Q4_K_M. Tempi dal comando UI al
ricevimento del nuovo elenco pronto, inclusi bridge, verifica e caricamento.

| Cambio | Destinazione | Tempo |
|---|---|---:|
| 1 | Qwen 3 1.7B Q8_0 | 1,488 s |
| 2 | Qwen 3.5 2B Q4_K_M | 13,069 s |
| 3 | Qwen 3 1.7B Q8_0 | 0,600 s |
| 4 | Qwen 3.5 2B Q4_K_M | 1,207 s |
| 5 | Qwen 3 1.7B Q8_0 | 1,376 s |
| 6 | Qwen 3.5 2B Q4_K_M | 1,945 s |

Sei cambi riusciti, nessun crash osservato. Il secondo comprende quasi
12 secondi di prima verifica SHA-256 di Qwen 3.5 nella sessione. I ritorni
successivi riutilizzano la verifica dei byte invariati. Verificato anche il
blocco reale di una richiesta di cambio durante un benchmark, mantenendo
Qwen 3.5 attivo. Il doppio tocco sull'azione UI non ha causato due cambi.

## Generazione dopo i cambi

Profilo growth in memoria isolata, eseguito separatamente con ciascun motore:

- Qwen 3.5: due generazioni native completed/stop, circa 23,72 e 37,47 s.
- Qwen 3: due generazioni native completed/stop, circa 35,96 e 25,36 s.
- Per ciascun motore: cinque passi validi e quattro controlli di apprendimento
  superati, inclusa riapertura dello stato di coalescenza isolato.

Il comando di annullamento inviato nell'ultima prova è arrivato dopo il
completamento: non prova l'interruzione di una generazione in corso.
Non sono valutazioni comparative della qualità semantica o dell'intelligenza.

## Memoria e persistenza

Le otto impronte degli archivi personali erano identiche dopo il primo ciclo
completo e dopo il benchmark Qwen 3.5. Alla fine sette erano ancora identiche;
allma_memory.json è stato risalvato durante la sospensione del telefono.
Non viene quindi dichiarata identità byte per byte dell'intero archivio finale.

Dopo il ripristino di Qwen 3.5, eseguiti chiusura forzata e riavvio: il motore
è stato caricato correttamente e il selettore lo mostra attivo. La scelta in
model_binding.json contiene qwen3.5-2b-q4_k_m.gguf e reasoning=true.
Confrontate sul dispositivo le sezioni persistite messages, user_data e
trauma_log prima del riavvio e dopo riavvio più salvataggio in background:
impronta identica. Nessun contenuto personale copiato sul Mac.

## Risorse e limiti

PSS/RSS raccolti con dumpsys meminfo, KiB:

| Momento | PSS | RSS |
|---|---:|---:|
| Qwen 3.5 iniziale | 1770680 | 1883436 |
| Qwen 3, primo cambio | 2457834 | 2567964 |
| Qwen 3.5, primo ritorno | 1684834 | 1764800 |
| Qwen 3.5, secondo ritorno | 1616729 | 1692060 |
| Qwen 3, terzo caricamento | 2365520 | 2432172 |

Non emerge accumulo monotono nei ritorni allo stesso modello. Sono campioni
brevi, non una misura dei picchi né una prova che escluda perdite lente.
Batteria da circa 36,0 a 42,3 °C, telefono in carica; prove terminate senza
ulteriori generazioni. Nessuna stima del consumo energetico o vantaggio
percentuale: condizioni termiche e cache non erano controllate.

Evidenze: ../analisi/2026-10-15/stabilita-modelli/ rispetto alla radice ALLMA_V4.
Contiene log dei test, tempi/hashes aggregati e i soli report sintetici.
Collegamento diagnostico rimosso; ALLMA lasciata aperta con Qwen 3.5 attivo.

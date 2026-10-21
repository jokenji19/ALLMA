# Secondo motore: Qwen 3.5 2B

L'utente sceglie il modello da Impostazioni → Modello di ALLMA. Il catalogo
mantiene Qwen 3 1.7B Q8_0 come modello originale e aggiunge Qwen 3.5 2B
Q4_K_M, facoltativo. Un altro modello non viene scaricato automaticamente
all'avvio. Identità, memorie, crescita emotiva e feedback rimangono nei
rispettivi archivi di ALLMA, indipendenti dai file GGUF.

## Artefatto pubblico verificato

- Repository GGUF: https://huggingface.co/unsloth/Qwen3.5-2B-GGUF
- Revisione: f6d5376be1edb4d416d56da11e5397a961aca8ae
- File: Qwen3.5-2B-Q4_K_M.gguf
- Dimensione: 1280835840 byte, 1,28 GB decimali.
- SHA256: aaf42c8b7c3cab2bf3d69c355048d4a0ee9973d48f16c731c0520ee914699223
- GGUF v3, 320 tensori, architettura dichiarata qwen35.

Il download usa un file .part, ripresa verificata e checksum prima della
promozione al nome definitivo. Hash del download Mac e del trasferimento
Android verificati. La proiezione visiva non viene scaricata o attivata:
il collaudo riguarda testo e ragionamento, secondo la priorità dell'utente.

## Cambio controllato

Il backend rifiuta scelte estranee al catalogo. Download, hash e caricamento
avvengono fuori dal thread UI. Il cambio è serializzato e rifiutato durante
una risposta, un benchmark o un sogno. Il vecchio modello viene chiuso prima
di aprire quello nuovo; nessuna doppia copia dei pesi in RAM. Il nuovo motore
viene collegato a ragionamento, DreamManager e ToT. La scelta viene salvata
solo dopo il caricamento riuscito; un fallimento tenta il ripristino del
precedente. Se anche il ripristino fallisce, i dati personali restano, ma il
modello richiede un nuovo caricamento.

Il template di dialogo proviene dai metadati GGUF. Per qwen35 è riconosciuta
la capacità thinking; verificate entrambe le modalità con il template reale.
La cache aggiuntiva di stati completi per conversazione viene disabilitata
per questa architettura ibrida: primo collaudo conservativo, da ottimizzare
solo dopo averne verificato lo stato ricorrente.

## Runtime

Il runtime precedente non conteneva l'architettura qwen35. La ricetta Android
usa ora llama-cpp-python 0.3.36 e il suo llama.cpp incluso, evitando un checkout
C++ di versione diversa dai binding Python. Il sorgente ha SHA256
832db0699007f1be95a7e41ef12e88926b02ba836461e36a36372db2760c1a2e;
la ricetta controlla anche SHA512. Solo backend CPU, target Android ARM64/API24.
Il verificatore APK controlla ELF ARM64, marker runtime e presenza di qwen35
nella libreria, oltre al payload Python corrispondente al sorgente.

## Verifica iniziale

102 test mirati passati; suite completa 1032 passati, 15 saltati, 8 avvisi.
Questi risultati verificano i percorsi software con doppi controllati;
la riuscita di una generazione reale Android richiede il collaudo separato.
Non è ancora una percentuale di qualità o un confronto prestazionale tra modelli.

## Esito Android

La prima build 102466 ha richiesto una correzione del collegamento al core
interno. La build 102467 passa il core della chat esplicitamente alla WebView
ed è quella installata e collaudata. SHA256 APK:
`b24e3d8e5221369f0ad58f8f6ddcfbe1eeaf069d7d7b13f82977b83987d64f14`.
Dopo la correzione: 6 test mirati del bridge/gestore e 70 del core passati.
Una prima riesecuzione dei 70 test nel sandbox ha abortito importando PyTorch;
la riesecuzione autorizzata fuori dalle restrizioni del sandbox passa (73,81s).

Benchmark growth reale, sessione 449eb0b2b8744275ac72942ec8d9b1d1:
- Manifesto: qwen3.5-2b-q4_k_m.gguf, stato isolato.
- Cinque turni validi; quattro controlli crescita tutti veri.
- Due risposte generate da architettura qwen35, native template e ragionamento
  abilitati, entrambe completed/stop. Nessun recupero di sicurezza.
- Tempi end-to-end dei due turni generati: 17,351 e 38,372s.
- Primo token: 8,300 e 22,176s; 64 token di ragionamento limitati per turno.
- Batteria 41,3°C, USB in carica, 93% all'inizio e alla fine. Non prova un
  vantaggio termico, energetico o di velocità a parità di condizioni.
- Le risposte rispettano l'attribuzione, ma includono spiegazioni tecniche
  non necessarie su identità/codice. Resta da misurare la qualità generale.

Impronta dello stato cognitivo personale prima e dopo il benchmark e dopo
il ritorno al modello originale identica:
`c30cf6dd753b0468a8b9a11360fc96f79424de70f67f6f1cd4a8c76d6c2b5193`.
Nessuna copia del contenuto personale: solo hash calcolato sul dispositivo.
Report sintetici: /Users/erikahu/ALLMA/analisi/2026-10-14/modelli-qwen35/.

Verificato anche il ritorno Qwen 3.5 → Qwen 3 → Qwen 3.5 dall'interfaccia.
Stessa impronta cognitiva dopo entrambi i cambi e dopo il riavvio dell'app;
`model_binding.json` contiene qwen3.5-2b-q4_k_m.gguf e reasoning=true.
Il nuovo modello viene caricato con successo anche al riavvio. Layout del
selettore controllato visivamente sul dispositivo.

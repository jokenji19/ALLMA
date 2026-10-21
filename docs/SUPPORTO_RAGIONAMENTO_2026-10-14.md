# Supporto: ragionamento 48 / 128

Il confronto precedente ha mostrato appropriazioni già nell’uscita nativa del modello con ragionamento limitato a 48 token, sia con prompt minimo sia con mappa dei ruoli. L’esperimento seguente verifica se aumentare il ragionamento modifica questo comportamento.

Diagnostica → Supporto · ragionamento 48 / 128 esegue due generazioni native del caso S4 (corso e colloquio). Stesso input, prompt minimo, seed 20261312, GGUF e campionamento. Budget totali 192/272; ragionamento 48/128 e riserva della risposta sempre 144. Il wrapper limita il ragionamento al massimo a metà del totale: 128 è quindi ammesso per 272. I metadati registrano il budget e i token effettivamente usati. Nessuna memoria personale, CognitivePipeline o riscrittura della risposta; controlli diagnostici su attribuzione e due frasi, con revisione umana del testo completo.

Due richieste sono una prova circoscritta, non una valutazione generale. Ordine fisso 48 poi 128, cache e frequenze CPU non controllate. Il caso è già noto: eventuale successo richiede successivamente casi nuovi. Il maggiore budget può aumentare attesa e calore; la chat ordinaria non cambia budget. Arresto prima della prossima richiesta se batteria >=41,5°C; condizioni per richiesta e risultati parziali sono conservati. Nessuna misura di energia.

Verifica: 69 test superati (support_roles, benchmark_metrics, core_response), controllo web e diff pulito. Il test di protocollo verifica input/seed identici, due richieste e la stessa riserva della risposta. Nessun miglioramento del modello è ancora dimostrato.

APK verificata e installata conservando i dati, SHA-256 locale e sul telefono a15076bfb9b2542ac6761d33098a3858fb88b3249b4a58cc9a67ea8560cce6b7. Activity avviata; confronto qualitativo sul telefono ancora da eseguire. Release GitHub invariata.

Collaudo completato: budget effettivi 48/128 e risposta 144 invariati come previsto; entrambi i candidati si attribuiscono il corso. Tempo 4,83→8,66 s (+79,2% osservato con cache/ordine non controllati). Entrambi i ragionamenti terminano per length: nessuna verifica di chiusura naturale. Nessun aumento globale dei budget. Analisi: /Users/erikahu/ALLMA/analisi/2026-10-14/supporto-ragionamento/ESITO_TELEFONO.md.

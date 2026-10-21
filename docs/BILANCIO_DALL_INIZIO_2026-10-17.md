# ALLMA: bilancio dall’inizio del lavoro insieme

Periodo dei primi interventi documentati: **29 settembre–17 ottobre 2026**. Il progresso principale riguarda memoria, identità, apprendimento, integrazione dei sistemi e verificabilità. Ogni misura sotto indica il proprio punto di partenza; non viene inventata una percentuale unica dell’intero progetto.

## Misure recuperate e aggiornate

| Ambito | Punto di partenza disponibile | Risultato | Lettura del progresso |
|---|---|---|---|
| Detector emotivo locale | 19/74 casi corretti, 25,68%, nella versione storica `AllmaV0.8.4.2` | 73/74, 98,65%, ricontrollati il 17 ottobre | **+72,97 punti percentuali** sullo stesso corpus |
| Errori emotivi sul corpus | 55 | 1 | **−98,18% nel conteggio degli errori** |
| Attribuzioni emotive errate sui 32 casi senza emozione attuale dell’utente | 25 | 0 | **25 falsi positivi eliminati** sul campione |
| Emozioni miste, tutte le famiglie richieste | 0/8 | 8/8 | Otto casi recuperati |
| Recupero di una risposta appresa, prova Android del 1 ottobre | 25,60 s osservati nella generazione iniziale | 0,18 s osservati dopo le conferme, senza LLM | **−99,30% di attesa in quel singolo caso** |
| Vecchio benchmark di sei domande, due report del 1 ottobre | Media 76,81 s | Media 46,33 s | **−39,69% osservato**, con budget e lunghezza delle risposte differenti |
| Verifiche automatiche superate nei resoconti | 248 nel primo blocco del 29 settembre, già dopo alcune correzioni | 1.495 nel riepilogo attuale | Circa **6 volte** i controlli superati; suite ampliata, non qualità moltiplicata per sei |

Il detector emotivo è confrontato usando solo il metodo locale della vecchia versione e quello attuale, sul Mac. Il corpus di 74 frasi è già noto nello sviluppo ed è stato scritto dopo l’implementazione; non è un test indipendente o rappresentativo di tutte le emozioni umane. Sulle sole categorie comuni fra le due versioni: 19/65 → 64/65, quindi il vantaggio non dipende solo dall’aggiunta di categorie.

Sono stati recuperati 55 casi precedentemente sbagliati, con una regressione conservata nel risultato: **E10, “Mi manca molto la mia famiglia”**, atteso `sadness`, ora nessuna famiglia rilevata dal criterio di misura. Il precedente risultato storico 74/74 non viene attribuito al codice attuale: la nuova misura è 73/74. Il numero finale è il saldo di miglioramenti e regressioni, non una selezione dei soli successi.

La prova del recupero rapido dimostra un percorso specifico: la risposta confermata viene riutilizzata in un contesto compatibile e può essere revocata. Non dimostra ragionamento più rapido sulle domande nuove né modifica dei pesi del GGUF. Il confronto delle medie di ottobre è storico e non misura le prestazioni dell’APK odierna. Non risultano misure iniziali/finali controllate sufficienti per percentuali di autonomia o temperatura dell’intero percorso.

## Cambiamenti funzionali nel percorso

- Identità nominale stabile, distinta dai ricordi e dalla conoscenza generale del modello.
- Recupero delle risposte confermate, revoca e conservazione dopo il riavvio.
- Memoria personale con provenienza, correzioni e revoche; richiami letterali nativi dove il dato è esplicito.
- Crescita emotiva, significati personali e preferenze espressive legati a esperienze attribuite e riscontri.
- Ipotesi oniriche separatamente confermabili, correggibili e scartabili, con cronologia delle revisioni.
- Due Qwen selezionabili senza sostituire identità e memoria di ALLMA; cambi e riavvio collaudati.
- Decider operativo in più percorsi, con memoria, permessi e priorità governati da ALLMA.
- Correzioni della voce, risposta progressiva, interfaccia ridisegnata, copia e notifiche native subordinate al consenso.
- Build con controllo del contenuto, test isolati e protezioni più forti contro salvataggi incompleti o archivi corrotti.

Questi sono interventi documentati, non un elenco di capacità interamente assenti nel progetto originale. ALLMA possedeva già un’architettura ampia: il lavoro ha riparato e collegato parti esistenti, oltre a introdurre nuovi percorsi.

## Ultimo punto verificato

Build **102508** installata; **60/60** scenari software sul telefono con modello simulato. Suite e ricontrolli attuali: **1.495 superati e 15 saltati**. Nell’ultimo confronto delle correzioni: **43 fallimenti riprodotti recuperati su 44 casi direttamente confrontabili**, più tre controlli API prima bloccati; nessuna regressione in quel diverso campione. Questi risultati recenti non vengono presentati come misure dell’intero periodo.

Il metodo per continuare a misurare è in [MISURA_PROGRESSI_2026-10-17.md](/Users/erikahu/ALLMA/ALLMA_V4/docs/MISURA_PROGRESSI_2026-10-17.md). Le prossime valutazioni della qualità generale richiedono casi nuovi con modello reale, separati dalle regressioni note.

## Evidenze

- [Nuova misura emotiva rispetto alla versione storica](/Users/erikahu/ALLMA/analisi/2026-10-17/progressi-inizio/emotion-comparison.json).
- [Riepilogo numerico del bilancio](/Users/erikahu/ALLMA/analisi/2026-10-17/progressi-inizio/bilancio.json).
- [Primo blocco documentato del 29 settembre](/Users/erikahu/ALLMA/ALLMA_V4/docs/CORREZIONI_2026-09-29.md).
- [Prova di apprendimento e recupero rapido](/Users/erikahu/ALLMA/ALLMA_V4/docs/INTEGRAZIONE_APPRENDIMENTO_2026-10-01.md).
- [Limiti dei vecchi confronti di latenza](/Users/erikahu/ALLMA/ALLMA_V4/docs/MISURE_2026-10-12.md).
- [Ultime correzioni e collaudo](/Users/erikahu/ALLMA/ALLMA_V4/docs/CORREZIONI_AUDIT_2026-10-17.md).

In questo bilancio sono stati eseguiti una nuova misura locale del detector e il controllo dei resoconti conservati; nessuna modifica applicativa, nuova APK o nuova prova sul telefono.

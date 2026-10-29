# Percezione e confronto del contesto — 26 ottobre 2026

Intervento successivo alla build 102572. ALLMA-LM resta un progetto futuro: nessun addestramento, nuovo modello o servizio cloud avviato.

## Correzioni

- L'urgenza usa parole intere, ambito locale, negazioni e citazioni. «Colorato» non significa «ora»; «non è urgente e non devi rispondere subito» non genera una richiesta di fretta. Una proprietà dell'oggetto («un treno veloce») non impone una risposta rapida. Il segnale resta un indizio: non sono stati introdotti tagli del ragionamento o nuove politiche di budget.
- Il rilevatore emotivo locale include indizi espliciti in spagnolo, francese e tedesco, oltre a italiano e inglese. Usa le stesse famiglie e sfumature già consumate da chat, voce e personalità.
- Negazioni, altre persone, passato, ipotesi e incertezza sono controllati anche per le nuove espressioni. I vocaboli ambigui richiedono un contesto: «content» in un documento JSON non è felicità; «J’ai perdu ma clé» non prova confusione emotiva.
- Conservate le associazioni emotive apprese dall'utente e i relativi controlli di attribuzione. Il lessico strutturale aggiunto non diventa un ricordo autobiografico e non modifica i pesi del modello.
- Nessuna seconda inferenza per rilevare queste emozioni. Tre test del percorso chat verificano anche il passaggio degli indizi ai metadati e al prompt, con una sola chiamata al modello simulato.

Si tratta di riconoscimento euristico di indizi testuali, non della comprensione universale delle emozioni. Il report mantiene l'incertezza quando manca evidenza sufficiente; il tono e la correttezza della risposta del GGUF restano verifiche distinte.

## Due prove aggiunte alla Diagnostica

**Emozioni e urgenza · 24 scenari:** testi sintetici, nessun archivio personale e nessuna inferenza. Sulla stessa batteria il sorgente precedente supera 9/24 casi (37,5%), quello corretto 24/24 (100%): +62,5 punti percentuali su quei casi di regressione. Non è una percentuale generale di affidabilità, né una valutazione indipendente su dati nuovi.

**Contesto 2K / 4K / 8K · storia conservata:** stesso tokenizer e template del GGUF caricato, conversazione sintetica di 60 coppie, riserva finale di 256 token più 32 di margine. Registra token occupati, coppie rimosse e presenza di tre note iniziale/centrale/recente. Non genera risposte, non ricarica la GPU e non modifica il contesto della chat. I tempi registrati riguardano solo la preparazione del testo; non misurano attesa del modello, RAM allocata, correttezza del richiamo o durata della batteria.

La prova può essere interrotta; conserva le righe già concluse e rilascia lo stato occupato. Per scegliere una finestra operativa più grande servirà un confronto successivo di inferenza, RAM e temperatura. Il valore operativo rimane 2.048 token.

## Evidenze e collaudo

Cartella dei risultati: [percezione-contesto](/Users/erikahu/ALLMA/analisi/2026-10-26/percezione-contesto).

- [Confronto prima/dopo sui 24 casi](/Users/erikahu/ALLMA/analisi/2026-10-26/percezione-contesto/before-after.json).
- [Verifica corrispondenza APK/sorgenti e backend](/Users/erikahu/ALLMA/analisi/2026-10-26/percezione-contesto/apk-verification.json).

### Esito finale — build 102573

- APK compilata, verificata contro il payload corrente e installata con prenotazione del runtime inattivo, senza arrestare inferenze in corso. Primo tentativo rimandato perché un’operazione nativa era ancora attiva; al tentativo successivo l’installazione è riuscita.
- Desktop: **2.942 test superati, 15 saltati**, con sei test di uscita improvvisa esclusi da quel giro e **6/6 superati separatamente** fuori dall’ambiente che impedisce a OpenMP di aprire la memoria condivisa. Totale verificato: **2.948 superati**, 15 saltati. Un tentativo aggiuntivo è stato terminato con SIGKILL durante attività concorrenti: è conservato nei log e non è contato come risultato positivo.
- Android reale: **24/24 percezione**, **60/60 software**, confronto 2K/4K/8K completato. Processo rimasto vivo; Qwen ancora su **OpenCL**, zero operazioni native residue e prenotazione aggiornamento rilasciata. Nessuna inferenza Decider in questa batteria; NPU non ricollaudata qui.
- Ripristinato il tempo originale di spegnimento dello schermo: 60 secondi. Nessun archivio personale usato.

| Finestra confrontata | Token del prompt | Coppie conservate / 60 | Nota iniziale | Nota centrale | Nota recente |
|---|---:|---:|---|---|---|
| 2.048 | 1.738 | 25 | assente | assente | presente |
| 4.096 | 3.755 | 55 | assente | presente | presente |
| 8.192 | 4.097 | 60 | presente | presente | presente |

Si tratta della stessa conversazione sintetica e della presenza dei testi nel prompt: non prova che il modello sappia rispondere usando tutte le note. Il caso a 8K occupa circa 4,1K token di prompt, quindi non è nemmeno un carico di inferenza a piena finestra 8K. Il costo di preparazione è influenzato dai tentativi di rimozione dei turni e non va interpretato come velocità del modello.

[Esito aggregato e impronte dei sorgenti](/Users/erikahu/ALLMA/analisi/2026-10-26/percezione-contesto/summary.json). [Dati Android](/Users/erikahu/ALLMA/analisi/2026-10-26/percezione-contesto/android-result.json). [Rapporto contesto nativo](/Users/erikahu/ALLMA/analisi/2026-10-26/percezione-contesto/android-context-report.json).

Prossimo passo: confronto separato di generazione a 2K/4K/8K, una configurazione per volta con ripristino finale, stessi casi e seed, misura dell’attesa iniziale, RAM e temperatura. La finestra di produzione rimane 2K fino a quel confronto.


Aggiornamento successivo: il [confronto di inferenza reale, build 102574](CONFRONTO_CONTESTO_REALE_102574.md) è completato. Dodici richieste su Android, configurazione originale 2K ripristinata. L’aumento del contesto non ha migliorato i casi di qualità provati e la produzione resta a 2K.

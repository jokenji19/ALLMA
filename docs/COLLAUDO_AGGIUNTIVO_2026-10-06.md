# Collaudo aggiuntivo — 6 ottobre 2026

Suite finale: **564 passed, 15 skipped**, 12 warning di dipendenze, nessun fallimento; 50,92 s. Cinque nuovi test rispetto al collaudo precedente. I test saltati rimangono non verificati.

## Difetti riprodotti e corretti

- Una conferma ripetuta o una correzione dopo una conferma perdeva il riferimento alla risposta e avviava il modello. La catena dei feedback conserva ora chiave e identificatore dell'osservazione originale. Una seconda conferma sulla stessa osservazione non aumenta il conteggio; rimangono necessarie conferme di osservazioni distinte. La correzione invalida il candidato senza LLM.
- Un fallimento della scrittura della coda dei sogni lasciava l'ipotesi già aggiunta in RAM: al tentativo successivo veniva saltata come duplicato e il checkpoint poteva renderne impossibile il recupero dopo riavvio. Ora la RAM viene aggiornata soltanto dopo il salvataggio riuscito.
- Lo stesso ordine errato riguardava il checkpoint e la rimozione delle ipotesi dalla coda. Entrambe le operazioni ora salvano una copia prima di sostituire lo stato in RAM. Test con errori disco simulati seguiti da riprova o riavvio.
- Verificata anche la cancellazione onirica durante un aumento della temperatura: nessuna ipotesi o checkpoint consolidato, wake lock rilasciato.

I test iniziali hanno riprodotto quattro fallimenti in queste due aree; le regressioni rimangono nella suite.

## Telefono Samsung SM-S938B

Prove tramite la UI con modello reale, prima dell'installazione delle nuove correzioni.

| Prova | Esito | Generazione | Primo segmento risposta | CPU | Batteria |
|---|---|---:|---:|---:|---:|
| Quadrati e rettangoli | Conclusione corretta: non basta sapere che una figura è un rettangolo. Spiegazione imprecisa, tre frasi anziché due | 21,41 s; 151 token; stop | 18,65 s | 60,2 → 65,2 °C | 40,2 → 40,2 °C |
| Formazione delle stelle | Finale completo e leggibile, ma espressioni poco chiare e formato non realmente passo per passo | 31,77 s; 405 token; stop | Vedere JSON | 47,8 → 63,7 °C | 40,7 → 41,2 °C |

Il tentativo di interruzione della seconda richiesta è arrivato dopo il completamento. Non è una prova positiva di cancellazione sul dispositivo e non dimostra perdita di risposta. Nessuna domanda è stata sostituita con risposte hardcoded o rigenerata automaticamente per migliorare il risultato.

La qualità generale e il riscaldamento rimangono limiti concreti. Il telefono era collegato via USB: nessuna stima di autonomia o percentuale di miglioramento. Non ripetuto il benchmark completo né il collaudo vocale con parlato umano.

## Build

APK compilata, payload corrente verificato e librerie ARM64 controllate. SHA256: `a7b78d3bf4d705cfbf1239818786df7a78c7af7ff527e866f827eacf26ef98d8`.

Artefatti: `/Users/erikahu/ALLMA/analisi/2026-10-06/collaudo-aggiuntivo`.

Installazione finale con `adb install -r`: **Success**, senza disinstallazione o cancellazione dati. Modifiche salvate localmente; nessun commit o push effettuato in questa fase.

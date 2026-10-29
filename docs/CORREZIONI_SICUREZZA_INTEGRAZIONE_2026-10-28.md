# Correzioni successive all’audit del 28 ottobre 2026

Build Android **102589**, versione pubblica invariata **0.9.1**. APK compilata, verificata e installata sul dispositivo di prova. Modifiche salvate nel checkout; questo intervento non comprende commit, push o pubblicazione di una release.

## Correzioni

| Audit | Intervento | Verifica |
|---|---|---|
| A1 — testo/comandi | Il compositore invia un contenitore `chat` con un campo testuale che non viene reinterpretato. Il destinatario della chat non decodifica più stringhe come azioni. Rimossa anche la vecchia esclusione dei JSON dall’ammissione delle richieste. Un invio rifiutato libera l’attesa e recupera la bozza. | Test sui due destinatari reali, sull’ammissione e sul compositore; stringhe JSON e vecchi comandi speciali restano testo. Le azioni reali restano utilizzabili. |
| A2 — divieti Internet | Il vincolo del turno riconosce le varianti riprodotte nell’audit e ulteriori negazioni comuni; restringe il consenso generale senza modificarlo. Una copia già locale rimane utilizzabile. | Le otto nuove formulazioni di divieto non chiamano il lettore di rete. |
| A3 — nuovo soggetto | La sostituzione esplicita del soggetto aggiorna il riferimento di lavoro prima della ricerca. Una nuova domanda completa prevale sull’ancora vecchia. Una correzione ambigua non autorizza la ricerca dell’argomento precedente. | Tre prove attraverso il nucleo reale, con la vecchia fonte già in cache: la risposta proviene dal termometro e non dalla bussola, senza generazione del modello. |
| A4 — sogni | Il nucleo è l’unica autorità. La pagina richiede lo stato, attende conferma dei cambiamenti e non riproduce preferenze del browser. Sono ammessi solo booleani; un salvataggio fallito non pubblica uno stato diverso da quello confermato. | Test di tipo, errore di disco e interfaccia; su Android spunta e preferenza nativa coincidono. |
| A5 — attese HTTP | Limite del chiamante e cancellazione sorvegliati indipendentemente dal completamento del blocco di rete. `read1` legge i byte disponibili. Un’unica ammissione impedisce di accumulare richieste ancora in chiusura; i risultati tardivi non raggiungono chat o cache. | Requests reale sul servizio locale lento: cancellazione in circa 0,002 s nella prova; scadenza a 8,001 s; trasporti chiusi al termine. |
| A6 — memoria visiva | Eliminato il caricamento pickle. I nuovi vettori sono JSON con limiti e controlli di schema, tipo e valori finiti. Scritture atomiche, nomi delle immagini indipendenti dalle etichette e cancellazione limitata alla directory prevista. | Test di persistenza visiva esistenti, vettori malformati, preservazione dei vecchi file e rifiuto di cancellazioni esterne. |
| A7 — WebView | Accesso a file e content provider disabilitato; blocco rete obbligatorio e verificato. Se non si può applicare l’isolamento, la chat non viene caricata e l’avvio mostra un errore. Documento con Content Security Policy che blocca rete, risorse esterne, frame, plugin e invio di form. | Impostazioni simulate anche nel caso di errore; su Android documento pronto con la politica prevista e comunicazione nativa funzionante. |
| A8 — compatibilità | Rimosso il ramo memoria irraggiungibile. Ritirato l’output `thought` senza identificatore di richiesta; il flusso attivo rimane quello associato al turno. Anche gli aggiornamenti di stato serializzano i parametri, senza interpolare testo in codice JavaScript. | Test del vecchio callback con apostrofi e contenuto simile a codice; nessuna esecuzione o contaminazione di un altro turno. |

## Risultati

- Suite completa in 16 processi successivi: **3.215 casi distinti superati, 0 falliti, 15 saltati**. I 15 casi saltati sono legacy: 8 per NLP non disponibile, 5 per API core non disponibile, 1 per API reasoning non disponibile e 1 per file di prova assente. Sono preesistenti e non sono contati come superati; questo intervento non li rende operativi.
- **58 casi nuovi** rispetto al controllo precedente: 55 nel file di regressione dell’audit e 3 nella pipeline del cambio di argomento. Il conteggio complessivo esclude eventuali duplicazioni fra gruppi tramite coppia classe/nome del test.
- Sei prove di recupero dopo arresto improvviso hanno inizialmente incontrato il limite del Mac sulla memoria condivisa, prima di eseguire la prova prevista. Ripetuto l’intero gruppo nell’ambiente autorizzato: 554/554 superati, senza modificare o escludere quei test.
- APK: sorgenti incorporati e asset verificati; SHA-256 `db17007890aec89461736fa40c9f3c79ceaea880eba9cfe3e4e7cc7f293d3a1f`.
- Android: **6/6 scenari della diagnostica Internet**, in archivi sintetici separati dalle conversazioni personali. Verificati versione installata, avvio della chat, politica del documento e sincronizzazione della spunta sogni.
- Internet e sogni erano entrambi abilitati prima del collaudo e lo sono rimasti dopo. Qwen è rimasto sul backend **OpenCL**. Non sono stati cambiati modello, tempo di spegnimento dello schermo o dati autobiografici per eseguire le prove.

## Limiti e scelte esplicite

- I vecchi `features.pkl` e i loro metadati sono **conservati e non deserializzati**. Se esiste soltanto il vecchio formato, il componente visivo impedisce scritture e cancellazioni finché non viene predisposta una conversione esplicita e sicura. Non è stata eseguita una conversione sui dati del telefono.
- Il limite temporale protegge il chiamante anche mentre la libreria sincrona attende DNS/intestazioni. Un trasporto sottostante può terminare solo quando il sistema restituisce il controllo; nel frattempo non si ammettono altri trasporti, non si accumulano thread e non si pubblicano risultati tardivi. Il test locale ha verificato anche la chiusura dei trasporti utilizzati.
- Il riconoscimento linguistico dei divieti non è una prova matematica di comprensione di ogni formulazione o lingua. Il consenso generale disattivato resta una barriera distinta, indipendente dall’interpretazione del messaggio.
- La politica degli script mantiene `unsafe-inline` perché l’interfaccia attuale usa gestori di eventi incorporati. Non è stata rimossa la sanitizzazione Markdown: la Content Security Policy è una protezione aggiuntiva. Migrare tutti i gestori a collegamenti espliciti permetterà una politica ancora più restrittiva.
- Il browser integrato ha impedito l’apertura del file locale della fixture; quel tentativo non è contato come verifica superata. I controlli automatici JavaScript e il collaudo dell’app Android installata sono riportati separatamente.
- Non è una certificazione contro ogni vulnerabilità futura, né un collaudo su tutti i telefoni Android. La verifica Android riguarda questo dispositivo e i sei scenari indicati, oltre ai controlli di avvio/stato descritti.

Evidenze locali: `/Users/erikahu/ALLMA/analisi/2026-10-28/correzioni-sicurezza/`. L’audit precedente e le riproduzioni originarie sono conservati in `audit-integrazione-sicurezza/`.

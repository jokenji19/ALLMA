# Chat con Internet, indicatori e sogni · collaudo del 28 ottobre 2026

Build finale installata: **102588**, versione 0.9.1. Internet è rimasto **abilitato**, come nella preferenza già scelta sul telefono. Tempo di spegnimento ripristinato a 60 secondi.

## Problemi osservati nella conversazione reale

Alla domanda «Chi era Mussolini?» il modello aveva risposto «Non sono Mussolini», confondendo il soggetto storico con ALLMA. Al successivo «Cerca su Internet» aveva prodotto anche affermazioni storiche false, tra cui un ruolo nella Resistenza. Le due risposte erano generate dal modello: non erano risultati di una fonte consultata con successo.

Le cause individuate:

1. Il filtro dei risultati respingeva «Benito Mussolini» perché la domanda conteneva solo il cognome. La protezione dagli omonimi era troppo rigida.
2. «Cerca su Internet» senza argomento esplicito non recuperava correttamente il soggetto della domanda precedente. Anche un successivo approfondimento poteva fermarsi su quell’istruzione invece di risalire al soggetto.
3. Una ricerca esplicita senza fonte utilizzabile poteva essere sostituita da una risposta del modello. Il solo controllo di provenienza non ne correggeva i fatti.
4. Lo stato della ricerca non era visibile mentre avveniva; le copie locali non avevano un’etichetta immediata.

## Correzioni

La ricerca tenta prima il titolo tramite l’API ufficiale e segue normalizzazioni e rimandi documentati. Può fare un solo tentativo di ricerca aggiuntivo. Un cognome non viene associato arbitrariamente al primo risultato: il rimando «Mussolini → Benito Mussolini» deve provenire dal servizio. Rimangono i controlli su omonimi, disambiguazioni, host, protocollo, dimensioni, consenso e cancellazione.

Il comando di ricerca contestuale risale alle domande dell’utente; i testi dell’assistente non diventano prove. La risoluzione continua a funzionare dopo più seguiti. Per gli approfondimenti vengono esclusi gli estratti già comunicati nella parte recente del dialogo.

Una ricerca richiesta esplicitamente, ma priva di fonte utilizzabile, produce ora un esito tecnico separato: non viene rimpiazzata da fatti inventati dal modello. Le domande generali riconosciute vengono inoltre distinte meglio dai richiami di esperienze personali.

## Segnali nell’interfaccia

- **Ricerca su Internet…**: compare soltanto durante la consultazione effettiva, con un colore discreto.
- **Locale**: ALLMA non sta cercando online in quel momento. Non significa che il consenso generale sia disattivato.
- **Wikipedia · fonte online**: il messaggio usa una fonte appena consultata.
- **Wikipedia · copia locale**: il messaggio riusa un estratto conservato sul dispositivo, senza nuova ricerca.

Gli eventi sono associati alla singola richiesta: aggiornamenti tardivi non possono accendere l’indicatore di un altro turno. Il completamento e l’interruzione ripristinano lo stato locale. «Origine» conserva dettagli, collegamenti alla revisione letta e attribuzione.

È stato eliminato l’avviso in basso all’avvio e al termine dei sogni, insieme al relativo codice e stile. Il ciclo onirico, il Diario e l’indicatore discreto restano disponibili.

È stato migliorato anche lo scorrimento delle risposte immediate: la posizione viene valutata prima della sostituzione finale del testo. Chi sta leggendo messaggi precedenti non viene riportato forzatamente in fondo.

## Risultati

**3157 test distinti superati, 15 saltati, 0 falliti**, in 16 gruppi di processi separati. Dopo l’ultima correzione dello scorrimento sono passati anche i 13 controlli mirati su interfaccia, navigazione e invio.

Prova sul Mac dell’intera pipeline con accesso reale a Wikipedia: **6/6**, senza chiamare la generazione del modello. Prova Android sulla build finale: **6/6**. I casi coprono ricerca contestuale dopo una risposta errata, contributo nuovo da cache, cambio d’argomento, calcolo locale, identità e fonte non disponibile simulata. Gli archivi diagnostici erano separati dalle conversazioni personali.

Nella chat visibile sono state poi eseguite due domande pubbliche, prima su Mussolini e poi nella build finale su Marie Curie. In entrambi i confronti il primo messaggio ha attivato la ricerca reale, il secondo ha usato un estratto differente dalla cache. Le etichette online/locale sono state lette nell’interfaccia effettiva. I controlli non si basano soltanto sul fatto che la pipeline abbia restituito `valid`.

Per Marie Curie, la risposta ha riportato la biografia dalla fonte; al seguito ha aggiunto l’assegnazione del Nobel nel 1903. Non ha ripetuto il primo estratto.

La prima sonda automatica dello scorrimento ha letto circa 30 pixel di distanza dal fondo durante l’animazione e si è fermata troppo presto. Tre letture successive con la chat visibile e inattiva hanno misurato circa −0,67 pixel, ossia il fondo con arrotondamento del viewport. La sonda futura aspetta che l’animazione si assesti. Sono conservati separatamente il risultato iniziale, le riletture e le osservazioni successive di una chat con posizione ormai cambiata; non vengono usate per dichiarare un difetto di contenuto.

## Limiti ancora presenti

La consultazione riguarda Wikipedia, non l’intero Web. L’estratto documenta ciò che quella pagina afferma e può contenere errori. Una domanda non riconosciuta o senza fonte può ancora richiedere il modello locale, con i suoi limiti di conoscenza e ragionamento. Il miglioramento elimina i problemi riprodotti in questo percorso; non certifica la correttezza di qualsiasi futura conversazione.

Le modifiche sono salvate nei sorgenti e nell’APK installata. Non è stato richiesto un nuovo commit, push o rilascio GitHub per questo intervento.

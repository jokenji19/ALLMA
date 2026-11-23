# Piano di sviluppo della ricerca Internet di ALLMA

Baseline del 16 novembre 2026, build Android **0.9.1.27 (102619)**.

## Stato attuale

**Realizzazione stimata del piano al 50%.** La stima è la media dei 12 ambiti a pari peso. La scala è 0 per una funzione da iniziare, 25 per un prototipo o una copertura circoscritta, 50 per una funzione integrata con lacune significative, 75 per una funzione già utilizzabile con verifiche mirate ancora da estendere, 100 quando i criteri di verifica concordati sono soddisfatti. Si aggiorna solo quando un ambito raggiunge il livello successivo.

| Prova | Misura | Risultato |
|---|---|---|
| Decisione di cercare, con rete simulata | Se il sistema seleziona correttamente la ricerca o il percorso locale nei casi previsti | **101/101**, con 38 ricerche attese e 63 casi locali |
| Ricerca con fonti reali sul Mac | Se il sistema recupera evidenze utili alla domanda | **7/12 pertinenti (58,3%)**, 2 parziali e 3 senza riscontro |
| Flusso sul Galaxy | Quattro ricerche mirate in tre lingue e un controllo a globo spento | **5/5**, nessuna attività di rete nel controllo a globo spento |
| Regressione software | Compatibilità delle correzioni con il resto dell'app | **3.304 test superati** |

Le 12 domande con fonti reali erano concentrate sui primati e sulle attribuzioni storiche. Il confronto più ampio deve includere anche scienza, attualità, documentazione tecnica, cultura, sport e richieste locali.

## Cosa migliorare

| Ambito | Realizzazione | Lavoro rimanente e verifica |
|---|---:|---|
| 1. Ricerca generale sul telefono | **25%** | La ricerca ampia usa anche un servizio sperimentale su loopback. Rendere esplicita la disponibilità dei motori e verificare un percorso utilizzabile senza il Mac. Provare un'installazione pulita su Wi-Fi e rete mobile, con e senza servizio di ricerca configurato, e distinguere motore assente da ricerca senza risultati. |
| 2. Capire cosa cercare | **50%** | Estrarre argomento, relazione, luogo, data e vincoli come «primo», «in solitaria» o «senza scalo». Generare poche query complementari, usando sinonimi e nomi alternativi. Risolvere i seguiti dalla chat e chiedere un chiarimento quando più riferimenti sono plausibili. Verificare cambi di argomento, correzioni e parafrasi in un insieme di domande tenuto da parte. |
| 3. Trovare e leggere i passaggi giusti | **50%** | Classificare i risultati per pertinenza alla domanda, qualità della fonte e data, quando conta. Leggere il passaggio esatto e il contesto necessario. Migliorare l'estrazione di testo, tabelle e abstract e conservare l'attribuzione. Provare pagine lunghe, titoli fuorvianti, sigle, omonimi e fonti temporaneamente inaccessibili. |
| 4. Incrociare le fonti | **25%** | Scomporre le domande complesse in affermazioni verificabili. Rilevare fonti che riprendono lo stesso originale e conflitti di definizione, data o perimetro. Mostrare il disaccordo quando le evidenze restano inconcludenti. Verificare copie della stessa notizia, fonti divergenti e primati validi solo in una categoria. |
| 5. Comporre risposte documentate | **50%** | Mettere la risposta diretta all'inizio, spiegare le differenze rilevanti e collegare le affermazioni alle rispettive fonti. Aumentare il dettaglio su richiesta mantenendo i vincoli di formato. Segnalare i punti rimasti aperti. Verificare manualmente che ogni affermazione centrale sia sostenuta dalla citazione. |
| 6. Gestire attualità e fonti specialisthe | **50%** | Estendere i percorsi per meteo, studi, aggiornamenti tecnici, sport e dati correnti. Distinguere ora del dato, data dell'evento e data di pubblicazione. Gestire unità, fusi orari, versioni e periodi. Misurare quanto spesso il sistema rifiuta dati scaduti e recupera una fonte recente adeguata. |
| 7. Cercare in più lingue | **50%** | Estendere il controllo semantico oltre i casi sui primati coperti in italiano, inglese e spagnolo. Quando serve, cercare nella lingua della fonte più utile e rispondere in quella dell'utente. Verificare che nomi, date, condizioni e implicazioni restino corretti nella traduzione e nei seguiti multilingue. |
| 8. Mostrare cosa sta succedendo in chat | **75%** | Rifinire il globo, l'indicatore di attività e l'apertura delle fonti. Rendere distinguibili «ricerca disattivata», «motore irraggiungibile», «riscontro parziale», «risposta da fonte salvata» e «nessun riscontro». Verificare leggibilità, accessibilità e stati che cambiano mentre la ricerca è in corso. |
| 9. Imparare dalle ricerche e dal feedback | **50%** | Estendere salvataggio, correzione e revoca alle diverse categorie di fonti. Conservare l'affermazione, la fonte, la data e l'eventuale correzione dell'utente. Il pollice su esprime utilità. Il pollice giù può avviare una verifica con Internet consentito. Verificare che una correzione sostituisca il dato precedente anche dopo un riavvio e che un dato scaduto venga segnalato quando riutilizzato. |
| 10. Proteggere privacy e consenso | **75%** | Continuare a verificare che escano solo termini pubblici necessari, controllando dati personali combinati, cronologia, log, indirizzi locali, reindirizzamenti e testo ostile nelle pagine. Provare revoca e cancellazione durante richieste attive, cambio di chat, passaggio in background e riavvio. |
| 11. Prestazioni e resilienza Android | **50%** | Misurare separatamente decisione, ricerca, lettura e risposta. Imporre limiti di durata e traffico, dare priorità alle fonti più promettenti e riusare solo dati ancora validi. Misurare latenza mediana e al 95º percentile, memoria, temperatura e consumo su reti diverse e su dispositivi di più fasce. |
| 12. Benchmark e diagnosi dei problemi | **50%** | Unire prove ripetibili con fonti controllate e collaudi con rete reale. Tenere un gruppo di domande fuori dallo sviluppo. Registrare per ogni fallimento se dipende da decisione, query, motore, lettura, verifica o risposta. Confrontare due build sulle stesse domande, con lo stesso hardware e condizioni confrontabili. |

## Sequenza di lavoro

1. **Misurare e rendere la ricerca disponibile sul telefono.** Preparare il primo gruppo fisso con domande risolvibili, ambigue, senza riscontro, sensibili e con Internet spento. Riprodurre i casi falliti su Nobel, volo solitario attraverso l'Atlantico e invenzione della stampa. Verificare separatamente cosa accade senza il servizio sperimentale sul Mac.
2. **Aumentare il numero di domande che trovano evidenze utili.** Migliorare la formulazione delle query, la scelta delle fonti e la selezione dei passaggi. Ripetere il confronto anche con domande nuove, usando quelle già fallite come regressioni.
3. **Aumentare l'affidabilità delle risposte.** Verificare affermazione per affermazione, esplicitare conflitti e copertura parziale, controllare freschezza, lingua e fedeltà delle citazioni. Collegare il feedback a evidenze correggibili e conservabili.
4. **Validare il rilascio Android.** Confrontare prestazioni su più dispositivi, verificare gli stati dell'interfaccia e ripetere le prove di privacy con errori di rete, cambi di chat, revoca e riavvio.

## Indicatori da pubblicare a ogni confronto

- **Copertura** come quota di domande risolvibili con risposta completa e fonti pertinenti. Indicare a parte risposte parziali, mancate ricerche, errori dei motori e astensioni corrette.
- **Correttezza delle citazioni** come quota di affermazioni centrali effettivamente sostenute dal passaggio citato.
- **Protezione dei dati** come numero di invii non autorizzati o pubblicazioni tardive osservati nel gruppo di prove dedicato.
- **Prestazioni** come latenza mediana e al 95º percentile, con tipo di rete e dispositivo. Riportare memoria, temperatura e consumo nelle prove prolungate.

Come primi obiettivi di collaudo si propongono almeno **90% di risposte complete** sui casi risolvibili e almeno **95% di affermazioni centrali sostenute dalle citazioni** sul gruppo di domande tenuto da parte. Per consenso, revoca e protezione dei dati l'obiettivo è **zero violazioni osservate**. Il 100% di realizzazione riguarda il completamento degli ambiti e il relativo collaudo.

## Aggiornamento della build 0.9.1.28

La ricerca generale può interrogare l'indice pubblico Mwmbl direttamente quando il servizio sperimentale SearXNG non risponde. ALLMA legge le pagine trovate prima di citarle. Il confronto usa 18 domande fisse, con SearXNG escluso in entrambe le versioni. Il controllo automatico confronta gli elementi attesi nelle fonti, con una soglia aggiuntiva sulla provenienza per alcuni casi.

| Esito | 0.9.1.27 | 0.9.1.28 |
|---|---:|---:|
| Tutti gli elementi attesi | 9/18 (50%) | 13/18 (72,2%) |
| Riscontro parziale | 1/18 | 3/18 |
| Nessun riscontro | 8/18 | 2/18 |

Le tre domande usate per riprodurre il problema ora trovano riscontri sul primo Nobel assegnato a una donna, sul primo volo transatlantico in solitaria e sulle diverse tappe della stampa a caratteri mobili. La regressione software conta **3.310 test superati**.

Sul Galaxy la build **102620** ha superato **5 prove mirate su 5** con SearXNG scollegato. I log hanno confermato una risposta da Mwmbl per le query CSS. Anche i tre casi storici hanno restituito fonti, con tempi di ricerca tra **2,3 e 5,6 secondi** sulle quattro consultazioni. A globo spento la ripetizione della domanda CSS non ha generato attività Internet. La preferenza del globo è stata ripristinata al termine.

Il traguardo del 90% viene valutato nel confronto più ampio qui sotto.

## Misura della copertura su 48 domande nuove

Il campione contiene otto domande per ciascuno di sei ambiti, in italiano, inglese, spagnolo, francese, portoghese e tedesco. La prova confronta il motore di ricerca generale delle APK 0.9.1.27 e 0.9.1.28, eseguito sullo stesso Mac con fonti web reali, preferenze temporanee e SearXNG escluso. Il percorso di chat completo è collaudato separatamente con il benchmark integrato Android.

La verifica automatica cerca le informazioni attese nei passaggi citati. La revisione manuale controlla la relazione fra domanda e passaggio. È completo il caso in cui almeno un passaggio, oppure più passaggi insieme, sostengono la risposta richiesta. Un risultato parziale fornisce un elemento pertinente e lascia aperta una parte essenziale. Un risultato fuori tema cita un passaggio che non risponde al quesito. La durata include i casi senza riscontro.

| Esito della revisione manuale | 0.9.1.27 | 0.9.1.28 |
|---|---:|---:|
| Riscontro completo | 4/48 (8,3%) | 5/48 (10,4%) |
| Riscontro parziale | 3 | 3 |
| Passaggi fuori tema | 6 | 6 |
| Nessun passaggio | 35 | 34 |
| Latenza mediana | 2,43 s | 2,94 s |
| Latenza al 95º percentile | 3,86 s | 7,67 s |

| Ambito | Completi nella 0.9.1.27 | Completi nella 0.9.1.28 |
|---|---:|---:|
| Storia | 0/8 | 0/8 |
| Scienza | 0/8 | 0/8 |
| Tecnologia | 1/8 | 1/8 |
| Geografia | 2/8 | 2/8 |
| Cultura | 1/8 | 1/8 |
| Energia e ambiente | 0/8 | 1/8 |

La 0.9.1.28 ha trovato il passaggio mancante sul limite di 1,5 °C nell’Accordo di Parigi e un riscontro parziale per la documentazione SQLite WAL. Le sei risposte fuori tema persistono. Nel caso del Muro di Berlino la parola «caduto» appartiene a un passaggio su una persona. Nel caso della Divina Commedia la citazione descrive un adattamento a fumetti. La domanda pubblica sulla lunghezza di un indirizzo IPv6 viene fermata dal filtro prima della ricerca in entrambe le versioni.

Nella 0.9.1.28, su 34 domande prive di passaggi pubblicati, **23** hanno ricevuto lo stato «evidenza insufficiente», **9** «ricerca parziale», **1** «nessun risultato» e **1** è rimasta locale. Il recupero di pagine e la selezione di passaggi che sostengono la relazione richiesta sono i punti da approfondire. Le proporzioni riguardano questo campione mirato e alcune risposte complete includono anche un secondo estratto irrilevante.

La lista è in `benchmarks/evaluation/internet_coverage_v2.json`. Per ripetere il test di recupero sui sorgenti locali, usare `python3 tools/measure_internet_retrieval.py --cases benchmarks/evaluation/internet_coverage_v2.json --output <percorso-report.json>`. Il confronto riportato sopra usa il codice estratto dalle due APK.

## Confronto della chat su due ambienti Android

La stessa APK **0.9.1.28 (102620)** ha completato tutti i 45 scenari integrati su entrambi gli ambienti, con SearXNG scollegato e conversazioni sintetiche. Il benchmark comprende anche meteo, fonti specialistiche, dialoghi di seguito, consenso e risposte locali. Le preferenze Internet prima e dopo la prova coincidevano su entrambi.

| Ambiente | Scenari conformi alle attese | Durata complessiva |
|---|---:|---:|
| Galaxy S25 Ultra fisico, Android 17 | 42/45 (93,3%) | 21,0 s |
| Emulatore ARM64, Android 13 | 44/45 (97,8%) | 35,7 s |

Il controllo che simulava una fonte indisponibile ha restituito contenuto da un altro percorso web in entrambi gli ambienti. Questo è uno scostamento dall’attesa del test. Sul Galaxy due seguiti sono passati per la ricerca generale. Il primo ha mantenuto il soggetto della domanda, il secondo ha citato altri membri della famiglia Mussolini, perdendo il riferimento a Benito. Le durate descrivono le due esecuzioni osservate, con reti, modelli locali e hardware diversi. Il collaudo su un secondo telefono fisico resta aperto.

## Relazioni fra domanda e fonte nella 0.9.1.30 e nella 0.9.1.31

La ricerca distingue il soggetto della domanda dalla relazione richiesta, per esempio la data di un evento, l’autore di un’opera o la foce di un fiume. Consulta il testo della pagina e cita la revisione letta quando la fonte è Wikipedia. Le domande riconosciute con evidenza insufficiente ricevono un esito di ricerca senza affermazioni fattuali generate dal modello.

Il confronto usa le stesse 48 domande, fonti reali e SearXNG disattivato sul Mac. La 0.9.1.29 è stata eseguita dal codice estratto dall’APK. La 0.9.1.30 usa i sorgenti della build 102622. Gli esiti sono classificati dopo aver letto i passaggi citati.

| Esito | 0.9.1.29 | 0.9.1.30 |
|---|---:|---:|
| Riscontro completo | 5/48 (10,4%) | 17/48 (35,4%) |
| Riscontro parziale | 2 | 3 |
| Solo passaggi fuori tema | 6 | 2 |
| Nessun passaggio | 35 | 26 |
| Latenza mediana | 2,92 s | 2,50 s |
| Latenza al 95º percentile | 6,80 s | 6,76 s |

Sulle **23 domande riconosciute dal nuovo percorso**, i riscontri completi passano da **3 a 15**. Il miglioramento comprende la caduta del Muro di Berlino e la distinzione fra l’autore della Divina Commedia e quello di un suo adattamento. La 0.9.1.29 conteneva due risposte classificate complete con una seconda citazione fuori tema, su Wellington e sulla foce del Danubio. La 0.9.1.30 ha restituito un solo passaggio pertinente in entrambi i casi. Nei due casi ancora fuori tema, i passaggi descrivono lavori a un impianto idroelettrico e un effetto biologico dell’ozono. Le otto domande di scienza hanno ancora zero riscontri completi.

Le 12 domande aggiuntive in `benchmarks/evaluation/internet_facts_holdout.json` hanno dato **7 riscontri completi** e **5 senza passaggio**. I risultati completi coprono soprattutto la paternità delle opere. Restano senza riscontro l’apertura della Torre Eiffel, l’inizio della Prima guerra mondiale, la caduta di Costantinopoli, la foce del Rio delle Amazzoni e il Paese in cui si trova il Vesuvio. Questi casi misurano la copertura osservata sulle domande del campione.

Nel primo collaudo sul Galaxy, una domanda in francese inserita dopo una domanda in inglese ha ereditato la lingua sbagliata. La chat è passata al modello locale e ha attribuito al Danubio una foce errata. La build 102623 determina la lingua di consultazione dalla formulazione della domanda riconosciuta. Il motore misurato nelle tabelle sopra usa gli stessi criteri di selezione.

La build 102623 ha superato **5 prove su 5** sul Galaxy S25 Ultra in una chat sintetica. Muro di Berlino, Divina Commedia, capitale della Nuova Zelanda e foce del Danubio hanno restituito un passaggio pertinente con la revisione della fonte. La quinta prova ha confermato l’assenza di attività di ricerca a globo spento. La preferenza Internet precedente è stata ripristinata. La suite locale conta **3.337 test superati**.

## Spiegazioni scientifiche nella 0.9.1.33

Per le domande supportate, ALLMA identifica se la richiesta riguarda una causa, un meccanismo, una funzione, una distinzione o una misura. Seleziona una frase o due frasi adiacenti nello stesso paragrafo della fonte. Un passaggio sul galleggiamento del ghiaccio deve indicare la differenza di densità rispetto all’acqua. Per l’accumulo idroelettrico deve descrivere sia la generazione sia il pompaggio verso il bacino superiore. Il testo mostrato proviene dalla pagina citata. [INAF](https://www.media.inaf.it/2022/10/17/eclissi-sole-25-ottobre/) · [NOAA](https://oceanservice.noaa.gov/facts/tidescurrents.html) · [USGS](https://pubs.usgs.gov/gip/volc/nature.html) · [US Department of Energy](https://www.energy.gov/cmei/water/pumped-storage-hydropower)

| Misura con fonti reali sul Mac | Prima | 0.9.1.33 |
|---|---:|---:|
| Domande di scienza con riscontro completo | 0/8 | 8/8 |
| Riscontri completi nel campione generale | 17/48 (35,42%) | 27/48 (56,25%) |
| Solo passaggi fuori tema nel campione generale | 2 | 0 |
| Latenza mediana sulle 8 domande di scienza | 2,83 s | 1,06 s |
| Latenza mediana sulle 48 domande | 2,50 s | 1,56 s |

Le prove sono state eseguite con il motore di ricerca generale, SearXNG disattivato e preferenze temporanee. I dieci casi interessati sono stati ripetuti sul codice estratto dall’APK 0.9.1.31. Per il confronto sulle 48 domande si usa il precedente risultato documentato della 0.9.1.30, che impiega la stessa selezione della 0.9.1.31. I risultati dipendono dalle fonti raggiungibili al momento del test.

La revisione dei passaggi integra il controllo automatico delle parole attese. Per esempio, «densità che è circa dell’8% inferiore» risponde alla domanda sul ghiaccio anche se il controllo automatico cercava l’espressione contigua «densità inferiore». Il campione generale ha ottenuto 23 corrispondenze automatiche complete e 27 riscontri completi dopo revisione. Le [12 riformulazioni](../benchmarks/evaluation/internet_science_variants.json) hanno tutte trovato un riscontro dopo revisione. Coprono gli stessi fenomeni, con due domande provate anche in inglese. Restano 18 domande generali senza passaggio e tre con riscontro parziale. La suite locale conta **3.341 test superati**.

Il primo collaudo Android ha mostrato che una fonte di riserva sulle mitocondrie menzionava l’ATP in un passaggio sulla loro origine. La build 102625 richiede anche il legame con la produzione di energia, la respirazione cellulare o la fosforilazione ossidativa. Con la pagina universitaria simulata come indisponibile, la ricerca ha trovato un passaggio pertinente nella fonte di riserva. Sul Galaxy S25 Ultra sono passate **6 prove su 6**, cinque domande con riscontri citati e un controllo con il globo spento. La preferenza Internet precedente è stata ripristinata.

## Documentazione tecnica nelle versioni 0.9.1.34 e 0.9.1.35

Per i riferimenti tecnici riconosciuti, ALLMA apre direttamente il manuale e seleziona la sezione del simbolo, del comando o del protocollo richiesto. Quando una definizione e la spiegazione sono in punti distinti della sezione, il segno `[…]` indica il passaggio omesso. Per le proprietà pubbliche di IPv6, l’ammissione si limita alla domanda sulla lunghezza dello standard e lascia fuori le richieste sugli indirizzi personali. [Python](https://docs.python.org/3/library/contextlib.html) · [Cargo Book](https://doc.rust-lang.org/cargo/commands/cargo-metadata.html) · [SQLite](https://sqlite.org/wal.html) · [Git](https://git-scm.com/docs/git-rebase) · [MDN](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Status/304)

Nelle otto domande di tecnologia, i riscontri completi dopo revisione sono passati da **1/8** con l’APK 0.9.1.33 a **8/8** con la 0.9.1.35. Il controllo automatico ha segnato `cargo metadata` come parziale perché il nome del comando è nel titolo della fonte, mentre il passaggio del manuale descrive correttamente l’output JSON. Le [otto prove aggiuntive](../benchmarks/evaluation/internet_technical_variants.json), con cinque riferimenti nuovi e tre riformulazioni, hanno ottenuto **8 riscontri completi su 8**.

Nel primo giro sulle 48 domande, la 0.9.1.34 ha ottenuto **30 riscontri completi**, due parziali e 16 senza passaggio. La ripetizione ha coinciso con timeout di connessione verso più domini, confermati anche fuori da ALLMA. Il risultato generale varia con la raggiungibilità delle fonti. Per IPv6 il lettore può usare la specifica RFC 4291 quando la pagina italiana è indisponibile. [IETF · RFC 4291](https://www.rfc-editor.org/info/rfc4291/)

La 0.9.1.34 ha superato **7 prove su 7** sul Galaxy S25 Ultra, inclusi il globo spento e il blocco delle richieste su un indirizzo personale. La 0.9.1.35 recupera anche le definizioni Python che terminano con i due punti prima di un esempio e conserva gli underscore nei nomi speciali come `__enter__`. Entrambe le correzioni sono state confermate sul Galaxy con la 0.9.1.35 installata. La preferenza Internet precedente è stata ripristinata. La suite locale conta **3.345 test superati**.

## Energia e ambiente nella 0.9.1.36

ALLMA cerca un passaggio che sostenga la relazione richiesta. Per l’eolico il passaggio deve spiegare il legame tra vento, rotazione e produzione di elettricità. Per l’Accordo di Parigi deve riportare il limite ben al di sotto dei 2 °C, gli sforzi per limitarlo a 1,5 °C e il riferimento ai livelli preindustriali. Per la geotermia deve spiegare da dove viene l’energia. Con la fonte INGV simulata come indisponibile, ALLMA ha letto il passaggio della fonte universitaria di riserva. [Assolombarda](https://www.assolombarda.it/transizione-energetica/energia-rinnovabile-elettrica/eolico/intro) · [ONU](https://www.un.org/en/climatechange/science/climate-issues/degrees-matter) · [INGV](https://pulse.ingv.it/calore/) · [Università di Padova](https://ilbolive.unipd.it/it/news/scienza-ricerca/energia-geotermica-sguardo-dinsieme-fonte)

| Misura sulle otto domande originali | 0.9.1.35 | 0.9.1.36 |
|---|---:|---:|
| Riscontro completo dopo la lettura del passaggio | 2/8 (25%) | 8/8 (100%) |
| Riscontro parziale dopo la lettura del passaggio | 1 | 0 |
| Nessun passaggio pertinente | 5 | 0 |
| Latenza mediana della ricerca sul Mac | 2,82 s | 0,44 s |

Il confronto usa otto domande di [`internet_coverage_v2.json`](../benchmarks/evaluation/internet_coverage_v2.json), la 0.9.1.35 estratta dall’APK e i sorgenti della build 102628. Le prove usano fonti pubbliche, preferenze temporanee e SearXNG disattivato. La mediana misura il recupero del passaggio e varia con la raggiungibilità delle fonti. Il controllo lessicale ha trovato tutte le parole attese in cinque casi originali e sei varianti. Negli altri casi la verifica del testo ha riconosciuto formulazioni equivalenti, come il pompaggio espresso da «pumps» e il filtro UV descritto da «bloqueia». Tutte le [otto riformulazioni](../benchmarks/evaluation/internet_energy_variants.json) hanno restituito un passaggio completo dopo revisione, sugli stessi argomenti in italiano, spagnolo, inglese, francese e portoghese.

La suite locale conta **3.349 test superati**. Le nuove prove coprono il legame causale per l’eolico, i due obiettivi climatici, l’assorbimento e lo stoccaggio del carbonio e la fonte di riserva per la geotermia.

Sul Galaxy S25 Ultra, la build **102628** ha superato **6 prove su 6**. La chat ha mostrato cinque risposte con fonte e senza avvisi di incompletezza. La geotermia ha usato la fonte universitaria di riserva. A globo spento la richiesta esplicita di ricerca è rimasta offline. Al termine è stata ripristinata la preferenza Internet precedente.

## Recupero delle ricerche senza riscontro nella 0.9.1.37

Quando il primo giro non trova un passaggio utile, ALLMA riformula la ricerca usando il dato richiesto, per esempio una data, un autore o un confine. Tiene traccia delle revisioni già tentate e può proseguire dopo l’errore di una singola pagina. Se il motore configurato risponde senza riscontri utilizzabili, può consultare l’indice pubblico di riserva entro il limite di tempo già in uso. Le anteprime servono a ordinare i candidati. Per citare un passaggio, ALLMA continua a leggere la pagina e a controllare la relazione richiesta.

| Misura sul Mac con fonti reali e SearXNG disattivato | 0.9.1.36 | 0.9.1.37 |
|---|---:|---:|
| Risposte pertinenti sulle otto domande prima senza riscontro | 0/8 | 6/8 |
| Tutte le parole attese sulle stesse otto domande | 0/8 | 4/8 |
| Latenza mediana sulle otto domande | 6,12 s | 2,14 s |
| Riscontri completi sulle [dieci domande aggiuntive](../benchmarks/evaluation/internet_recovery_holdout.json) | 2/10 | 3/10 |

Tra gli otto casi iniziali, le date del referendum italiano e dell’inizio dell’indipendenza messicana risultano pertinenti dopo la lettura del testo. Il controllo di parole attese segnala rispettivamente la formulazione con i giorni della settimana e l’assenza di Miguel Hidalgo nella frase che riporta la data d’inizio. Restano senza riscontro la proclamazione dell’indipendenza del Brasile e la Nona di Beethoven nella domanda che cita l’Inno alla gioia.

Nella prova sulle domande aggiuntive una fonte datata sul trattato di Maastricht del 1843 era stata scambiata per l’opera omonima. La build finale scarta la voce con l’anno nel titolo quando la domanda riguarda un titolo privo di quella specificazione. La ripetizione della prova ha restituito un esito senza riscontro. Il controllo mantiene la distinzione tra un risultato assente e una data trovata per un altro soggetto.

Nel giro generale sulle 48 domande, gli esiti senza riscontro sono scesi da **8 a 3**. Le corrispondenze lessicali complete sono passate da 35 a 37 e quelle parziali da 5 a 8. Il Museo del Prado era l’unica domanda che aveva perso il riscontro. In una prova separata, dopo l’intervento sull’estrazione delle frasi adiacenti, la ricerca ha nuovamente trovato Madrid nel testo della fonte.

La suite finale conta **3.355 test superati**. L’APK 102629 è compilata e verificata. Al termine del controllo il Galaxy era bloccato e il collaudo Android restava da eseguire.

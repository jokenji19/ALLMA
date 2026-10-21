# Confronto ALLMA / modello — 13 ottobre 2026

Riferimento di rilascio: V0.9.0.0, commit 62d3e49. Il profilo `comparison` è strumentazione aggiunta a quel codice, non una nuova release pubblicata. I fingerprint dei sorgenti, del dataset e del payload distinguono la build diagnostica dall’APK rilasciata. Non si deve presentare la prova come esecuzione bit per bit dell’APK di release.

## Protocollo

Quattro nuovi casi: aritmetica, deduzione, JSON con calcolo e supporto emotivo misto. Ogni input viene eseguito una volta nella pipeline completa e una nel probe isolato; il seed è uguale nella coppia e l’ordine viene alternato tra coppie. Budget richiesto 192 token totali, 48 di ragionamento; la pipeline conserva i limiti termici ed energetici, che possono ridurlo ulteriormente. Le differenze effettive dei parametri vengono indicate nel manifest invece di trattare automaticamente le prove come equivalenti.

Il core di prova usa storage temporaneo e condivide soltanto l’istanza nativa già caricata. Nessun accesso alla memoria personale della chat, nessuna conferma appresa, sogni disabilitati nel core temporaneo e background del core principale sospeso durante la misura. Il probe non scrive ricordi o preferenze. Le risposte esatte di riferimento sono usate soltanto dal valutatore; il codice di ALLMA non riceve le soluzioni del dataset.

Il probe usa il template nativo e un’istruzione minimale in italiano. Passa ancora dal wrapper, con limite di ragionamento e controllo lessicale dei loop: non è un confronto con un motore privo di qualsiasi controllo. La pipeline usa identità, contesto emotivo, prompt e vincoli finali; queste sono differenze intenzionali. I casi risolti senza modello sono indicati esplicitamente come bypass e non ricevono una falsa equivalenza di budget.

## Misure e limiti

Tempo end-to-end, metadati associati alla richiesta, token, arresto, parametri reali e condizioni prima/dopo ogni braccio. Il TTFT del wrapper può riferirsi al primo token di ragionamento, non alla prima parola visibile sullo schermo. I fingerprint del modello disponibili sono nome e dimensione, non una verifica crittografica del GGUF.

Le prove alternano l’ordine ma non azzerano la cache; non sono prove cold controllate. Le pause brevi non garantiscono raffreddamento. La diagnostica si ferma prima di una nuova inferenza se la temperatura della batteria raggiunge 41,5 °C e conserva il report parziale. Sensori mancanti sono N/D, non valori stimati. Non viene misurata energia consumata; un telefono USB in carica non permette di ricavare una percentuale di risparmio batteria.

Esattezza numerica, deduzione sì/no e JSON hanno controlli dichiarati. Il supporto emotivo e la qualità generale richiedono una rubrica umana. Il corpus è piccolo, costruito per questa diagnostica e noto dopo la pubblicazione: non è un benchmark indipendente. Nessun punteggio generale d’intelligenza e nessuna attribuzione causale automatica “colpa del modello” o “colpa di ALLMA”. Una coppia incompleta è segnalata, non conteggiata come completata.

## Accesso sul telefono

Impostazioni → Impostazioni avanzate → Diagnostica → Tipo di prova → **ALLMA / modello · 4 coppie** → Avvia benchmark. Sono 8 richieste complessive; lasciare l’app aperta. È possibile interrompere e salvare. Il report viene conservato in tre file (Markdown, risultati JSON, manifest JSON) e condiviso con il percorso esistente.

## Verifiche

64 test mirati superati, poi 149 controlli aggiuntivi superati (insiemi sovrapposti: non sommarli come test unici). Verificati ordine/seed delle coppie, due percorsi senza retry, bypass aritmetico, limiti di budget, arresto termico, annullamento durante il probe e report parziali. Controlli JavaScript della chat eseguiti con successo. APK diagnostica compilata, payload corrente verificato e installazione con conservazione dei dati riuscita. SHA256 `a4856fdd81e909226484a35b250462ab68cd09974b745e7e0e19e6bbac282c7d`. Processo Android 13283. Il pacchetto di release pubblicato rimane identico, SHA256 `2b512743f9cc53cc51d29d558c3220c1d10e03a07a45101780b2ee7427443206`. Collaudo completato: 4 coppie, 8 richieste. Risultati dettagliati in analisi/2026-10-13/confronto-pipeline-modello/ESITO_TELEFONO.md (directory esterna al repository). Calcolo diretto corretto; deduzione e JSON numerico errati su entrambi i percorsi; supporto emotivo meglio attribuito nella pipeline, ancora parziale. Nessuna percentuale generale di qualità derivata da quattro casi.

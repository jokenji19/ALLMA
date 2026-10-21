# Sensibilità al contesto e apprendimento del supporto — 102533

Questa modifica collega la lettura emotiva, il contesto recente e il modo di
rispondere già gestito da personalità e coalescenza. Non aggiunge una seconda
memoria personale, non modifica il GGUF e non richiede inferenze supplementari.

## Interpretazione del turno

`relational_perception` produce un piano temporaneo a partire dalle evidenze
del rilevatore emotivo esistente e dai messaggi dell'utente. Distingue emozioni
attuali, negate e dichiarate in precedenza. Una correzione esplicita prevale
sulle ipotesi precedenti. «Ho fallito ancora» è una ripetizione dichiarata,
non la prova di una particolare emozione né di altri episodi conosciuti.

«Lascia perdere» resta ambiguo: non diventa automaticamente tristezza o rabbia.
«Non voglio parlarne», quando costituisce l'intera richiesta, riceve invece
un riconoscimento immediato senza modello né domande aggiuntive. I messaggi
che contengono anche un altro compito non vengono consumati da questa scorciatoia.

Il contesto emotivo consulta al massimo quattro turni dell'utente negli ultimi
sedici messaggi e soltanto entro trenta minuti, nello stesso profilo e nella
stessa conversazione. Richiede date valide e attribuzione personale; non usa
le risposte del modello come prove. Un cambio di argomento interrompe il
trascinamento emotivo; i rinvii espliciti come «sto come prima» possono collegare
turni recenti, senza attraversare una chiusura esplicita dell'argomento.

I segnali passati sono presentati come contesto passato, mai come prova che
l'utente provi ancora la stessa emozione o abbia un certo carattere. Testi
troncati, esempi, citazioni, terze persone e ipotesi non sono promossi a ricordi
emotivi personali. I metadati aggiunti contengono etichette e provenienza,
non copie dei testi precedenti. I formati di risposta stretti restano prioritari.

## Ascolto e aiuto pratico

L'asse `support_mode` estende la personalità esistente. «Voglio solo sfogarmi»
e «Dammi consigli pratici» sono richieste del momento: non diventano preferenze
stabili nemmeno semplicemente ripetendole. Negazioni, citazioni, condizioni e
richieste contraddittorie non vengono trasformate in scelte certe.

Una preferenza può essere dichiarata esplicitamente:

- «Quando sto male preferisco essere ascoltato senza consigli»;
- «Quando sto male preferisco suggerimenti pratici».

Si applica ai momenti di supporto, non a ogni domanda tecnica o informativa.
Una richiesta attuale diversa prevale. «Dimentica la mia preferenza di supporto»
revoca soltanto questo asse; il normale azzeramento dello stile resta disponibile.

Il percorso di apprendimento dagli esiti della coalescenza ora ammette anche
«Il tuo ascolto senza consigli mi è stato utile» e «I suggerimenti pratici mi
sono stati utili», comprese le forme negative. Il riscontro deve riferirsi a
una risposta originale, valida e completata, per la quale ALLMA abbia fornito
al generatore quella strategia. Un piano ricevuto non certifica da solo la
qualità semantica dell'esecuzione: l'utilità è valutata dall'utente.

Tre compiti distinti con riscontri espliciti sufficientemente concordi possono
integrare una tendenza. Conferme duplicate e ringraziamenti generici non
fabbricano nuove esperienze; una correzione può sospendere la tendenza. L'utilità
di consigli tecnici non viene usata per dedurre preferenze di supporto emotivo.
Questi stati riutilizzano salvataggio, recupero, isolamento e backup della
personalità esistente. Un errore di scrittura non modifica la personalità viva.

## Verifica e limiti

La diagnosi «Sensibilità e contesto · 12 scenari» usa archivi temporanei,
conversazioni sintetiche e generazione simulata. Controlla attribuzione,
incertezza, correzioni, confini, isolamento, persistenza, revoca, errori di
scrittura, apprendimento e collegamento al prompt del core reale.

Questo verifica il funzionamento del percorso software. Il rilevatore resta
euristico e può sbagliare; la qualità delle risposte reali dipende anche dal
modello. Non è una misura di coscienza, di emozioni soggettive o di comprensione
universale. Non si assegna una percentuale globale di miglioramento.

Nella regressione estesa sono stati aggiornati cinque casi precedenti di
`test_cognitive_persistence`: richiedevano il riuso parziale o la sostituzione
di un archivio danneggiato, in contrasto con la protezione già verificata da
`test_answer_recall_recovery`. Ora richiedono conservazione dell'originale,
sospensione del richiamo e ripresa soltanto dopo un ripristino valido. Il codice
di AnswerRecall non è stato modificato in questo intervento.

Evidenze e risultati finali:
`/Users/erikahu/ALLMA/analisi/2026-10-21/sensibilita-contesto/`.

Risultati completati: 860 test mirati superati, zero fallimenti o casi saltati;
60/60 scenari operativi sul Mac; 12/12 scenari della nuova diagnosi sul Mac e
12/12 sul telefono Android. APK 102533 installata, contenuto verificato e impronte
dei componenti installati corrispondenti ai sorgenti. Avvio di WebView, modello
e transizione rilevati; nessun indicatore tecnico di errore nei controlli.

Una misura locale su Mac di 200 esecuzioni del solo piano, con analisi corrente
già disponibile e un turno precedente, riporta mediana 0,311 ms e p95 0,371 ms.
Non è la latenza complessiva Android né una misura di risparmio della batteria.
La diagnosi del core verifica zero inferenze aggiuntive per questo collegamento.

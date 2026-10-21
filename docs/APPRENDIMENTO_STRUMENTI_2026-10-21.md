# Apprendimento procedurale degli strumenti — 102532

Questa modifica collega l'uso degli strumenti esatti all'esperienza persistente
di ALLMA. La prima strategia appresa riguarda il criterio di sovrapposizione
nei conteggi ambigui. L'instradamento generale delle richieste resta affidato
ai riconoscitori e ai controlli del core: non si addestra un nuovo parser né
si modificano i pesi del GGUF.

## Cosa cambia con l'esperienza

1. Un'operazione esatta, verificata dal sistema e salvata nella conversazione,
   produce una ricevuta di esecuzione. Il solo successo tecnico non equivale
   all'approvazione dell'utente.
2. Se l'utente sceglie esplicitamente il criterio dopo un chiarimento, il sistema
   conserva il riferimento a quella scelta. Una successiva «Risposta corretta»
   può approvarne l'utilità; «Risposta sbagliata» può correggere il riscontro.
3. Tre o più compiti diversi approvati e sufficientemente concordi possono
   sostenere una proposta su un nuovo compito. Si usa una stima con prior neutro
   e soglia di supporto: non è una percentuale di accuratezza o intelligenza.
4. La proposta chiede sempre conferma. «Sì» usa il criterio proposto e ricalcola
   il risultato sul testo nuovo. «No» lascia il criterio aperto; l'utente può
   specificare l'alternativa senza riscrivere gli operandi.
5. Le approvazioni delle proposte suggerite non rinforzano la stessa proposta.
   Un riscontro negativo può invece ridurne il supporto. Correggere una
   strategia non modifica la verità matematica del risultato già calcolato.

Esempio di trasferimento verificato: tre compiti con `ana/banana`, `aa/aaaa`
e `aba/ababa`, ciascuno seguito da una scelta esplicita e una conferma,
consentono una proposta per `issi/mississippi`. Il risultato `2` viene calcolato
sui nuovi operandi. Non viene recuperata una risposta «2» imparata a memoria.

Una singola scelta, un ringraziamento, tre conferme della stessa risposta o
la ripetizione dello stesso compito non bastano a creare tre esempi indipendenti.
Una correzione che contiene nuovi fatti non viene consumata come un semplice
riscontro sullo strumento.

## Memoria e integrazione

Il componente `ToolStrategyLearning` appartiene al `MetaLearningSystem` e usa
il database dei moduli già presente (`allma_modules.db`), incluso nel sistema
di backup. Non introduce un nuovo archivio di testi o una seconda memoria
autobiografica. Lo stato è separato per utente e contiene:

- conteggi cumulativi delle operazioni registrate;
- ricevute e riscontri recenti con identificatori e impronte;
- un insieme limitato di compiti distinti che sostengono o indeboliscono la
  proposta corrente;
- un'epoca per invalidare ricevute precedenti a un azzeramento e un checkpoint
  per il recupero delle registrazioni interrotte.

Si conservano al massimo 256 ricevute e 256 contributi di compiti recenti per
utente. Il sistema continua ad aggiornarsi entro questi limiti di memoria;
non pretende di conservare un numero infinito di esperienze dettagliate.
Non si salvano qui operandi, risposte numeriche o conversazioni complete.

Le esecuzioni entrano nel giornale di consegna esistente (`DeliveryUpdates`)
solo dopo il salvataggio della risposta e della sua provenienza. Il recupero
alla riapertura verifica utente, conversazione, contenuto, epoca e checkpoint.
Un arresto fra salvataggio e conferma del giornale non conta due volte la stessa
esecuzione. Gli aggiornamenti dello stato avvengono in una transazione SQLite.
Uno stato malformato viene rifiutato e conservato, non sostituito con uno vuoto.

Gli strumenti restano utilizzabili se il salvataggio dell'apprendimento non
riesce. Un riscontro che non viene registrato produce un avviso esplicito.
Output del modello, risposte troncate, chiarimenti e operazioni fallite non
vengono promossi a esperienza esatta verificata.

## Controlli disponibili nella chat

- «Cosa hai imparato sui conteggi?» mostra operazioni registrate e compiti
  distinti confermati, distinguendoli dalla presenza di una proposta appresa.
- «Dimentica le strategie di conteggio apprese» azzera questo apprendimento
  dell'utente e invalida i vecchi riscontri. Le conversazioni restano salvate.

L'attività effettiva del componente compare nel nodo di meta-apprendimento
della visualizzazione del cervello.

## Verifiche

534 test mirati superati, senza fallimenti o casi saltati, compresi arresti
improvvisi reali dei processi. I due fallimenti iniziali dei sottoprocessi
OpenMP nella sandbox sono stati rieseguiti fuori da tale restrizione e superati.

La nuova diagnosi «Apprendimento strumenti · 12 scenari» esegue un confronto
prima/dopo attraverso il core reale, su archivi temporanei e con un modello
che solleva un errore se chiamato. Verifica nascita senza preferenze, soglia,
approvazione, trasferimento, duplicati, correzioni, isolamento, riapertura,
azzeramento, guasto di scrittura e assenza di autorinforzo. Su Mac: 12/12.
Sul telefono Android, build 102532 installata: 12/12 in 3,12 secondi. Nel caso
di trasferimento il report conferma tre compiti distinti approvati, una proposta
assente prima e presente dopo, risultato `2` sul nuovo testo e nessuna chiamata
al modello. Verificati anche i byte dei componenti installati rispetto ai sorgenti.

La batteria operativa separata sul Mac supera inoltre 60/60 scenari. I tre
insiemi di verifiche non sono un campione indipendente di tutti gli usi possibili
e non consentono di assegnare una percentuale globale di affidabilità ad ALLMA.

Questa prova non allena il profilo personale dell'utente e non misura la qualità
del modello esterno, l'intelligenza generale, consumi o temperatura.

Evidenze: `/Users/erikahu/ALLMA/analisi/2026-10-21/apprendimento-strumenti/`.

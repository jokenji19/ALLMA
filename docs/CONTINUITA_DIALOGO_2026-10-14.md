# Correzioni della conversazione su ALLMA

La verifica sul Samsung ha individuato: risposta identitaria sostitutiva
non pertinente al saluto; confusione ALLMA/modello; tentativi ripetuti
confrontati con una domanda più vecchia dopo un blocco; consegna completa
forzata anche nei nuovi argomenti; risposta invalida segnata `completed`.

## Interventi

* La continuità usa una cronologia dei tentativi per riconoscere una domanda
  ripetuta dopo un fallimento. Non usa il contenuto della risposta invalida
  come prova o come risposta precedente. La correzione «non ripetere» mantiene
  la protezione e non autorizza a riproporre il testo.
* Il saluto già soddisfatto non impone più la consegna completa dei turni
  successivi. La prima risposta al saluto resta protetta prima della consegna;
  negli altri turni lo streaming controlla le domande sul benessere prima
  di emetterle, anche se vengono spezzate tra token.
* Domande dirette supportate su funzionamento, emozioni e modello ricevono
  informazioni sui sistemi presenti. La descrizione non è un vissuto,
  una preferenza né una prova di esperienza soggettiva. Non aggiunge nuovi
  fatti autobiografici originari: il nome resta l'unico dato originario.
* Un chiarimento dopo un blocco spiega la ragione registrata dal controllo;
  dopo una descrizione del sistema chiarisce quella descrizione. Non riprende
  il candidato invalido e non richiede il modello per questi intenti limitati.
* Una sostituzione identitaria conserva fonte `identity_guard_notice`,
  motivo `identity_conflict` o `unsupported_personal_claim` e validità falsa.
  Non viene più etichettata come risposta modello completata, né appresa.

Le protezioni su emozioni attribuite, ripetizioni tra turni e ricordi
inventati restano attive. Non sono state aggiunte riscritture silenziose
dei ricordi esistenti o raccolte di candidati dalle conversazioni personali.

## Verifica

Test mirati: 111 passati prima dell'integrazione del benchmark. La batteria
invariata di affidabilità passa 60/60 sul Mac.
È disponibile «Dialogo su ALLMA · 6 turni» nella diagnostica: dati temporanei,
sei richieste nella stessa conversazione sintetica, controllo sull'assenza
di chiamate al modello e rubriche di pertinenza. Non misura la qualità
generale del GGUF e non certifica ogni possibile formulazione linguistica.

Le richieste complesse, quelle con formati specifici e altre formulazioni
continuano attraverso la pipeline ordinaria. Il recupero dopo un fallimento
non garantisce che un modello produca una buona nuova risposta.

## Esito finale

Suite completa: 1006 passati, 15 saltati, 11 avvisi in 129,14 secondi.
APK verificata e installata conservando i dati: versione 0.9.0.0,
codice 102462, SHA256
`274d11cba89e1f1036bc1838293b61577d9cccc51dffabdc57d4c79278c2e629`.

Sul Samsung, sessione sintetica `498a3880c9fa410bb51ba89aab7cf5cf`, test D1.
Tutti i sei turni hanno `is_valid=true` e `llm_used=false`; nessun avviso
di blocco. Tempi di elaborazione: 23,99 / 15,53 / 12,64 / 10,90 / 11,31 /
12,28 millisecondi. Escludono avvio, caricamento, disegno della UI e TTS;
non sono una misura di accelerazione del modello. La descrizione è stabile
e può ripetersi se viene posta di nuovo la stessa domanda.

La batteria invariata sul runtime Android passa 60/60. Non certifica ogni
modulo, ogni domanda o la verità delle risposte del GGUF. I file diagnostici
sono in `/Users/erikahu/ALLMA/analisi/2026-10-14/affidabilita/continuita-dialogo/`.
Sono stati ripristinati lo schermo sempre acceso e il forwarding ADB.

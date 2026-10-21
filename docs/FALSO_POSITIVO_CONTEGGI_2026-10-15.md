# Falso positivo di attribuzione nei conteggi

Turno reale esaminato: domanda sulle sette palline, due rimosse. L'utente ha
visto prima il risultato 5 e poi l'avviso sulle esperienze personali. Il log
conferma finish=stop e successivo subject_mismatch: non era un taglio di token.
Il testo finale grezzo non viene conservato dalla chat normale; la specifica
formulazione del candidato nativo scartato non è quindi disponibile qui.

Riproduzione deterministica: borrowed_user_experience respingeva
«Rimangono 5 palline. All’inizio ci sono 7 palline e ne vengono tolte 2.».
La regex trattava il sono esistenziale come prima persona e l'intersezione di
7/palline con la domanda come appropriazione autobiografica.

Correzione circoscritta: ci sono/vi sono esistenziali vengono esclusi a livello
di singola proposizione. Le forme locative personali, come ci sono stata,
e le successive affermazioni personali continuano a essere controllate.
Non viene disattivata la protezione per tutte le domande numeriche.

Inoltre il fallback non viene più inviato come un altro pezzo di risposta
quando esiste già un'anteprima emessa. Il risultato finale autorevole della UI
sostituisce l'anteprima, evitando l'accodamento di risposta più avviso.
Le vere violazioni restano bloccate; nessuna risposta corretta viene inventata
per sostituire una generazione rifiutata.

Verifiche finali: 71 test su contratti/attribuzione e continuità, più 5 del core,
tutti superati. Coperti conteggi con numeri e parole, ripetizione delle premesse,
ci sono stata/vi sono già stata, affermazione personale dopo una frase lecita,
streaming del risultato corretto e blocco finale senza accodare il fallback.


APK 102479, versione 0.9.0.0, payload e runtime ARM64 qwen35 verificati.
SHA256: e9868dd7202726e7959a10a947015ce5651337c649b027ed39614a22b8825b2f.
La ripetizione reale sul telefono richiede il nuovo turno dell'utente dopo
l'installazione: i test simulati non sostituiscono questo riscontro.

Installazione con mantenimento dati riuscita sul telefono.

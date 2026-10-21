# Supporto emotivo concreto — 13 ottobre 2026

Il confronto precedente aveva mostrato che ALLMA distingue l’utente da sé, ma trascura la soddisfazione per il corso e risponde genericamente sull’ansia. Rilevare due emozioni nei metadati non garantisce che la risposta le accolga entrambe.

## Correzioni

- Gli indizi nel prompt conservano le chiavi diagnostiche e aggiungono nomi italiani (gioia, ansia, orgoglio, sollievo, ecc.). Restano ipotesi sull’utente, con negazioni, altro soggetto e incertezza separati.
- Il modello riceve una direttiva breve per riconoscere le emozioni coesistenti nella situazione concreta, mantenere il formato richiesto e proporre aiuto pertinente quando offre supporto. Evitare discorsi astratti sulle emozioni e suggerimenti automatici. Nessuna risposta preconfezionata al benchmark, seconda inferenza o riscrittura nascosta.
- L’adattatore emotivo usa un tono equilibrato per gli stati misti, anziché scegliere soltanto il tono della famiglia primaria. Le sfumature rilevanti possono contribuire con due direttive distinte al massimo. Non viene aggiunta una famiglia negativa quando le emozioni espresse sono tutte positive.
- L’adattatore di personalità considera le famiglie secondarie: gioia predominante con tristezza o paura non aumenta automaticamente l’umorismo. Rimane il controllo di confidenza prima di adattare lo stile.
- Il default “Stile bilanciato” e il valore diagnostico “Formalità: 0.50” non aggiungono direttive al prompt. I moduli continuano a produrre osservazioni e statistiche; richieste di stile esplicite e direttive concrete restano nei percorsi esistenti.
- Corretto il confine della negazione prima di una nuova dichiarazione personale dopo i due punti: «non sono triste: sono sollevata» non deve negare il sollievo. Il nuovo confine richiede un verbo personale esplicito; «non sono: triste» mantiene la negazione. Attribuzione e offset delle evidenze restano separati.

## Prova breve

Diagnostica → **Supporto emotivo · 3 casi**. Un caso già misurato (S4, stesso input e seed) e due nuovi casi di orgoglio/tristezza e sollievo con emozione di un’altra persona. Una generazione per caso, 48 token di ragionamento e 144 riservati alla risposta. Storage isolato e arresto termico come nel confronto precedente. Le verifiche sulle famiglie misurano solo il detector nei metadati; la qualità del testo e la completezza del supporto richiedono la rubrica umana.

Questi esempi sono diagnostici di sviluppo, non una validazione indipendente né una garanzia di comprensione universale. Dopo avere corretto un errore emerso da un esempio, quel caso non può essere trattato come prova cieca. Nessuna percentuale di qualità o prestazioni assegnata prima del collaudo.

## Verifiche in corso

Il primo gruppo ha evidenziato tre problemi di verifica: una direttiva doveva mantenere l’indicazione “miste” e due nuovi test importavano il nome sbagliato dell’adattatore. Correzioni applicate; suite completa con **880 test superati, 15 saltati, 7 warning**, 183,00 s. Dopo gli ultimi aggiustamenti della negazione e delle direttive miste, **190 controlli finali superati**, 19,66 s. Gli insiemi si sovrappongono, non sommare come test unici. Il nuovo detector riconosce il sollievo nel caso con negazione e soggetto distinto. APK finale compilata e payload verificato, SHA256 `4ea2be22009fa13e0364350380d73ec7bf31b33267a061a50be13a903c8c75d2`. Installata con `-r`, conservando i dati. Prova telefonica ancora da avviare; nessun miglioramento della qualità del testo dichiarato prima del report. Release GitHub invariata; modifiche locali salvate.

## Collaudo completato

Tre casi eseguiti: S4 ora menziona gioia e ansia ma resta generico; T1/T2 bloccati per attribuzione in prima persona dell’esperienza dell’utente. Detector corretto nei metadati dei tre esempi. Tempi 34,27/23,40/24,07 s; nessuna percentuale generale di qualità o velocità. Temperatura batteria 38,6 → 39,8 °C, USB in carica. Il dettaglio è conservato in `analisi/2026-10-13/supporto-emotivo/ESITO_TELEFONO.md`, esterno al repository. Il problema della riformulazione in prima persona rimane aperto.

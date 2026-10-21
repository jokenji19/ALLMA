# Collaudo ALLMA sul telefono — 14 ottobre 2026

**Telefono reale: Samsung SM-S938B. APK aggiornata installata con `adb install -r`, senza disinstallazione o cancellazione dei dati.** Versione 0.9.0.0, versionCode 102458. SHA-256 del base.apk installato corrisponde alla build verificata: `c65c8c39af25a4aea87f6d6c89454fc5f568200689e323c00dcaf3f49a8db9d1`.

## 1. Affidabilità software nel runtime Android

**95%: 57 scenari superati su 60**, in circa 2,02 secondi. Stessi casi e stessi esiti del Mac. Sei categorie da dieci scenari; criteri invariati. Archivi temporanei e risposte del modello programmate: questa percentuale non misura la qualità del GGUF né tutti i comportamenti della UI nativa.

Fallimenti confermati su Android:

- Scrittura di un messaggio fallita: il messaggio resta soltanto in RAM.
- Aggiornamento del contesto fallito: il nuovo contesto resta soltanto in RAM.
- Vincolo di due frasi: testo di tre frasi con citazione viene lasciato passare.

I guasti simulati sono applicati alle sole istanze temporanee, non alla memoria dell’app aperta. Nessuna modifica dei difetti prima del confronto.

## 2. Pipeline con il GGUF reale

Sei casi del benchmark Rapida eseguiti e completati. Modello `qwen3-1.7b-q8_0.gguf`, 1.834.426.016 byte, già caricato. Cinque richieste usano il modello, il calcolo è risolto dal percorso esatto di ALLMA. Stato del benchmark isolato dalla memoria personale.

| Caso | Esito osservato | Secondi |
|---|---|---:|
| N1 | Deduzione e formato sì/no corretti: `no`. | 7.13 |
| N2 | Calcolo corretto: `42`, senza LLM. | 0.02 |
| N3 | JSON e valori corretti: totale 8, pari true. | 8.67 |
| N4 | Emozioni riconosciute, ma risposta bloccata dal controllo di attribuzione; manca un conforto utile. | 12.30 |
| N5 | Tre frasi prodotte; terminologia e accuratezza richiedono revisione. | 16.02 |
| N6 | Errore di soggetto: alla domanda sul colore dell’utente risponde sul proprio colore. | 9.82 |

**Controlli automatici della pipeline: 3/4 = 75%.** I due casi privi di verifiche automatiche non entrano nel denominatore. N6 è valutato separatamente come errore di allineamento del soggetto; N5 resta da validare. Questa non è una percentuale globale di intelligenza, affidabilità o qualità delle risposte.

N4 non conserva nel report il candidato scartato: da questo report non si può distinguere con certezza un’appropriazione reale da un falso positivo del controllo. L’esito utile per l’utente è comunque fallito. I risultati originali non sono riscritti per adattarli alla valutazione.

Tempo medio per caso: 8.99 s, includendo il calcolo senza LLM. Nessun confronto causale con vecchie build, prompt e condizioni differenti.

## 3. Interruzione e lifecycle reali

Avviata una seconda Rapida e inviata l’azione normale «Interrompi e salva» mentre il modello generava il caso N3. Manifest `cancelled=true`, tre righe del report parziale salvate e caso interrotto non considerato risposta valida. Il processo ALLMA è rimasto lo stesso (PID 14307). Questo giro interrotto non viene contato come un test di qualità fallito né sommato ai sei casi completati.

Tre passaggi Home → ALLMA. La WebView è rimasta pronta e sono stati osservati gli eventi Python «Pausing», «Memory saved on pause» e «Resumed». Nessun riavvio del processo. Non certifica ogni possibile sequenza di lifecycle o ogni callback.

## Temperature e limiti

Nel giro completo GGUF la temperatura batteria è passata da **37,6°C a 38,7°C**. Il telefono era collegato e in carica, con batteria al 100%: non è una misura attendibile del consumo a batteria. I log riportano anche picchi di sensori CPU/SoC durante l’inferenza; non vanno confusi con la temperatura batteria. Non è un collaudo termico prolungato.

Microfono, lettura vocale fisica, sessioni lunghe, tutti i moduli sperimentali e correttezza generale del modello non sono certificati da questa prova. L’APK aggiornata resta installata sul telefono. L’impostazione temporanea di schermo acceso è stata ripristinata a 0; forwarding USB diagnostico rimosso.

## Evidenze

- [Riepilogo verificabile](/Users/erikahu/ALLMA/analisi/2026-10-14/affidabilita/ANDROID_ESITO.json)
- [60 scenari sul runtime Android](/Users/erikahu/ALLMA/analisi/2026-10-14/affidabilita/android-runtime/summary.json)
- [Esiti caso per caso](/Users/erikahu/ALLMA/analisi/2026-10-14/affidabilita/android-runtime/results.json)
- [Risposte reali originali](/Users/erikahu/ALLMA/analisi/2026-10-14/affidabilita/android-gguf-results.json)
- [Manifest modello/seed/sorgenti](/Users/erikahu/ALLMA/analisi/2026-10-14/affidabilita/android-gguf-manifest.json)
- [Manifest interruzione](/Users/erikahu/ALLMA/analisi/2026-10-14/affidabilita/android-cancel-manifest.json)

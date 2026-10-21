# Notifiche di sistema con consenso — 15 ottobre 2026

Prima dell'intervento era presente POST_NOTIFICATIONS nel manifesto, chiesto
insieme agli altri permessi all'avvio. Non esistevano canale, invio né una
preferenza esplicita. Ora la richiesta runtime avviene soltanto attivando
Consenti le notifiche in Impostazioni → Notifiche. Il precedente permesso
Android eventualmente già concesso non viene interpretato come opt-in.

Implementazione: allma_model/ui/system_notifications.py, bridge Android,
UI impostazioni e collegamento agli eventi della chat. Preferenza e tempi
dell'ultimo invio in notifications.json, separati da memoria e identità.

- Default disattivato; consenso strettamente booleano e salvato atomicamente.
- Permesso Android e stato del canale controllati prima di ogni invio.
- Canale Aggiornamenti ALLMA, notifiche locali native apribili toccandole.
- Avvisi per iniziative validate, ciclo onirico con fase done e modello pronto.
- Messaggi generici: nessun testo personale inserito nella notifica.
- Un avviso per tipo ogni dieci minuti, con controllo persistente fra riavvii.
  Il pulsante esplicito di prova può ripetere la sola notifica test.
- Disattivazione rimuove gli avvisi dell'app; un esito tardivo del dialogo
  permessi non può riattivare l'impostazione spenta nel frattempo.
- Pulsante verso le impostazioni Android per blocchi di sistema/canale;
  stato aggiornato tornando all'app.

Non aggiunge inferenza in background, servizi permanenti, push cloud o sveglie.
I messaggi proattivi mantengono il loro requisito di app in primo piano;
gli avvisi sono emessi quando arrivano eventi dalle attività in esecuzione.
A processo terminato ALLMA non genera nuovi messaggi autonomi. Questa
limitazione è indicata anche nell'interfaccia.

Verifica: 21 test mirati passati, di cui 8 nuovi su consenso, rifiuto,
revoca, callback tardivo, persistenza, frequenza e invio fallito. Sintassi
JS/Python valida; payload e runtime ARM64 qwen35 verificati.

APK 102476, versione 0.9.0.0, installata mantenendo i dati.
SHA256: d2e19673cb3d51cd97de9e977f9623a67512a0acb032780c0c4f9efce0ece9ff.

Collaudo reale: l'utente ha attivato l'impostazione e premuto Invia una prova,
confermando «Sì, vedo la notifica». La WebView mostra consenso attivo,
pulsante prova disponibile, e notifications.json salva enabled=true.
Preferenza lasciata come scelta dall'utente; collegamento diagnostico rimosso.

Riferimento ufficiale per la richiesta nel contesto della funzione:
https://developer.android.com/develop/ui/views/notifications/notification-permission

## Icona dedicata

Build 102477 sostituisce ic_dialog_info con ic_allma_notification:
A aperta stilizzata e punto di curiosità/crescita, vettoriale 24dp monocromatico,
senza disco di sfondo. Risorsa Android aggiunta tramite android.add_resources;
lookup nel pacchetto dell'app, senza fallback silenzioso all'icona informativa.
Anteprima SVG in assets/web/allma-notification.svg, equivalente al vettore
Android in assets/android/drawable/ic_allma_notification.xml.

9 test mirati passati. AAPT2 conferma drawable/ic_allma_notification
con ID 0x7f010000. APK installata, SHA256:
9f41fe25b13419c838931bb9eab63714d0a615bd9b7d6031920b014f5a3d5119.
Prova nativa inviata con il consenso già scelto dall'utente. La singola
NotificationRecord ALLMA 7104 conferma icon=RESOURCE, pacchetto
org.allma.allma_prime e ID 0x7f010000, non android.R.ic_dialog_info.
Consenso preservato, collegamento diagnostico rimosso.
Anteprima: ../analisi/2026-10-15/notifiche/icona-allma.png dalla radice ALLMA_V4.

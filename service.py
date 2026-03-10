import time
import os
import sys
import logging
from jnius import autoclass
from android import api_version

# Configurazione logging minimo per il sub-processo
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [ALLMA_SRV] - %(message)s')

def start_foreground():
    """
    Solleva i permessi del Servizio Background ad "Android Foreground Service".
    Ciò protegge il processo dall'uccisione per App Standby / Doze Mode.
    Richiede una notifica persistente obbligatoria.
    """
    try:
        PythonService = autoclass('org.kivy.android.PythonService')
        mService = PythonService.mService
        Context = autoclass('android.content.Context')
        Intent = autoclass('android.content.Intent')
        PendingIntent = autoclass('android.app.PendingIntent')
        
        # Costruzione Notifica Android Nativa
        if api_version >= 26:
            NotificationChannel = autoclass('android.app.NotificationChannel')
            NotificationManager = autoclass('android.app.NotificationManager')
            channel = NotificationChannel(
                'allma_brain_channel', 
                'ALLMA Subconscio', 
                NotificationManager.IMPORTANCE_LOW # Importanza Low = Niente suono, solo icona fissa
            )
            getSystemService = mService.getSystemService
            notification_manager = getSystemService(Context.NOTIFICATION_SERVICE)
            notification_manager.createNotificationChannel(channel)
            
            NotificationBuilder = autoclass('android.app.Notification$Builder')
            builder = NotificationBuilder(mService, 'allma_brain_channel')
        else:
            NotificationBuilder = autoclass('android.app.Notification$Builder')
            builder = NotificationBuilder(mService)
            
        builder.setContentTitle('ALLMA')
        builder.setContentText('Cosciente in background...')
        # Utilizzo icona generica di sistema Kivy/Android
        app_context = mService.getApplicationContext()
        icon_id = app_context.getResources().getIdentifier('icon', 'drawable', app_context.getPackageName())
        builder.setSmallIcon(icon_id)
        
        # Avvia effettivamente il Foreground Service
        notification = builder.build()
        mService.startForeground(1, notification)
        logging.info("Elevazione a Foreground Service (Notifica persistente) Riuscita.")
        
    except Exception as e:
        logging.error(f"Errore fatale nell'elevazione a Foreground Service: {e}")

def main():
    logging.info("Avvio del Brain Service Indipendente...")
    start_foreground()
    
    # ---------------------------------------------------------
    # Qui andrà istanziato il DreamManager e l'EventBus in futuro.
    # Per ora creiamo un Heartbeat infinito per validare che Android
    # non ci uccida il thread. (Sleep 60s x consumo irrisorio)
    # ---------------------------------------------------------
    
    while True:
        try:
            # Heartbeat (solo per debug logcat)
            logging.info("Heartbeat Subconscio ALLMA: Vivo.")
            time.sleep(60)
        except Exception as e:
            logging.error(f"Eccezione nel ciclo di vita del daemon: {e}")
            time.sleep(10)

if __name__ == '__main__':
    main()

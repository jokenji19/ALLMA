import time
import os
import sys
import logging
try:
    from jnius import autoclass
    from android import api_version
except ImportError:
    autoclass = None
    api_version = 0

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

def _lazy_init_subconscious():
    """
    Inizializza il minimo indispensabile del motore ALLMA per girare in Background
    senza causare OOM (Out of Memory) crash al sistema operativo.
    """
    from allma_model.memory_system.conversational_memory import ConversationalMemory
    from allma_model.core.event_bus import EventBus
    from allma_model.llm.mobile_gemma_wrapper import MobileGemmaWrapper
    from allma_model.learning_system.incremental_learning import IncrementalLearner
    from allma_model.core.dream_system.dream_manager import DreamManager
    from allma_model.core.system_monitor import SystemMonitor

    logging.info("[SRV] Inizializzazione EventBus...")
    EventBus.get_instance()

    logging.info("[SRV] Inizializzazione SystemMonitor...")
    sys_monitor = SystemMonitor()

    logging.info("[SRV] Inizializzazione Memory DB...")
    # Condivide lo stesso file SQLite WAL gestito internamente dal VectorEngine e JSON
    memory = ConversationalMemory()

    logging.info("[SRV] Inizializzazione Incremental Learner...")
    learner = IncrementalLearner()

    logging.info("[SRV] Inizializzazione LLM (Background Mode)...")
    # Il Wrapper Mobile impone già in automatico 4_threads se è su Android per l'interazione in app, 
    # ma in background possiamo usarne persino solo 2 per estremo risparmio.
    # Evitiamo di forzarlo e lasciamo usare il default mobile_gemma_wrapper "smart".
    llm = MobileGemmaWrapper(
        models_dir="allma_model/weights",
        model_name="qwen2.5-coder-3b-instruct-q4_k_m.gguf",
        n_ctx=2048,
        system_monitor=sys_monitor
    )

    logging.info("[SRV] Inizializzazione DreamManager...")
    dreamer = DreamManager(
        memory_system=memory,
        incremental_learner=learner,
        system_monitor=sys_monitor,
        llm_wrapper=llm
    )
    
    return dreamer, sys_monitor

def main():
    logging.info("Avvio del Brain Service Indipendente...")
    start_foreground()
    
    dreamer = None
    sys_monitor = None
    
    try:
         dreamer, sys_monitor = _lazy_init_subconscious()
         logging.info("[SRV] Subconscio inizializzato con successo.")
    except Exception as e:
         logging.error(f"[SRV] Impossibile inizializzare il subconscio: {e}")
         return # Se fallisce brutalmente usciamo

    user_id = "user_default" # Hardcoded per ora come nell'app principale

    while True:
        try:
            # Check stato energetico
            metabolic = sys_monitor.get_metabolic_state() if sys_monitor else None
            
            # Decidi se sognare
            # Sogno completo se in carica. Altrimenti magari un garbage collector leggero.
            if metabolic and metabolic.is_charging:
                logging.info("[SRV] Dispositivo in carica. Inizio Ciclo REM Profondo.")
                dreamer.current_user_id = user_id
                
                # Esegui sincronamente per non sfuggire al try/except locale
                # (invece di usare check_and_start_dream che avvia un daemon thread parallelo sfuggente nel SRV)
                dreamer._dream_cycle() 
            else:
                logging.info("[SRV] Dispositivo a batteria. Mantenimento NREM.")
                # Magari in futuro esegui solo un compress dell'indice vettoriale.
            
            # Ciclo di Sonno Profondo tra un sogno e l'altro per Android Battery Management (1 ora)
            sleep_duration = 3600
            logging.info(f"[SRV] Ciclo concluso. Sospensione Background per {sleep_duration}s.")
            time.sleep(sleep_duration)

        except Exception as e:
            logging.error(f"[SRV] Eccezione nel ciclo di vita onirico del daemon: {e}")
            time.sleep(60) # Cortocircuito back-off

if __name__ == '__main__':
    # Creazione delle cartelle di lavoro se non esistono (avvio da zero in background)
    os.makedirs('data', exist_ok=True)
    os.makedirs('allma_model/weights', exist_ok=True)
    main()

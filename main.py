import os
import logging
import traceback
from kivy.app import App
from kivy.uix.label import Label
from kivy.utils import platform

# Configura logging aggressivo
if platform == 'android':
    from android.storage import app_storage_path
    log_dir = app_storage_path()
    log_file = os.path.join(log_dir, 'allma_debug.log')
    logging.basicConfig(filename=log_file, level=logging.DEBUG)

class DebugApp(App):
    def build(self):
        try:
            # Tenta di importare i moduli uno alla volta per vedere chi fallisce
            import kivymd.app
            logging.info("KivyMD imported successfully")
            
            from Model.core.allma_core import ALLMACore
            logging.info("ALLMACore imported successfully")
            
            return Label(text="ALLMA DEBUG MODE\n\nSe leggi questo, l'app base funziona.\nIl crash è altrove.")
        except Exception as e:
            logging.error(f"Import Error: {e}")
            return Label(text=f"ERRORE AVVIO:\n{str(e)}")

if __name__ == "__main__":
    try:
        DebugApp().run()
    except Exception as e:
        if platform == 'android':
            with open(os.path.join(app_storage_path(), 'crash_fatal.txt'), 'w') as f:
                f.write(traceback.format_exc())

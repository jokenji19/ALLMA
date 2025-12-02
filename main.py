import os
import logging
import traceback
from kivy.app import App
from kivy.uix.label import Label
from kivy.utils import platform

# Configura logging
if platform == 'android':
    from android.storage import app_storage_path
    log_dir = app_storage_path()
    log_file = os.path.join(log_dir, 'allma_nuclear_debug.log')
    logging.basicConfig(filename=log_file, level=logging.DEBUG)

class NuclearApp(App):
    def build(self):
        logging.info("NuclearApp build started")
        return Label(text="NUCLEAR DEBUG MODE\n\nPure Kivy Works!\nIf you see this, KivyMD is the culprit.")

if __name__ == "__main__":
    try:
        logging.info("Starting NuclearApp")
        NuclearApp().run()
    except Exception as e:
        logging.critical(f"CRASH: {e}")
        if platform == 'android':
            from android.storage import app_storage_path
            with open(os.path.join(app_storage_path(), 'crash_nuclear.txt'), 'w') as f:
                f.write(traceback.format_exc())

import os
import logging
import traceback
import threading
from kivy.app import App
from kivy.uix.label import Label
from kivy.utils import platform
from kivy.clock import Clock

# Configura logging
if platform == 'android':
    from android.storage import app_storage_path
    log_dir = app_storage_path()
    log_file = os.path.join(log_dir, 'allma_dep_test.log')
    logging.basicConfig(filename=log_file, level=logging.DEBUG)

class DepTestApp(App):
    def build(self):
        self.label = Label(text="TESTING DEPENDENCIES...\n\n1. Kivy: OK", halign="center")
        # Avvia il test in un thread separato per non bloccare la UI (e vedere l'aggiornamento)
        threading.Thread(target=self.run_tests).start()
        return self.label

    def update_text(self, text):
        Clock.schedule_once(lambda dt: setattr(self.label, 'text', self.label.text + "\n" + text))

    def run_tests(self):
        try:
            import time
            time.sleep(1) # Dai tempo alla UI di apparire
            
            # TEST 1: Pillow (PIL)
            self.update_text("2. Testing Pillow...")
            import PIL
            from PIL import Image
            self.update_text("   -> Pillow OK")
            time.sleep(0.5)

            # TEST 2: KivyMD
            self.update_text("3. Testing KivyMD...")
            import kivymd.app
            self.update_text("   -> KivyMD App OK")
            from kivymd.uix.screen import MDScreen
            self.update_text("   -> KivyMD Screen OK")
            time.sleep(0.5)
            
            # TEST 3: Model
            self.update_text("4. Testing Model...")
            from Model.utils.model_downloader import ModelDownloader
            self.update_text("   -> Model Downloader OK")
            
            self.update_text("\nALL TESTS PASSED! \nIf it crashes now, it's the logic.")

        except Exception as e:
            logging.critical(f"TEST FAILED: {e}")
            self.update_text(f"\nFAIL: {e}")
            if platform == 'android':
                from android.storage import app_storage_path
                with open(os.path.join(app_storage_path(), 'crash_dep_test.txt'), 'w') as f:
                    f.write(traceback.format_exc())

if __name__ == "__main__":
    try:
        DepTestApp().run()
    except Exception as e:
        logging.critical(f"CRASH: {e}")
        if platform == 'android':
            from android.storage import app_storage_path
            with open(os.path.join(app_storage_path(), 'crash_fatal.txt'), 'w') as f:
                f.write(traceback.format_exc())

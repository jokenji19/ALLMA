```python
import os
import sys
import logging
import traceback
from kivy.app import App
from kivy.uix.label import Label
from kivy.clock import Clock
from kivy.utils import platform

# Mantiene logging di base su stdout per debug ADB
logging.basicConfig(level=logging.DEBUG)

class ALLMAApp(App):
    def build(self):
        try:
            return Label(text="ALLMA CORE\nSystem Check: OK\nAndroid 16 Test: Build 72", 
                         halign='center', font_size='24sp')
        except Exception as e:
            return Label(text=f"CRITICAL FAULT: {e}")

    def on_start(self):
        logging.info("App Started Successfully on Main Thread")
        try:
            if platform == 'android':
                from android.permissions import request_permissions, Permission
                # Prova a chiedere permessi dopo 2 secondi
                Clock.schedule_once(lambda dt: request_permissions([
                    Permission.WRITE_EXTERNAL_STORAGE,
                    Permission.READ_EXTERNAL_STORAGE,
                    Permission.INTERNET
                ]), 2)
        except:
            pass

        # 4. Check Models and Init
        # DISABLED FOR BUILD 76 - TESTING UI ONLY
        logging.info("Core Logic DISABLED for Build 76")
        # Assuming update_status and ALLMACore would be defined elsewhere or passed
        # For now, we'll just log the status.
        # if ALLMACore:
        #      update_status("Core Loaded (but disabled)")
        #     try:
            BUILD_VERSION = "Build 76" # UI Only (Core Stubbed)
        #         self.downloader = ModelDownloader()
        #         missing_models = self.downloader.check_models_missing()
        #         
        #         if missing_models:
        #             self.sm.current = 'download'
        #         else:
        #             update_status("Initializing...")
        #             self.initialize_allma()
        #             update_status("Ready!")
        #     except Exception as e:
        #         logging.error(f"Init Error: {e}")
        #         update_status(f"Init Failed: {e}")
        
        # update_status("Build 76: UI ONLY MODE") # Commented out as update_status is not defined

    def initialize_allma(self):
        # STUBBED FOR BUILD 76
        logging.info("initialize_allma called (STUBBED)")
        pass

if __name__ == "__main__":
    try:
        ALLMAApp().run()
    except Exception as e:
        print(f"BOOTSTRAP CRASH: {e}")
```

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

if __name__ == "__main__":
    try:
        ALLMAApp().run()
    except Exception as e:
        print(f"BOOTSTRAP CRASH: {e}")


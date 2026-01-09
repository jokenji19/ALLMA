import os
import sys
import logging
import traceback
from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.label import MDLabel
from kivy.lang import Builder
from kivy.clock import Clock
from kivy.utils import platform

logging.basicConfig(level=logging.DEBUG)

class ALLMAApp(MDApp):
    def build(self):
        try:
            BUILD_VERSION = "Build 75 (KivyMD Diagnostic)"
            self.theme_cls.primary_palette = "Blue"
            self.theme_cls.theme_style = "Dark"
            
            screen = MDScreen()
            label = MDLabel(
                text="ALLMA KivyMD Diagnostic\nSystem OK\nBuild 75",
                halign="center",
                theme_text_color="Custom",
                text_color=(0, 1, 0, 1),
                font_style="H4"
            )
            screen.add_widget(label)
            return screen
        except Exception as e:
            # Fallback to Kivy Label if KivyMD fails inside build?
            logging.critical(f"KivyMD Build Crash: {e}")
            from kivy.uix.label import Label
            return Label(text=f"CRITICAL FAULT: {e}")

    def on_start(self):
         # Try permissions after UI load
         Clock.schedule_once(self.deferred_perms, 2)

    def deferred_perms(self, dt):
        try:
            if platform == 'android':
                from android.permissions import request_permissions, Permission
                request_permissions([
                    Permission.WRITE_EXTERNAL_STORAGE, 
                    Permission.READ_EXTERNAL_STORAGE, 
                    Permission.INTERNET
                ])
        except: pass

if __name__ == "__main__":
    try:
        ALLMAApp().run()
    except Exception as e:
        print(f"BOOTSTRAP CRASH: {e}")

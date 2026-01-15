
import os
import kivy
from kivy.app import App
from kivy.uix.label import Label
import allma_core

BUILD_VERSION = "Build 134-Flat"

class AllmaFlatApp(App):
    def build(self):
        print(f"Starting {BUILD_VERSION}")
        try:
            self.core = allma_core.AllmaCore()
            msg = self.core.process_message("test").content
            return Label(text=f"ALLMA {BUILD_VERSION}\n{msg}", halign="center")
        except Exception as e:
            return Label(text=f"Error: {e}", halign="center")

if __name__ == "__main__":
    AllmaFlatApp().run()

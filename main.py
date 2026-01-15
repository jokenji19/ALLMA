
import os
import sys
import kivy
from kivy.app import App
from kivy.uix.label import Label

# Build 135: Standard Import from Root Model Package
try:
    from Model.core.allma_core import AllmaCore
except ImportError as e:
    print(f"CRITICAL IMPORT ERROR: {e}")
    AllmaCore = None

BUILD_VERSION = "Build 136-Full"

class AllmaRootApp(App):
    def build(self):
        print(f"Starting {BUILD_VERSION}")
        if AllmaCore:
            try:
                # Initialize Core (might fail if missing dependencies)
                self.core = AllmaCore()
                # Dummy process call if possible, or just show success
                return Label(text=f"ALLMA {BUILD_VERSION}\nCore Imported Successfully!", halign="center")
            except Exception as e:
                return Label(text=f"ALLMA {BUILD_VERSION}\nCore Init Error: {e}", halign="center")
        else:
            return Label(text=f"ALLMA {BUILD_VERSION}\nImport Failed (See Log)", halign="center")

if __name__ == "__main__":
    AllmaRootApp().run()

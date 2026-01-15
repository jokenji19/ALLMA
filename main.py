
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

BUILD_VERSION = "Build 138-PathLogo"

# Build 138: Path Patch & Logo
import_error_message = ""
try:
    # CRITICAL FIX: Ensure root directory is in sys.path
    import os, sys
    root_dir = os.path.dirname(os.path.abspath(__file__))
    if root_dir not in sys.path:
        sys.path.append(root_dir)
        
    from Model.core.allma_core import AllmaCore
except ImportError as e:
    print(f"CRITICAL IMPORT ERROR: {e}")
    import_error_message = str(e)
    AllmaCore = None
except Exception as e:
    print(f"CRITICAL GENERIC ERROR: {e}")
    import_error_message = str(e)
    AllmaCore = None

BUILD_VERSION = "Build 138-PathLogo"

class AllmaRootApp(App):
    def build(self):
        print(f"Starting {BUILD_VERSION}")
        if AllmaCore:
            try:
                # Initialize Core (might fail if missing dependencies)
                self.core = AllmaCore()
                return Label(text=f"ALLMA {BUILD_VERSION}\nCore Imported Successfully!", halign="center")
            except Exception as e:
                # Capture Init Errors too
                return Label(text=f"ALLMA {BUILD_VERSION}\nCore Init Error:\n{str(e)}", halign="center")
        else:
            # Show the Import Error
            return Label(text=f"ALLMA {BUILD_VERSION}\nImport Failed:\n{import_error_message}", halign="center")

if __name__ == "__main__":
    AllmaRootApp().run()

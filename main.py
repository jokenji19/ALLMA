
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

BUILD_VERSION = "Build 142-DataZip"

# Build 141: ZipLoader Strategy
import_error_message = ""
try:
    import os, sys, shutil, zipfile
    root_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Define Extraction Path (Internal Storage)
    # On Android, use private storage. On Desktop, use ./unpacked_brain
    extract_path = os.path.join(root_dir, "unpacked_brain")
    # Build 142: Look in allma_data folder
    zip_path = os.path.join(root_dir, "allma_data", "allma_model.zip")
    
    # Logic: Prefer Folder > Zip
    # But if folder is missing (Android P4A issue), use Zip.
    
    # 1. Attempt direct import (in case Folder works)
    if os.path.exists(os.path.join(root_dir, "allma_model")):
         if root_dir not in sys.path: sys.path.append(root_dir)
         print("Found allma_model folder directly.")
         
    # 2. Attempt Zip Extraction
    elif os.path.exists(zip_path):
        print(f"Found Zip: {zip_path}. Extracting to {extract_path}...")
        if not os.path.exists(extract_path):
            os.makedirs(extract_path)
            
        # Unzip
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_path)
            
        # Add to Path
        if extract_path not in sys.path:
            sys.path.append(extract_path)
        print("Extraction complete and path added.")
        
    else:
        print("CRITICAL: Neither Folder nor Zip found.")
        
    # 3. Import
    from allma_model.core.allma_core import AllmaCore

except ImportError as e:
    print(f"CRITICAL IMPORT ERROR: {e}")
    # DEBUG: List contents to see if Zip exists in data folder
    try:
        files = os.listdir(root_dir)
        files_str = f"ROOT: {', '.join(files)}"
        
        data_dir = os.path.join(root_dir, "allma_data")
        if os.path.exists(data_dir):
            data_files = os.listdir(data_dir)
            files_str += f"\nDATA: {', '.join(data_files)}"
        else:
            files_str += "\nDATA: Folder Missing"
            
    except:
        files_str = "Error listing dir"
        
    import_error_message = f"{str(e)}\n{files_str}"
    AllmaCore = None
except Exception as e:
    print(f"CRITICAL GENERIC ERROR: {e}")
    import_error_message = str(e)
    AllmaCore = None

BUILD_VERSION = "Build 142-DataZip"

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

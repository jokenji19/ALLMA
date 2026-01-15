
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

BUILD_VERSION = "Build 146-Blob"

# Build 141: ZipLoader Strategy
import_error_message = ""
try:
    import os, sys, shutil, zipfile
    root_dir = os.path.dirname(os.path.abspath(__file__))
    try:
        print(f"🔍 ROOT DIR CONTENTS: {os.listdir(root_dir)}")
    except: pass
    
    # Build 146: Embedded Blob Strategy
    # The code is inside code_blob.py as a variable.
    # This bypasses all file/asset filters.
    
    zip_target_path = os.path.join(root_dir, "allma_model.zip")
    extract_path = os.path.join(root_dir, "unpacked_brain")
    
    # 1. Check if we need to extract (skip if already done/exists)
    if not os.path.exists(os.path.join(extract_path, "allma_model")):
        try:
            print("🧬 Importing Code Blob...")
            import code_blob
            
            print("💾 Writing Blob to Zip...")
            zip_bytes = code_blob.get_zip_bytes()
            with open(zip_target_path, "wb") as f:
                f.write(zip_bytes)
            print(f"✅ Zip created: {len(zip_bytes)} bytes.")
            
            # Extract
            print(f"📦 Extracting to {extract_path}...")
            with zipfile.ZipFile(zip_target_path, 'r') as zip_ref:
                zip_ref.extractall(extract_path)
            print("✅ Extraction Complete.")
            
        except ImportError:
            print("❌ CRITICAL: code_blob.py missing!")
        except Exception as e:
            print(f"❌ Blob Error: {e}")

    # 2. Add to Path
    if os.path.exists(extract_path):
        if extract_path not in sys.path:
            sys.path.append(extract_path)
        print(f"📚 Added {extract_path} to sys.path")
    else:
        print("⚠️ Extraction path missing after attempts.")
        
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

BUILD_VERSION = "Build 146-Blob"

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

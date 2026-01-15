
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

BUILD_VERSION = "Build 147-Debug"

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
    
    # Build 147: Sherlock Holmes Debug
    zip_target_path = os.path.join(root_dir, "allma_model.zip")
    extract_path = os.path.join(root_dir, "unpacked_brain")
    
    print("🕵️ STARTING BLOB EXTRACTION SEQUENCE")
    
    # Step 1: Import Blob
    try:
        print("Step 1: Importing code_blob...")
        import code_blob
        print("✅ code_blob imported.")
    except ImportError as e:
        print(f"❌ Step 1 FAILED: Could not import code_blob! {e}")
        print(f"Directory Contents: {os.listdir(root_dir)}")
        
    # Step 2: Write Zip
    try:
        print("Step 2: Getting bytes...")
        zip_bytes = code_blob.get_zip_bytes()
        print(f"Got {len(zip_bytes)} bytes.")
        
        print(f"Writing to {zip_target_path}...")
        with open(zip_target_path, "wb") as f:
            f.write(zip_bytes)
        print("✅ Zip written to disk.")
    except Exception as e:
        print(f"❌ Step 2 FAILED: {e}")

    # Step 3: Extract
    try:
        print(f"Step 3: Extracting to {extract_path}...")
        if not os.path.exists(extract_path):
            os.makedirs(extract_path)
            
        with zipfile.ZipFile(zip_target_path, 'r') as zip_ref:
            # Debug: List zip contents first
            print(f"Zip File Names (First 5): {zip_ref.namelist()[:5]}")
            zip_ref.extractall(extract_path)
        print("✅ Extraction Complete.")
        
        # Verify
        extracted_model_path = os.path.join(extract_path, "allma_model")
        if os.path.exists(extracted_model_path):
            print(f"✅ Verified: {extracted_model_path} exists.")
            print(f"Contents: {os.listdir(extracted_model_path)}")
        else:
            print(f"⚠️ Warning: {extracted_model_path} does NOT exist after extraction.")
            print(f"Unpacked root contents: {os.listdir(extract_path)}")

    except Exception as e:
        print(f"❌ Step 3 FAILED: {e}")

    # Step 4: Add to Path
    if extract_path not in sys.path:
        sys.path.append(extract_path)
    print(f"📚 sys.path updated. Current path: {sys.path}")
    
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

BUILD_VERSION = "Build 147-Debug"

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

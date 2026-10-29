
import re
import base64
import zipfile
import io
import os

MAIN_PY_PATH = "/Users/erikahu/ALLMA/MODELLO_SVILUPPO_ALLMA(versione 4 stabile)/main.py"

def fix_code_blob():
    print(f"Reading {MAIN_PY_PATH}...")
    try:
        with open(MAIN_PY_PATH, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        print(f"Failed to read main.py: {e}")
        return

    # Extract ZIP_DATA lines
    # It might be multiline or single line.
    # The view_file output showed "ZIP_DATA = b'UEsDBBQAAAAAAM5...'" on line 5.
    # It is likely a single long line or byte literal.
    
    # We use regex to find it.
    match = re.search(r"(ZIP_DATA\s*=\s*b')(.+?)(')", content, re.DOTALL)
    if not match:
        print("Could not find ZIP_DATA in main.py")
        return

    start_marker = match.group(1)
    old_b64 = match.group(2)
    end_marker = match.group(3)
    
    print("Found ZIP_DATA. Decoding...")
    try:
        zip_bytes = base64.b64decode(old_b64)
    except Exception as e:
        print(f"Failed to decode base64: {e}")
        return

    new_zip_io = io.BytesIO()
    
    count_files_fixed = 0
    
    print("Processing zip contents...")
    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes), 'r') as old_z:
            with zipfile.ZipFile(new_zip_io, 'w', compression=zipfile.ZIP_DEFLATED) as new_z:
                for item in old_z.infolist():
                    file_data = old_z.read(item.filename)
                    
                    if item.filename.endswith(".py"):
                        try:
                            text_data = file_data.decode("utf-8")
                            
                            # Perform replacements
                            new_text_data = text_data
                            
                            # Replace "from Model" with "from allma_model"
                            if "from Model" in new_text_data:
                                new_text_data = new_text_data.replace("from Model", "from allma_model")
                            
                            # Replace "import Model" with "import allma_model"
                            if "import Model" in new_text_data:
                                new_text_data = new_text_data.replace("import Model", "import allma_model")
                                
                            if new_text_data != text_data:
                                file_data = new_text_data.encode("utf-8")
                                count_files_fixed += 1
                                # print(f"Fixed imports in {item.filename}")
                                
                        except UnicodeDecodeError:
                            # If not text (e.g. binary), skip text replacement
                            pass
                    
                    new_z.writestr(item, file_data)
                    
    except Exception as e:
        print(f"Failed to process zip: {e}")
        return

    print(f"Fixed {count_files_fixed} files in zip.")
    
    print("Encoding new zip data...")
    new_b64 = base64.b64encode(new_zip_io.getvalue()).decode('utf-8')
    
    # Verify the regex again ensuring we replace ONLY the base64 part safely
    # If the file is huge, string replacement might be slow or memory intensive but needed.
    
    new_content = content[:match.start(2)] + new_b64 + content[match.end(2):]
    
    print("Writing back to main.py...")
    try:
        with open(MAIN_PY_PATH, "w", encoding="utf-8") as f:
            f.write(new_content)
        print("Done. ZIP_DATA updated.")
    except Exception as e:
        print(f"Failed to write main.py: {e}")

if __name__ == "__main__":
    fix_code_blob()

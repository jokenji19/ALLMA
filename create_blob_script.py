import base64
import os

def create_blob():
    # Source: The zip file
    source_path = "allma_model.zip"
    target_path = "code_blob.py"
    
    if not os.path.exists(source_path):
        print(f"Error: {source_path} not found.")
        return

    print(f"Reading {source_path}...")
    with open(source_path, "rb") as f:
        data = f.read()
        
    encoded = base64.b64encode(data)
    
    print(f"Encoding {len(data)} bytes to base64...")
    
    content = f'''# ALLMA Code Blob
# Auto-generated. Do not edit.
import base64

ZIP_DATA = {encoded}

def get_zip_bytes():
    return base64.b64decode(ZIP_DATA)
'''
    
    with open(target_path, "w") as f:
        f.write(content)
        
    print(f"Success! Created {target_path} ({len(content)} bytes).")

if __name__ == "__main__":
    create_blob()

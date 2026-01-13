import os
import zipfile
import base64
import sys

def generate_embedded():
    source_dir = 'libs/Model'
    # Create zip in memory or temp file
    zip_filename = 'temp_lite_model.zip'
    
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(source_dir):
            if '__pycache__' in dirs:
                dirs.remove('__pycache__')
            
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    # Arcname: libs/Model/... -> Model/...
                    # We want imports to work like 'from Model.core import ...'
                    # So inside zip we need 'Model/core/...'
                    
                    # Relpath from libs: libs/Model/core/x.py -> Model/core/x.py
                    arcname = os.path.relpath(file_path, 'libs')
                    zf.write(file_path, arcname)
                    print(f"Adding: {arcname}")

    # Read and encode
    with open(zip_filename, 'rb') as f:
        data = f.read()
    
    b64_str = base64.b64encode(data).decode('utf-8')
    print(f"\nTotal Zip Size: {len(data)/1024:.2f} KB")
    print(f"Base64 Length: {len(b64_str)}")
    
    # Write to a file to be picked up
    with open('embedded_code.txt', 'w') as f:
        f.write(b64_str)
    
    os.remove(zip_filename)
    print("Saved to embedded_code.txt")

if __name__ == '__main__':
    generate_embedded()

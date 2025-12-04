import os
import zipfile

def zip_model_code():
    source_dir = 'libs/Model'
    output_filename = 'model_code.zip'
    
    with zipfile.ZipFile(output_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(source_dir):
            # Exclude __pycache__
            if '__pycache__' in dirs:
                dirs.remove('__pycache__')
                
            for file in files:
                if file.endswith(('.pyc', '.DS_Store', '.pt', '.bin', '.gguf', '.h5')):
                    continue
                    
                file_path = os.path.join(root, file)
                # Archive name should be relative to libs/Model parent, i.e., inside the zip it should start with Model/
                # We want the zip to contain "Model/core/...", so we arcname relative to libs
                arcname = os.path.relpath(file_path, 'libs')
                zipf.write(file_path, arcname)
                print(f"Zipped: {arcname}")

if __name__ == "__main__":
    zip_model_code()

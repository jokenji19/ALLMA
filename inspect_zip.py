
import re
import base64
import zipfile
import io
import os

MAIN_PY_PATH = "/Users/erikahu/ALLMA/MODELLO_SVILUPPO_ALLMA(versione 4 stabile)/main.py"

def inspect_zip_data():
    try:
        with open(MAIN_PY_PATH, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Extract ZIP_DATA
        match = re.search(r"ZIP_DATA = b'(.*?)'", content, re.DOTALL)
        if not match:
            print("Could not find ZIP_DATA in main.py")
            return

        zip_b64 = match.group(1)
        zip_bytes = base64.b64decode(zip_b64)
        
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
            print(f"Files in zip: {len(z.namelist())}")
            for filename in z.namelist():
                if filename.endswith(".py"):
                    with z.open(filename) as f:
                        file_content = f.read().decode("utf-8", errors="ignore")
                        if "from Model" in file_content or "import Model" in file_content:
                            print(f"Found 'Model' import in: {filename}")
                            # Print the specific lines
                            for line in file_content.splitlines():
                                if "from Model" in line or "import Model" in line:
                                    print(f"  {line.strip()}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    inspect_zip_data()

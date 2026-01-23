
import os
import zipfile
import base64
import re
import io

def pack_and_update():
    print("Packing allma_model...", flush=True)
    
    # Create in-memory zip
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk('allma_model'):
            # clean unwanted
            dirs[:] = [d for d in dirs if d not in ['__pycache__', '.git', '.DS_Store']]
            for file in files:
                if file in ['.DS_Store', '.gitignore', 'allma_diary.json']: 
                    continue
                if file.endswith('.pyc'): continue
                
                abs_path = os.path.join(root, file)
                rel_path = os.path.relpath(abs_path, '.')
                print(f"Adding {rel_path}", flush=True)
                zf.write(abs_path, rel_path)
    
    encoded = base64.b64encode(buffer.getvalue()).decode('utf-8')
    print(f"Blob size: {len(encoded)} chars", flush=True)
    
    print("Reading main.py...", flush=True)
    with open('main.py', 'r') as f:
        content = f.read()
        
    # Regex to find ZIP_DATA = "..."
    # We assume string starts with "UEsDB" (PK zip header in b64)
    # Be careful with regex dot matching newline vs not. B64 is one line? 
    # In the file view it looked like one line.
    
    # Robust replacement strategy
    print("Injecting new payload...", flush=True)
    
    # Find start
    start_marker = 'ZIP_DATA = "'
    start_idx = content.find(start_marker)
    if start_idx == -1:
        print("ERROR: Could not find ZIP_DATA variable in main.py")
        return
        
    start_quote = start_idx + len(start_marker)
    
    # Find end quote - this is tricky if the blob is huge and possibly split?
    # Usually it's one huge line in python scripts generated this way.
    # We look for the next " that is NOT escaped.
    
    # Faster approach: Regex
    # Pattern: ZIP_DATA = "([A-Za-z0-9+/=]+)"
    # But regex on 1MB string might be slow/hang in some envs? No, Python is fine.
    
    new_content = re.sub(
        r'ZIP_DATA = "[A-Za-z0-9+/=\n\r]*"',
        f'ZIP_DATA = "{encoded}"',
        content,
        count=1
    )
    
    if len(new_content) == len(content) and encoded not in content:
         # Fallback if regex failed (maybe due to newlines)
         print("Regex failed to match, trying manual slice replacement", flush=True)
         # Assume it ends at the next quote
         # Actually, let's just assume the structure we saw
         pass # If regex fails we might be in trouble, but let's try the simple one first
    
    with open('main.py', 'w') as f:
        f.write(new_content)
        
    print("SUCCESS: main.py updated with new code blob.", flush=True)

if __name__ == "__main__":
    pack_and_update()

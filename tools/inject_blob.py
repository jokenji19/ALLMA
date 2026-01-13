import os

def inject():
    # Read the base64 data
    try:
        with open('embedded_code.txt', 'r') as f:
            blob_data = f.read().strip()
    except FileNotFoundError:
        print("embedded_code.txt not found! Run generate_embedded_code.py first.")
        return

    # Read main.py
    with open('main.py', 'r') as f:
        main_content = f.read()

    # Robust replacement: find line with # INJECT_HERE
    lines = main_content.split('\n')
    new_lines = []
    injected = False
    
    for line in lines:
        if '# INJECT_HERE' in line and 'INCEPTION_BLOB' in line:
            # Preserve indentation
            indent = line[:line.find('INCEPTION_BLOB')]
            new_lines.append(f'{indent}INCEPTION_BLOB = "{blob_data}"')
            injected = True
        else:
            new_lines.append(line)
            
    if not injected:
        print("Target placeholder not found in main.py (Robust Search)!")
        return

    new_content = '\n'.join(new_lines)
    
    # Write back
    with open('main.py', 'w') as f:
        f.write(new_content)
    
    print(f"Injected {len(blob_data)} chars into main.py")

if __name__ == '__main__':
    inject()

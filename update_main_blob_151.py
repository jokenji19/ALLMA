import os
import re

blob_file = '/Users/erikahu/ALLMA/MODELLO_SVILUPPO_ALLMA(versione 4 stabile)/code_blob.py'
main_file = '/Users/erikahu/ALLMA/MODELLO_SVILUPPO_ALLMA(versione 4 stabile)/main.py'

print(f"Reading new blob from {blob_file}...")
with open(blob_file, 'r') as f:
    blob_content = f.read()

# Extract ZIP_DATA from blob_content
# We expect ZIP_DATA = b'...'
start_marker = "ZIP_DATA = b'"
start_idx = blob_content.find(start_marker)
if start_idx == -1:
    print("Error: Could not find ZIP_DATA in code_blob.py")
    exit(1)

end_idx = blob_content.find("'", start_idx + len(start_marker))
if end_idx == -1:
    print("Error: Could not find ZIP_DATA end in code_blob.py")
    exit(1)

new_zip_data_line = blob_content[start_idx:end_idx+1]
print(f"Extracted new ZIP_DATA size: {len(new_zip_data_line)} bytes")

print(f"Reading target file {main_file}...")
with open(main_file, 'r') as f:
    main_content = f.read()

# Find and replace in main_content
main_start_idx = main_content.find(start_marker)
if main_start_idx == -1:
    print("Error: Could not find ZIP_DATA start in main.py")
    exit(1)

main_end_idx = main_content.find("'", main_start_idx + len(start_marker))
if main_end_idx == -1:
    print("Error: Could not find ZIP_DATA end in main.py")
    exit(1)

print(f"Found existing ZIP_DATA in main.py from {main_start_idx} to {main_end_idx+1}")

new_content = main_content[:main_start_idx] + new_zip_data_line + main_content[main_end_idx+1:]

# Update BUILD_VERSION
new_version = 'BUILD_VERSION = "Build 151 (Plan G)"'
print(f"Updating BUILD_VERSION to '{new_version}'...")
new_content = re.sub(r'BUILD_VERSION\s*=\s*"[^"]+"', new_version, new_content)

print(f"Writing updated content to {main_file}...")
with open(main_file, 'w') as f:
    f.write(new_content)

print("Done.")

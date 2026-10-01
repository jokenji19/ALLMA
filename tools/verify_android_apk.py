"""Check the packaged Python/runtime payload before deploying an ALLMA APK."""
import argparse
import ast
import hashlib
import io
import json
from pathlib import Path
import tarfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def verify_apk(apk):
    tree = ast.parse((ROOT / 'main.py').read_text())
    payload = next(ast.literal_eval(node.value) for node in tree.body
                   if isinstance(node, ast.Assign) and any(
                       isinstance(target, ast.Name) and target.id == 'ZIP_DATA'
                       for target in node.targets))
    with zipfile.ZipFile(apk) as package:
        with tarfile.open(fileobj=io.BytesIO(package.read('assets/private.tar')), mode='r:*') as private:
            entry = next(m for m in private.getmembers() if m.name in ('main.py', 'main.pyc'))
            if payload.encode() not in private.extractfile(entry).read():
                raise ValueError('APK does not contain the current embedded source payload')
        with tarfile.open(fileobj=io.BytesIO(package.read('lib/arm64-v8a/libpybundle.so')), mode='r:*') as bundle:
            names = set(bundle.getnames())
            base = '_python_bundle/site-packages/'
            for module in ('android', 'jnius', 'kivy', 'kivymd', 'requests', 'numpy', 'plyer', 'llama_cpp'):
                if not any(base + module + '/__init__.' + suffix in names for suffix in ('py', 'pyc')):
                    raise ValueError(f'Missing packaged module: {module}')
            metadata_name = base + 'kivymd-1.2.0.dist-info/METADATA'
            if metadata_name not in names:
                raise ValueError('The APK must contain KivyMD 1.2.0')
            for library in ('libllama.so', 'libggml.so', 'libggml-base.so', 'libggml-cpu.so'):
                header = bundle.extractfile(base + 'llama_cpp/' + library).read(20)
                if header[:4] != b'\x7fELF' or int.from_bytes(header[18:20], 'little') != 183:
                    raise ValueError(f'Not an Android ARM64 ELF library: {library}')
    return {'apk': str(Path(apk).resolve()), 'sha256': hashlib.sha256(Path(apk).read_bytes()).hexdigest(),
            'payload_matches': True, 'kivymd': '1.2.0', 'native_arch': 'arm64-v8a'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('apk')
    args = parser.parse_args()
    print(json.dumps(verify_apk(args.apk), indent=2))

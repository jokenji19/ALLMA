"""Check the packaged Python/runtime payload before deploying an ALLMA APK."""
import argparse
import ast
import hashlib
import io
import json
from pathlib import Path
import tarfile
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def verify_apk(apk):
    tree = ast.parse((ROOT / 'main.py').read_text())
    payload = next(ast.literal_eval(node.value) for node in tree.body
                   if isinstance(node, ast.Assign) and any(
                       isinstance(target, ast.Name) and target.id == 'ZIP_DATA'
                       for target in node.targets))
    with zipfile.ZipFile(apk) as package:
        if not any(b'Lorg/allma/runtime/NativeProcessHealth;' in package.read(name)
                   and b'ownerForOperation' in package.read(name)
                   for name in package.namelist() if name.startswith('classes') and name.endswith('.dex')):
            raise ValueError('APK lacks the current native process/update health helper')
        presplash = ROOT/'assets/android/presplash.png'
        if package.read('res/drawable/presplash.jpg') != presplash.read_bytes():
            raise ValueError('APK still contains an old/default native launch screen')
        for resource in ('res/xml/allma_backup_rules.xml','res/xml/allma_extraction_rules.xml'):
            if resource not in package.namelist():raise ValueError('APK lacks backup rules: '+resource)
        for resource in ('startup_ui.py', 'assets/web/images/startup-connection.png',
                         'assets/web/fonts/Inter-Regular.ttf', 'assets/web/fonts/Inter-LICENSE.txt'):
            name = 'assets/startup/' + resource
            if name not in package.namelist() or package.read(name) != (ROOT/resource).read_bytes():
                raise ValueError('APK lacks the current early-startup resource: '+resource)
        with tarfile.open(fileobj=io.BytesIO(package.read('assets/private.tar')), mode='r:*') as private:
            from allma_model.utils.runtime_storage import STATE_FILES
            forbidden=set(STATE_FILES)|{'allma_model.zip','personality_state.json','beta_test_conversations.json','allma_model/allma_diary.json'}
            names={m.name.removeprefix('./') for m in private.getmembers()}
            if names&forbidden or any(n.startswith(('Library/','_quarantine/','htmlcov/','benchmarks/reports/')) for n in names):
                raise ValueError('APK contains local state or development caches')
            if any(n.startswith(('libs/recipes/', 'libs_custom/')) for n in names):
                raise ValueError('APK contains obsolete native libraries or build-only recipes')
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
            runtime = json.loads(bundle.extractfile(base + 'llama_cpp/allma_runtime.json').read())
            if runtime.get('python_version') != '0.3.36' or not runtime.get('qwen35'):
                raise ValueError('APK lacks the matched Qwen 3.5 native runtime')
            patches=ROOT/'libs/recipes/llamacpp_android/patches'
            if (runtime.get('runtime_id') != 'allma-cpu-opencl-hexagon-v3'
                    or runtime.get('dynamic_backends') is not True
                    or runtime.get('interactive_scheduling') is not True
                    or runtime.get('explicit_devices') is not True
                    or runtime.get('patch_set_sha256') != hashlib.sha256(
                        b''.join((patches/name).read_bytes() for name in
                                 ['opencl-interactive.patch','explicit-devices.patch'])).hexdigest()
                    or runtime.get('patch_sha256') != hashlib.sha256(
                        (ROOT / 'libs/recipes/llamacpp_android/patches/opencl-interactive.patch').read_bytes()).hexdigest()
                    or runtime.get('backends') != ['CPU', 'OpenCL', 'Hexagon']):
                raise ValueError('APK lacks the optional OpenCL runtime')
            manifest=json.loads((ROOT/'libs/native_backend/hexagon/manifest.json').read_text())
            if runtime.get('hexagon')!=manifest:
                raise ValueError('APK contains a different optional Hexagon component')
            for name,digest in manifest['files'].items():
                content=bundle.extractfile(base+'llama_cpp/'+name).read()
                machine=164 if name.endswith('.bin') else 183
                if (content[:4]!=b'\x7fELF' or int.from_bytes(content[18:20],'little')!=machine
                        or hashlib.sha256(content).hexdigest()!=digest):
                    raise ValueError('Invalid Hexagon component: '+name)
            if base+'llama_cpp/HEXAGON-LICENSE.txt' not in names:
                raise ValueError('Missing optional Hexagon license')
            source=next((base+'llama_cpp/llama.'+suffix for suffix in ['py','pyc']
                         if base+'llama_cpp/llama.'+suffix in names),None)
            if not source or b'_allma_device_array' not in bundle.extractfile(source).read():
                raise ValueError('APK lacks explicit native device isolation')
            if any(name.endswith('/libggml-htp-v79.so') for name in names|set(package.namelist())):
                raise ValueError('DSP skeleton must be packaged as data, never as an ARM64 library')
            plugin = bundle.extractfile(base + 'llama_cpp/libggml-opencl.so').read(20)
            if plugin[:4] != b'\x7fELF' or int.from_bytes(plugin[18:20], 'little') != 183:
                raise ValueError('Not an Android ARM64 OpenCL backend')
            if any(name.endswith('/libOpenCL.so') for name in names | set(package.namelist())):
                raise ValueError('The APK must use the system OpenCL driver, not bundle a replacement')
            if b'qwen35' not in bundle.extractfile(base + 'llama_cpp/libllama.so').read():
                raise ValueError('Native library lacks Qwen 3.5 architecture')
    return {'apk': str(Path(apk).resolve()), 'sha256': hashlib.sha256(Path(apk).read_bytes()).hexdigest(),
            'payload_matches': True, 'startup_assets_match': True, 'native_presplash_matches': True, 'kivymd': '1.2.0', 'native_arch': 'arm64-v8a',
            'llama_cpp_python':runtime['python_version'], 'qwen35':True,
            'native_backends':runtime['backends'], 'dynamic_backends':True,
            'explicit_devices':True,'hexagon_role':'decider','native_update_health':True,
            'operation_owner_refresh':True}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('apk')
    args = parser.parse_args()
    print(json.dumps(verify_apk(args.apk), indent=2))

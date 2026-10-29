"""Reproduce the manifest-only AAR merged into the Android application."""
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def build():
    destination = ROOT / 'libs/allma-native-manifest.aar'
    entry = zipfile.ZipInfo('AndroidManifest.xml', (1980, 1, 1, 0, 0, 0))
    entry.compress_type = zipfile.ZIP_DEFLATED
    entry.external_attr = 0o644 << 16
    with zipfile.ZipFile(destination, 'w') as archive:
        archive.writestr(entry, (ROOT / 'libs/native_backend/AndroidManifest.xml').read_bytes())
    return destination


if __name__ == '__main__':
    print(build())

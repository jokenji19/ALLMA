"""Optional, verified Kokoro asset pack. No audio or personal text leaves ALLMA."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import tarfile
import tempfile
import threading
import urllib.request

PACK_URL = 'https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models/kokoro-int8-multi-lang-v1_0.tar.bz2'
PACK_SHA256 = '4c3052abaa60943a341f193888cf6abd68787dae6ab8ae5c925a706caa247e4e'
PACK_BYTES = 132303094
PACK_DIRECTORY = 'kokoro-int8-multi-lang-v1_0'
FILES = {'model.int8.onnx': '4b86207ef680e394d8343bee22dfc4c512e5c707c6d9578e3f35ab09bffd6b36',
         'voices.bin': '1c5a5b983d3d50d8586d437a51f3faa2da7919ce76a013c081e65671a3447c29',
         'tokens.txt': '6ebb6bb288f20f3ae8d004d3c2ca27697da27c037d75e81a60e2a6a663f95425'}


def digest(path):
    hasher = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''): hasher.update(block)
    return hasher.hexdigest()


class VoicePack:
    def __init__(self, directory, on_change=None):
        self.directory = Path(directory)
        self.on_change = on_change
        self.progress = 0
        self.busy = False
        self.error = None
        self._lock = threading.Lock()
        self._lifecycle_lock = threading.Lock()
        self._cancel = threading.Event()
        self._verified = False
        self._fingerprint = None
        self._closed = False
        self._corrupt = False

    @property
    def ready(self):
        marker = self.directory / 'verified.json'
        try:
            return (not self._corrupt and json.loads(marker.read_text()) == {'sha256': PACK_SHA256}
                    and all((self.directory/name).is_file() for name in FILES)
                    and (self.directory/'espeak-ng-data/it_dict').is_file())
        except (OSError, ValueError): return False

    def verify(self):
        # Stat is cheap; hashing 114 MB is only needed after installation/change.
        # A cached successful hash must not authorize deleted/replaced assets.
        try:
            fingerprint = tuple((name, (self.directory/name).stat().st_ino,
                                 (self.directory/name).stat().st_size,
                                 (self.directory/name).stat().st_mtime_ns) for name in FILES)
            valid = self.ready
            if valid and (not self._verified or fingerprint != self._fingerprint):
                valid = all(digest(self.directory/name) == expected for name, expected in FILES.items())
        except OSError:
            valid = False
        if not valid:
            self._verified = False
            self._fingerprint = None
            self._corrupt = True
            self.error = 'Dati vocali non integri. Scarica nuovamente le voci.'
            self._notify()
            raise ValueError(self.error)
        self._verified = True
        self._fingerprint = fingerprint
        return str(self.directory)

    def _notify(self):
        if self.on_change: self.on_change()

    def install_archive(self, archive):
        """Authenticate before extraction, reject links/traversal and cap disk use."""
        archive = Path(archive)
        if archive.stat().st_size != PACK_BYTES or digest(archive) != PACK_SHA256:
            raise ValueError('Verifica del download vocale fallita.')
        parent = self.directory.parent
        parent.mkdir(parents=True, exist_ok=True)
        temporary = Path(tempfile.mkdtemp(prefix='.voice-install-', dir=parent))
        try:
            with tarfile.open(archive, 'r:bz2') as package:
                members = package.getmembers()
                if sum(m.size for m in members) > 500*1024*1024: raise ValueError('Archivio vocale troppo grande.')
                for member in members:
                    target = Path(member.name)
                    if (target.is_absolute() or '..' in target.parts or not target.parts
                            or target.parts[0] != PACK_DIRECTORY or not (member.isfile() or member.isdir())):
                        raise ValueError('Contenuto vocale non valido.')
                # Explicit extraction also works with Android's older Python.
                for member in members:
                    if self._cancel.is_set(): raise InterruptedError('Download interrotto.')
                    target = temporary / member.name
                    if member.isdir(): target.mkdir(parents=True, exist_ok=True)
                    else:
                        target.parent.mkdir(parents=True, exist_ok=True)
                        with package.extractfile(member) as source, target.open('wb') as output:
                            shutil.copyfileobj(source, output, 1024*1024)
            source = temporary / PACK_DIRECTORY
            if any(digest(source/name) != value for name, value in FILES.items()):
                raise ValueError('File vocali non integri.')
            if self.directory.exists():
                if self.ready: return
                # These are replaceable model assets, never user memories.
                retired = parent / (self.directory.name + '.invalid')
                if retired.exists(): shutil.rmtree(retired)
                os.replace(self.directory, retired)
            (source/'verified.json').write_text(json.dumps({'sha256':PACK_SHA256}))
            os.replace(source, self.directory)
            self._verified = True
            self._corrupt = False
            retired = parent / (self.directory.name + '.invalid')
            if retired.exists(): shutil.rmtree(retired)
        finally:
            shutil.rmtree(temporary, ignore_errors=True)

    def download(self):
        with self._lifecycle_lock:
            if self._closed or not self._lock.acquire(blocking=False): return False
            self.busy, self.error, self.progress = True, None, 0
            self._cancel.clear()
        def worker():
            partial = self.directory.parent / '.kokoro-download.part'
            try:
                if self._cancel.is_set(): raise InterruptedError('Download interrotto.')
                self.directory.parent.mkdir(parents=True, exist_ok=True)
                if shutil.disk_usage(self.directory.parent).free < 700*1024*1024:
                    raise OSError('Servono almeno 700 MB liberi per preparare le voci.')
                if self._cancel.is_set(): raise InterruptedError('Download interrotto.')
                with urllib.request.urlopen(PACK_URL, timeout=30) as response, partial.open('wb') as writer:
                    count = 0
                    for block in iter(lambda: response.read(256*1024), b''):
                        if self._cancel.is_set(): raise InterruptedError('Download interrotto.')
                        count += len(block)
                        if count > PACK_BYTES: raise ValueError('Dimensione vocale non valida.')
                        writer.write(block)
                        progress = min(98, int(count*98/PACK_BYTES))
                        if progress != self.progress:
                            self.progress = progress; self._notify()
                self.install_archive(partial)
                self.progress = 100
            except Exception as error:
                self.error = str(error)
            finally:
                partial.unlink(missing_ok=True)
                self.busy = False
                self._lock.release()
                self._notify()
        threading.Thread(target=worker, daemon=True, name='ALLMA-VoiceDownload').start()
        self._notify()
        return True

    def close(self):
        with self._lifecycle_lock:
            self._closed = True
            self._cancel.set()

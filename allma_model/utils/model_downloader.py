"""Verified, resumable downloads. Only complete models get their final filename."""
import hashlib
import logging
import os
import re
import threading
import time

import requests
from kivy.utils import platform


class ModelDownloader:
    _locks = {}
    _locks_guard = threading.Lock()
    _session_verified = {}

    def __init__(self, models_dir=None):
        self.logger = logging.getLogger(__name__)
        self.models_dir = models_dir or self._get_models_dir()
        self.max_retries = 5
        self.retry_delay = 2
        self._verified = self._session_verified
        from allma_model.llm.model_catalog import catalog
        self.models = catalog()

    def _get_models_dir(self):
        if platform == 'android':
            from android.storage import app_storage_path
            return os.path.join(app_storage_path(), 'models')
        return os.path.join(os.getcwd(), 'models')

    @staticmethod
    def _fingerprint(path, info):
        stat = os.stat(path)
        if stat.st_size != info['size_bytes']:
            return None
        return (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns,
                stat.st_ctime_ns, info['sha256'])

    def local_status(self, path, info):
        """Metadata-only inventory: presence is not a successful integrity check."""
        path = os.path.abspath(path)
        try:
            fingerprint = self._fingerprint(path, info)
            present = fingerprint is not None and os.path.isfile(path)
            return {'available': present,
                    'verified': bool(present and self._verified.get(path) == fingerprint)}
        except (OSError, KeyError):
            return {'available': False, 'verified': False}

    def _valid(self, path, info):
        """Reuse verified bytes across instances, only within this app process."""
        path = os.path.abspath(path)
        try:
            fingerprint = self._fingerprint(path, info)
            if fingerprint is None:
                return False
            if self._verified.get(path) == fingerprint:
                return True
            digest = hashlib.sha256()
            with open(path, 'rb') as handle:
                for chunk in iter(lambda: handle.read(1024 * 1024), b''):
                    digest.update(chunk)
            if digest.hexdigest() != info['sha256']:
                return False
            # Do not certify a file changed while hashing.
            if self._fingerprint(path, info) != fingerprint:
                return False
            self._verified[path] = fingerprint
            return True
        except (OSError, KeyError):
            return False

    def check_models_missing(self):
        # This method is deliberately read-only, including unknown/custom models.
        return [key for key, info in self.models.items()
                if info.get('required', True)
                if not self._valid(os.path.join(self.models_dir, info['filename']), info)]

    def cleanup_old_models(self):
        """Compatibility API: list unrecognized files without deleting user assets."""
        if not os.path.isdir(self.models_dir):
            return []
        known = {info['filename'] + suffix for info in self.models.values()
                 for suffix in ('', '.part')}
        return [name for name in os.listdir(self.models_dir) if name not in known]

    def download_model(self, model_key, progress_callback=None):
        info = self.models.get(model_key)
        if info is None:
            return False, f'Modello sconosciuto: {model_key}'
        filename = info['filename']
        if (os.path.basename(filename) != filename or filename in ('', '.', '..')
                or not re.fullmatch(r'[0-9a-f]{64}', info.get('sha256', ''))
                or not isinstance(info.get('size_bytes'), int) or info['size_bytes'] <= 0):
            return False, 'Manifest del modello non valido'
        path = os.path.abspath(os.path.join(self.models_dir, filename))
        with self._locks_guard:
            lock = self._locks.setdefault(path, threading.Lock())
        if not lock.acquire(blocking=False):
            return False, 'Download già in corso per questo modello'
        try:
            return self._download_locked(path, info, progress_callback)
        except (OSError, requests.RequestException, ValueError) as exc:
            self.logger.warning('Download non riuscito: %s', exc)
            return False, str(exc)
        finally:
            lock.release()

    def _download_locked(self, path, info, progress_callback):
        os.makedirs(self.models_dir, exist_ok=True)
        if self._valid(path, info):
            return True, None
        partial = path + '.part'
        expected = info['size_bytes']
        # Migrate incomplete files written by older versions, preserving their bytes.
        if not os.path.exists(partial) and os.path.isfile(path) and os.path.getsize(path) < expected:
            os.replace(path, partial)
        last_error = 'Download incompleto'
        for attempt in range(self.max_retries):
            try:
                if self._valid(partial, info):
                    os.replace(partial, path)
                    return True, None
                offset = os.path.getsize(partial) if os.path.exists(partial) else 0
                if offset >= expected:
                    # Only our own incomplete/corrupt transfer file is reset.
                    with open(partial, 'wb'):
                        pass
                    offset = 0
                headers = {'Accept-Encoding': 'identity', 'User-Agent': 'ALLMA-model-downloader'}
                if offset:
                    headers['Range'] = f'bytes={offset}-'
                with requests.get(info['url'], stream=True, timeout=(15, 60), headers=headers) as response:
                    if response.status_code == 416:
                        # Never treat 416 as success: the complete hash was checked above.
                        with open(partial, 'wb'):
                            pass
                        raise ValueError('Ripresa rifiutata: riavvio del download necessario')
                    response.raise_for_status()
                    if response.status_code == 206:
                        match = re.fullmatch(r'bytes (\d+)-(\d+)/(\d+)', response.headers.get('Content-Range', ''))
                        if not match:
                            raise ValueError('Content-Range mancante o non valido')
                        start, end, total = map(int, match.groups())
                        if start != offset or total != expected or not start <= end < total:
                            raise ValueError('Content-Range incompatibile con il modello')
                        segment_size = end - start + 1
                        mode = 'ab' if offset else 'wb'
                    elif response.status_code == 200:
                        # The server ignored Range: restart, never append a full response.
                        offset = 0
                        mode = 'wb'
                        segment_size = expected
                    else:
                        raise ValueError(f'Risposta HTTP inattesa: {response.status_code}')
                    length = response.headers.get('Content-Length')
                    if length is not None and int(length) != segment_size:
                        raise ValueError('Dimensione HTTP incompatibile con il modello')
                    if response.headers.get('Content-Encoding', 'identity') != 'identity':
                        raise ValueError('Codifica HTTP non supportata per la ripresa')
                    received = 0
                    with open(partial, mode) as handle:
                        for chunk in response.iter_content(chunk_size=65536):
                            if not chunk:
                                continue
                            if received + len(chunk) > segment_size:
                                raise ValueError('Il server ha inviato più dati del previsto')
                            handle.write(chunk)
                            received += len(chunk)
                            if progress_callback:
                                progress_callback(offset + received, expected)
                        handle.flush()
                        os.fsync(handle.fileno())
                    if received != segment_size:
                        raise ValueError('Connessione terminata prima del completamento')
                if not self._valid(partial, info):
                    raise ValueError('Modello incompleto o checksum SHA-256 non valido')
                os.replace(partial, path)
                return True, None
            except (OSError, requests.RequestException, ValueError) as exc:
                last_error = str(exc)
                self.logger.warning('Download tentativo %s/%s: %s', attempt + 1, self.max_retries, exc)
                if attempt + 1 < self.max_retries:
                    time.sleep(self.retry_delay)
        return False, last_error

    def start_background_download(self, model_keys, progress_callback, completion_callback, on_model_complete=None):
        def run():
            success, error = True, None
            try:
                for key in model_keys:
                    callback = (lambda d, t: progress_callback(key, d, t)) if progress_callback else None
                    success, error = self.download_model(key, callback)
                    if not success:
                        break
                    if on_model_complete:
                        on_model_complete(key)
            except Exception as exc:
                self.logger.exception('Errore nel download in background')
                success, error = False, str(exc)
            completion_callback(success, error)
        thread = threading.Thread(target=run, daemon=True, name='ModelDownload')
        thread.start()
        return thread

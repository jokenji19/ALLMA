"""Full model checksums shared by download and inference, within one process.

No persistent trust flag: a new process or changed file must hash the bytes again.
The cache only avoids rereading unchanged models after a native context closes.
"""
import hashlib
import os
import threading


class VerifiedModels:
    def __init__(self):
        self.verified = {}
        self._locks = {}
        self._guard = threading.Lock()

    @staticmethod
    def fingerprint(path, info):
        stat = os.stat(path)
        if stat.st_size != info['size_bytes']:
            return None
        return (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns,
                stat.st_ctime_ns, info['sha256'])

    def valid(self, path, info):
        path = os.path.abspath(path)
        with self._guard:
            lock = self._locks.setdefault(path, threading.Lock())
        with lock:
            try:
                fingerprint = self.fingerprint(path, info)
                if fingerprint is None:
                    return False
                if self.verified.get(path) == fingerprint:
                    return True
                digest = hashlib.sha256()
                with open(path, 'rb') as handle:
                    for chunk in iter(lambda: handle.read(1024 * 1024), b''):
                        digest.update(chunk)
                if digest.hexdigest() != info['sha256']:
                    return False
                # A download/replacement during verification cannot be certified.
                if self.fingerprint(path, info) != fingerprint:
                    return False
                self.verified[path] = fingerprint
                return True
            except (OSError, KeyError):
                return False


verified_models = VerifiedModels()

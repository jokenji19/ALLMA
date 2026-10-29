import hashlib
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import Mock

import pytest

from allma_model.utils import model_integrity as module


@pytest.fixture
def model(tmp_path):
    path = tmp_path/'model.gguf'
    data = b'verified synthetic model'
    path.write_bytes(data)
    info = {'size_bytes':len(data), 'sha256':hashlib.sha256(data).hexdigest()}
    return path, info


def test_reload_hashes_only_once_but_new_process_cache_verifies_again(model, monkeypatch):
    path, info = model
    digest = Mock(wraps=hashlib.sha256)
    monkeypatch.setattr(module.hashlib, 'sha256', digest)
    cache = module.VerifiedModels()
    assert cache.valid(path, info)
    assert cache.valid(str(path), info)
    assert digest.call_count == 1
    assert module.VerifiedModels().valid(path, info)
    assert digest.call_count == 2


def test_same_size_replacement_with_preserved_mtime_is_not_trusted(model):
    path, info = model
    cache = module.VerifiedModels()
    assert cache.valid(path, info)
    stat = path.stat()
    replacement = path.with_suffix('.replacement')
    replacement.write_bytes(b'x'*info['size_bytes'])
    os.utime(replacement, ns=(stat.st_atime_ns, stat.st_mtime_ns))
    replacement.replace(path)
    assert not cache.valid(path, info)


def test_changed_manifest_requires_fresh_verification(model):
    path, info = model
    cache = module.VerifiedModels()
    assert cache.valid(path, info)
    assert not cache.valid(path, dict(info, sha256='0'*64))
    path.unlink()
    assert not cache.valid(path, info)


def test_change_during_hash_is_not_cached(model, monkeypatch):
    path, info = model
    cache = module.VerifiedModels()
    real_digest = hashlib.sha256
    def hashing():
        digest = real_digest()
        def update(data):
            digest.update(data)
            path.write_bytes(b'x'*info['size_bytes'])
        return type('Digest', (), {'update':staticmethod(update),
                                   'hexdigest':staticmethod(digest.hexdigest)})()
    monkeypatch.setattr(module.hashlib, 'sha256', hashing)
    assert not cache.valid(path, info)
    assert str(path) not in cache.verified


def test_concurrent_loaders_share_one_complete_verification(model, monkeypatch):
    path, info = model
    cache = module.VerifiedModels()
    started, release = threading.Event(), threading.Event()
    real_digest = hashlib.sha256
    calls = []
    def hashing():
        calls.append(True)
        started.set()
        assert release.wait(3)
        return real_digest()
    monkeypatch.setattr(module.hashlib, 'sha256', hashing)
    with ThreadPoolExecutor(max_workers=2) as workers:
        first = workers.submit(cache.valid, path, info)
        assert started.wait(3)
        second = workers.submit(cache.valid, path, info)
        release.set()
        assert first.result(timeout=3) and second.result(timeout=3)
    assert len(calls) == 1

import hashlib
from pathlib import Path
from unittest.mock import Mock

import pytest
import requests
from allma_model.utils.model_downloader import ModelDownloader

DATA = b'GGUF-test-model-payload'


class Response:
    def __init__(self, code, body=DATA, headers=None):
        self.status_code = code
        self.body = body
        self.headers = requests.structures.CaseInsensitiveDict(headers or {})
    def __enter__(self):
        return self
    def __exit__(self, *args):
        pass
    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(str(self.status_code))
    def iter_content(self, chunk_size):
        yield self.body


@pytest.fixture
def downloader(tmp_path):
    obj = ModelDownloader(str(tmp_path))
    obj.models = {'test': {'url': 'https://example.invalid/model', 'filename': 'model.gguf',
                          'size_bytes': len(DATA), 'sha256': hashlib.sha256(DATA).hexdigest()}}
    obj.max_retries = 1
    obj.retry_delay = 0
    return obj


def request(monkeypatch, responses):
    getter = Mock(side_effect=responses)
    monkeypatch.setattr('allma_model.utils.model_downloader.requests.get', getter)
    return getter


def test_missing_check_preserves_unknown_files(downloader, tmp_path):
    other = tmp_path / 'my-custom-model.gguf'
    other.write_bytes(b'custom')
    assert downloader.check_models_missing() == ['test']
    downloader.cleanup_old_models()
    assert other.read_bytes() == b'custom'


@pytest.mark.parametrize('code', [200, 206])
def test_resume_ignored_or_honored_is_correct(downloader, tmp_path, monkeypatch, code):
    (tmp_path / 'model.gguf').write_bytes(DATA[:5])  # Legacy incomplete file.
    headers = {'Content-Length': str(len(DATA) if code == 200 else len(DATA)-5)}
    if code == 206:
        headers['Content-Range'] = f'bytes 5-{len(DATA)-1}/{len(DATA)}'
    getter = request(monkeypatch, [Response(code, DATA if code == 200 else DATA[5:], headers)])
    assert downloader.download_model('test') == (True, None)
    assert (tmp_path / 'model.gguf').read_bytes() == DATA
    assert getter.call_args.kwargs['headers']['Range'] == 'bytes=5-'
    assert not (tmp_path / 'model.gguf.part').exists()


@pytest.mark.parametrize('response', [
    Response(416, b''),
    Response(206, DATA[5:], {'Content-Range': f'bytes 4-{len(DATA)-1}/{len(DATA)}'}),
    Response(200, b'truncated'),
    Response(200, b'x' * len(DATA)),
    Response(200, DATA, {'Content-Length': '9999'}),
])
def test_invalid_download_never_published(downloader, tmp_path, monkeypatch, response):
    (tmp_path / 'model.gguf.part').write_bytes(DATA[:5])
    request(monkeypatch, [response])
    assert downloader.download_model('test')[0] is False
    assert not (tmp_path / 'model.gguf').exists()


def test_416_restarts_instead_of_false_success(downloader, tmp_path, monkeypatch):
    (tmp_path / 'model.gguf.part').write_bytes(DATA[:5])
    downloader.max_retries = 2
    getter = request(monkeypatch, [Response(416), Response(200)])
    assert downloader.download_model('test') == (True, None)
    assert 'Range' not in getter.call_args.kwargs['headers']


def test_complete_partial_is_verified_without_network(downloader, tmp_path, monkeypatch):
    (tmp_path / 'model.gguf.part').write_bytes(DATA)
    getter = request(monkeypatch, [])
    assert downloader.download_model('test') == (True, None)
    getter.assert_not_called()


def test_hash_cache_detects_same_size_corruption(downloader, tmp_path):
    path = tmp_path / 'model.gguf'
    path.write_bytes(DATA)
    assert downloader.check_models_missing() == []
    path.write_bytes(b'x' * len(DATA))
    assert downloader.check_models_missing() == ['test']


def test_failed_transfer_preserves_existing_final(downloader, tmp_path, monkeypatch):
    path = tmp_path / 'model.gguf'
    old = b'x' * len(DATA)
    path.write_bytes(old)
    request(monkeypatch, [Response(200, b'invalid')])
    assert downloader.download_model('test')[0] is False
    assert path.read_bytes() == old


def test_duplicate_download_is_rejected(downloader, monkeypatch):
    calls = []
    def nested(path, info, callback):
        calls.append(downloader.download_model('test'))
        return True, None
    monkeypatch.setattr(downloader, '_download_locked', nested)
    assert downloader.download_model('test') == (True, None)
    assert calls == [(False, 'Download già in corso per questo modello')]


def test_connection_failure_resumes_written_bytes(downloader, tmp_path, monkeypatch):
    class Interrupted(Response):
        def iter_content(self, chunk_size):
            yield DATA[:7]
            raise requests.ConnectionError('connessione interrotta')
    downloader.max_retries = 2
    getter = request(monkeypatch, [Interrupted(200), Response(206, DATA[7:], {
        'Content-Range': f'bytes 7-{len(DATA)-1}/{len(DATA)}',
        'Content-Length': str(len(DATA)-7)})])
    assert downloader.download_model('test') == (True, None)
    assert getter.call_args.kwargs['headers']['Range'] == 'bytes=7-'
    assert (tmp_path / 'model.gguf').read_bytes() == DATA


def test_background_exception_reports_completion_once(downloader, monkeypatch):
    monkeypatch.setattr(downloader, 'download_model', Mock(side_effect=RuntimeError('errore simulato')))
    completed = Mock()
    thread = downloader.start_background_download(['test'], None, completed)
    thread.join(timeout=3)
    assert not thread.is_alive()
    completed.assert_called_once_with(False, 'errore simulato')

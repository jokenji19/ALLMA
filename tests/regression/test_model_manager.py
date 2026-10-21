import threading
from types import SimpleNamespace
from unittest.mock import Mock
import pytest
from allma_model.llm.model_manager import ModelManager
from allma_model.utils.model_downloader import ModelDownloader


def make_core(tmp_path):
    return SimpleNamespace(models_dir=str(tmp_path), _user_active=threading.Event(),
        _shutdown_event=threading.Event(), dream_manager=SimpleNamespace(is_dreaming=False),
        _llm_ready=True, _llm=SimpleNamespace(model_path=str(tmp_path/'qwen3-1.7b-q8_0.gguf')),
        switch_model=Mock(return_value={'changed':True}), personal_history={'name':'ALLMA','learned':'spenta'})


def test_optional_model_never_forces_a_startup_download(tmp_path):
    obj = ModelDownloader(str(tmp_path))
    assert obj.check_models_missing() == ['gemma']


def test_user_choice_verified_download_then_switch_keeps_personal_state(tmp_path):
    core = make_core(tmp_path)
    manager = ModelManager(core)
    manager.downloader.download_model = Mock(return_value=(True,None))
    updates = []
    assert manager.apply('qwen35_2b', updates.append)['changed']
    core.switch_model.assert_called_once_with('qwen3.5-2b-q4_k_m.gguf', reasoning=True)
    assert core.personal_history == {'name':'ALLMA','learned':'spenta'}
    assert [x['phase'] for x in updates] == ['verifying','loading']
    assert not manager._operation.locked()


def test_bad_download_never_touches_current_motor(tmp_path):
    core = make_core(tmp_path)
    manager = ModelManager(core)
    manager.downloader.download_model = Mock(return_value=(False,'Checksum errato'))
    with pytest.raises(RuntimeError, match='Checksum'):
        manager.apply('qwen35_2b', lambda _:None)
    core.switch_model.assert_not_called()
    assert not manager._operation.locked()


def test_busy_core_rejects_switch_and_unknown_key_rejects_paths(tmp_path):
    core = make_core(tmp_path)
    manager = ModelManager(core)
    manager.downloader.download_model = Mock()
    core._user_active.set()
    with pytest.raises(RuntimeError, match='Attendi'):
        manager.apply('qwen35_2b', lambda _:None)
    with pytest.raises(ValueError):
        manager.apply('../custom.gguf', lambda _:None)
    manager.downloader.download_model.assert_not_called()


def test_failed_switch_unlocks_manager_for_retry(tmp_path):
    core = make_core(tmp_path)
    core.switch_model.side_effect = RuntimeError('failed')
    manager = ModelManager(core)
    manager.downloader.download_model = Mock(return_value=(True,None))
    with pytest.raises(RuntimeError):
        manager.apply('qwen35_2b', lambda _:None)
    assert not manager._operation.locked()


def test_model_inventory_does_not_read_or_hash_gguf(tmp_path, monkeypatch):
    import builtins
    core = make_core(tmp_path)
    manager = ModelManager(core)
    manager.downloader.models = {'tiny': dict(name='Tiny', quantization='Q4',
        size_bytes=4, reasoning=True, filename='tiny.gguf', sha256='0'*64)}
    (tmp_path/'tiny.gguf').write_bytes(b'bad!')
    # Even a same-size corrupt file may be listed, but never certified.
    monkeypatch.setattr(builtins, 'open', Mock(side_effect=AssertionError('Inventory read model bytes')))
    model = manager.snapshot()['models'][0]
    assert model['available'] is True
    assert model['verified'] is False


def test_verified_cache_shared_between_instances_but_invalidated_by_change(tmp_path, monkeypatch):
    import hashlib
    path = tmp_path/'tiny.gguf'
    path.write_bytes(b'good')
    info = {'size_bytes':4, 'sha256':hashlib.sha256(b'good').hexdigest()}
    first = ModelDownloader(str(tmp_path))
    second = ModelDownloader(str(tmp_path))
    assert first._valid(str(path), info)
    monkeypatch.setattr(hashlib, 'sha256', Mock(side_effect=AssertionError('Duplicate hash')))
    assert second._valid(str(path), info)
    assert second.local_status(str(path), info)['verified']
    path.write_bytes(b'evil')
    assert not second.local_status(str(path), info)['verified']
    with pytest.raises(AssertionError, match='Duplicate hash'):
        second._valid(str(path), info)


def test_concurrent_model_choices_never_start_two_loads(tmp_path):
    core = make_core(tmp_path)
    manager = ModelManager(core)
    entered, release = threading.Event(), threading.Event()
    errors = []
    def download(*args):
        entered.set()
        assert release.wait(3), 'Test did not release download'
        return True, None
    manager.downloader.download_model = Mock(side_effect=download)
    def first_choice():
        try:
            manager.apply('qwen35_2b', lambda _: None)
        except Exception as error:
            errors.append(error)
    worker = threading.Thread(target=first_choice)
    worker.start()
    try:
        assert entered.wait(2)
        with pytest.raises(RuntimeError, match='già in corso'):
            manager.apply('gemma', lambda _: None)
        core.switch_model.assert_not_called()
    finally:
        release.set()
        worker.join(3)
    assert not worker.is_alive() and not errors
    assert manager.downloader.download_model.call_count == 1
    core.switch_model.assert_called_once()
    assert not manager._operation.locked()

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
import json
import pytest

from allma_model.ui.backup_controller import BackupController
from allma_model.utils.backup_runtime import BackupRuntime
from allma_model.utils.state_restore import PENDING
from test_backup_runtime import core


def controller(tmp_path):
    c=core(tmp_path);c.backups=BackupRuntime(c)
    bridge=SimpleNamespace(core=c,is_android=False,execute_js=Mock())
    return BackupController(bridge),bridge


def test_desktop_export_fails_without_leaving_password_or_temporary_plaintext(tmp_path):
    control,bridge=controller(tmp_path)
    control._run('backup_export','private-password-123',None)
    assert control.pending is None
    assert not list(tmp_path.glob('.allma-transfer-*'))
    assert 'private-password-123' not in str(bridge.execute_js.call_args_list)
    assert not (tmp_path/PENDING).exists()


def test_restore_requires_verified_preview_and_does_not_guess_backup(tmp_path):
    control,bridge=controller(tmp_path)
    control._run('backup_confirm_restore',None,None)
    assert not (tmp_path/PENDING).exists()
    assert any('Seleziona' in str(call) for call in bridge.execute_js.call_args_list)


def test_confirm_restore_preserves_pre_restore_snapshot_and_stages_without_live_replacement(tmp_path):
    from allma_model.utils.state_backup import verify_archive
    control,bridge=controller(tmp_path);store=control.runtime.store
    store.create();old=store.latest()
    transfer=tmp_path/'transfer';transfer.mkdir()
    (transfer/'verified.zip').write_bytes(old.read_bytes())
    (store.root/'allma_settings.json').write_text('{"current":true}')
    control.preview={'directory':str(transfer)}
    control._run('backup_confirm_restore',None,None)
    assert (tmp_path/PENDING).is_file()
    assert json.loads((store.root/'allma_settings.json').read_text())=={'current':True}
    assert control.preview is None
    destination=tmp_path/'before';destination.mkdir();verify_archive(store.latest(),destination)
    assert json.loads((destination/'allma_settings.json').read_text())=={'current':True}


def test_cancel_restore_removes_only_unpublished_preview(tmp_path):
    control,bridge=controller(tmp_path)
    temporary=tmp_path/'preview';temporary.mkdir();(temporary/'verified.zip').write_bytes(b'preview')
    control.preview={'directory':str(temporary)}
    control._run('backup_cancel_restore',None,None)
    assert not temporary.exists() and not (tmp_path/PENDING).exists()
    assert (control.runtime.store.root/'allma_settings.json').is_file()


@pytest.mark.parametrize('wrong_password',[False,True])
def test_document_import_verifies_before_exposing_restore_confirmation(tmp_path,monkeypatch,wrong_password):
    import os,sys
    from types import ModuleType
    from allma_model.utils.backup_crypto import encrypt_backup
    control,bridge=controller(tmp_path);store=control.runtime.store;store.create()
    remote=tmp_path/'document.allma'
    encrypt_backup(store.latest(),remote,'transfer-password-123')
    descriptor=remote.open('rb')
    pfd=SimpleNamespace(getFd=descriptor.fileno,close=descriptor.close)
    resolver=SimpleNamespace(openFileDescriptor=lambda uri,mode:pfd)
    java=ModuleType('jnius');java.autoclass=lambda _:SimpleNamespace(mActivity=SimpleNamespace(getContentResolver=lambda:resolver))
    monkeypatch.setitem(sys.modules,'jnius',java)
    temporary=tmp_path/'transfer';temporary.mkdir()
    control.pending={'directory':str(temporary),'password':'wrong-password-123' if wrong_password else 'transfer-password-123'}
    original=(store.root/'allma_settings.json').read_bytes()
    control._transfer('synthetic-uri',False)
    assert control.pending is None and not (tmp_path/PENDING).exists()
    assert (store.root/'allma_settings.json').read_bytes()==original
    assert (control.preview is None)==wrong_password
    if not wrong_password:
        assert (Path(control.preview['directory'])/'verified.zip').exists()
        control.close()
    assert not temporary.exists()
    assert 'transfer-password-123' not in str(bridge.execute_js.call_args_list)


def test_restore_of_valid_copy_can_recover_corrupt_source_without_discarding_its_bytes(tmp_path):
    from allma_model.utils.state_restore import apply_pending_restore
    control,bridge=controller(tmp_path);store=control.runtime.store;store.create()
    transfer=tmp_path/'transfer';transfer.mkdir()
    (transfer/'verified.zip').write_bytes(store.latest().read_bytes())
    broken=b'{original damaged JSON'
    (store.root/'allma_settings.json').write_bytes(broken)
    control.preview={'directory':str(transfer)}
    control._run('backup_confirm_restore',None,None)
    assert (tmp_path/PENDING).exists()
    assert (store.root/'allma_settings.json').read_bytes()==broken
    receipt=apply_pending_restore(tmp_path)
    assert (tmp_path/receipt['previous']/'allma_settings.json').read_bytes()==broken
    assert json.loads((store.root/'allma_settings.json').read_text())=={}
    assert any('previous_copy_verified' in str(call) and 'false' in str(call) for call in bridge.execute_js.call_args_list)

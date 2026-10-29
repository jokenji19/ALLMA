"""Restore into a separate installation; never transfer model files or grants."""
import json
import sqlite3
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from allma_model.utils.runtime_storage import prepare_runtime_storage
from allma_model.utils.state_backup import StateBackups,verify_archive
from allma_model.llm.model_binding import saved_model_selection,ModelSelectionRequired
from allma_model.ui.system_notifications import SystemNotifications

MODEL={'version':1,'model_name':'chosen.gguf','reasoning':True}
NOTICES={'version':1,'enabled':True,'last_sent':{'message':1000}}


def seed(root):
    root.mkdir(parents=True,exist_ok=True)
    with sqlite3.connect(root/'allma.db') as db:db.execute('CREATE TABLE evidence(value TEXT)')
    for name,data in [('model_binding.json',MODEL),('notifications.json',NOTICES)]:
        (root/name).write_text(json.dumps(data))
    (root/'allma_memory.json').write_text(json.dumps({'messages':[],'conversations':{},'user_data':{'u':{'name':'Synthetic'}}}))


def transfer(tmp_path):
    source=Path(prepare_runtime_storage(tmp_path/'source'));seed(source)
    backups=StateBackups(source);backups.create()
    encrypted=tmp_path/'portable.allma';backups.export(encrypted,'Password-sintetica-portabile!')
    target=Path(prepare_runtime_storage(tmp_path/'target'))
    StateBackups(target).stage_encrypted_restore(encrypted,'Password-sintetica-portabile!')
    prepare_runtime_storage(target.parent)
    return source,target


def test_encrypted_transfer_keeps_preferences_history_and_excludes_weights(tmp_path):
    source,target=transfer(tmp_path)
    for name in ['model_binding.json','notifications.json','allma_memory.json']:
        assert (target/name).read_bytes()==(source/name).read_bytes()
    assert not list(target.rglob('*.gguf'))
    models=target.parent/'models';models.mkdir();(models/'chosen.gguf').write_bytes(b'GGUF')
    selected,reasoning=saved_model_selection(models,target/'model_binding.json')
    assert selected==models/'chosen.gguf' and reasoning is True


def test_restored_missing_model_does_not_guess_another_motor_or_modify_preference(tmp_path):
    source,target=transfer(tmp_path);models=target.parent/'models';models.mkdir()
    (models/'different.gguf').write_bytes(b'GGUF')
    with pytest.raises(ModelSelectionRequired):saved_model_selection(models,target/'model_binding.json')
    assert (target/'model_binding.json').read_bytes()==(source/'model_binding.json').read_bytes()
    assert json.loads((target/'allma_memory.json').read_text())['user_data']['u']['name']=='Synthetic'


def test_restored_notification_consent_is_not_an_android_permission(tmp_path):
    _,target=transfer(tmp_path)
    native=Mock(allowed=Mock(return_value=False))
    notices=SystemNotifications(target/'notifications.json',native,clock=lambda:2000)
    assert notices.status()=={'supported':True,'enabled':True,'allowed':False,'active':False}
    assert not notices.publish('message')
    native.request.assert_not_called();native.post.assert_not_called()
    native.allowed.return_value=True
    assert notices.publish('message')
    native.post.assert_called_once()


@pytest.mark.parametrize('name,bad',[
    ('model_binding.json',dict(MODEL,version=True)),
    ('model_binding.json',dict(MODEL,version=2)),
    ('model_binding.json',dict(MODEL,model_name='../outside.gguf')),
    ('model_binding.json',dict(MODEL,model_name='C:\\outside.gguf')),
    ('model_binding.json',dict(MODEL,reasoning='yes')),
    ('model_binding.json',dict(MODEL,model_name='bad\x00.gguf')),
    ('notifications.json',dict(NOTICES,version=2)),
    ('notifications.json',dict(NOTICES,enabled='yes')),
    ('notifications.json',dict(NOTICES,last_sent=[])),
    ('notifications.json',dict(NOTICES,last_sent={'message':True})),
    ('notifications.json',dict(NOTICES,last_sent={'message':-1})),
    ('notifications.json',dict(NOTICES,last_sent={'message':10**400})),
    ('notifications.json',dict(NOTICES,android_permission=True)),
])
def test_bad_preferences_cannot_replace_a_verified_snapshot(tmp_path,name,bad):
    root=tmp_path/'state';seed(root);store=StateBackups(root);store.create()
    old=store.latest();blob=old.read_bytes();index=store.catalog.read_bytes()
    (root/name).write_text(json.dumps(bad))
    with pytest.raises(ValueError):store.create()
    assert store.latest()==old and old.read_bytes()==blob and store.catalog.read_bytes()==index


@pytest.mark.parametrize('name,bad',[
    ('model_binding.json',dict(MODEL,model_name='../outside.gguf')),
    ('notifications.json',dict(NOTICES,version=9000)),
])
def test_import_validates_preference_schema_even_with_matching_file_digest(tmp_path,name,bad):
    import hashlib,zipfile
    from allma_model.utils.state_restore import stage_restore,PENDING
    source=tmp_path/'source';seed(source);store=StateBackups(source);store.create()
    with zipfile.ZipFile(store.latest()) as z:entries={key:z.read(key) for key in z.namelist()}
    payload=json.dumps(bad).encode();entries['state/'+name]=payload
    manifest=json.loads(entries['manifest.json'])
    manifest['files'][name]={'size':len(payload),'sha256':hashlib.sha256(payload).hexdigest()}
    entries['manifest.json']=json.dumps(manifest).encode()
    archive=tmp_path/'untrusted.zip'
    with zipfile.ZipFile(archive,'w') as z:
        for key,value in entries.items():z.writestr(key,value)
    target=Path(prepare_runtime_storage(tmp_path/'target'));seed(target)
    original={q.name:q.read_bytes() for q in target.iterdir() if q.is_file()}
    with pytest.raises(ValueError):stage_restore(target,archive)
    assert not (target.parent/PENDING).exists()
    assert {q.name:q.read_bytes() for q in target.iterdir() if q.is_file()}==original


def test_older_backup_without_preferences_is_restorable_and_never_merges_legacy(tmp_path):
    source=Path(prepare_runtime_storage(tmp_path/'source'));seed(source)
    (source/'model_binding.json').unlink();(source/'notifications.json').unlink()
    store=StateBackups(source);store.create()
    target=Path(prepare_runtime_storage(tmp_path/'target'));seed(target)
    from allma_model.utils.state_restore import stage_restore
    stage_restore(target,store.latest())
    legacy=tmp_path/'legacy';seed(legacy)
    prepare_runtime_storage(target.parent,legacy)
    assert not (target/'model_binding.json').exists() and not (target/'notifications.json').exists()


def test_legacy_preference_migration_is_durable_and_never_overwrites_current(tmp_path):
    legacy=tmp_path/'legacy';seed(legacy)
    state=Path(prepare_runtime_storage(tmp_path/'device',legacy))
    for name in ['model_binding.json','notifications.json']:assert (state/name).read_bytes()==(legacy/name).read_bytes()
    changed=dict(MODEL,model_name='new.gguf');(state/'model_binding.json').write_text(json.dumps(changed))
    prepare_runtime_storage(state.parent,legacy)
    assert json.loads((state/'model_binding.json').read_text())==changed


def test_notification_clock_rollback_cannot_suspend_delivery_indefinitely(tmp_path):
    path=tmp_path/'notifications.json';path.write_text(json.dumps(NOTICES))
    native=Mock(allowed=Mock(return_value=True),post=Mock(return_value=True))
    notices=SystemNotifications(path,native,clock=lambda:100)
    assert notices.publish('message')
    assert not notices.publish('message')


def test_invalid_notification_file_never_partially_enables_consent(tmp_path):
    path=tmp_path/'notifications.json';path.write_text(json.dumps(dict(NOTICES,last_sent=[])))
    notices=SystemNotifications(path,Mock())
    assert notices.enabled is False and notices.last_sent=={}


@pytest.mark.parametrize('bad',[dict(MODEL,version=3),dict(MODEL,model_name='../outside.gguf')])
def test_unsupported_or_unsafe_local_model_preference_requires_user_choice(tmp_path,bad):
    path=tmp_path/'model_binding.json';path.write_text(json.dumps(bad))
    with pytest.raises(ModelSelectionRequired):saved_model_selection(tmp_path,path)
    assert json.loads(path.read_text())==bad


@pytest.mark.parametrize('present',[False,True])
def test_core_restored_selection_links_only_the_requested_local_motor(tmp_path,monkeypatch,present):
    from allma_model.core.allma_core import ALLMACore
    import allma_model.llm.mobile_gemma_wrapper as wrapper
    models=tmp_path/'models';models.mkdir();(models/'different.gguf').write_bytes(b'GGUF')
    if present:(models/'chosen.gguf').write_bytes(b'GGUF')
    (tmp_path/'model_binding.json').write_text(json.dumps(MODEL))
    brain=SimpleNamespace(_llm_ready=False,models_dir=str(models),db_path=str(tmp_path/'allma.db'),
        reasoning_engine=SimpleNamespace(),dream_manager=SimpleNamespace(tot=SimpleNamespace()),
        decision_runtime=object(),conversational_memory=object())
    memory=brain.conversational_memory;engine=SimpleNamespace(llm=object())
    factory=Mock(return_value=engine)
    monkeypatch.setattr(wrapper,'LLAMA_CPP_AVAILABLE',True)
    monkeypatch.setattr(wrapper,'MobileGemmaWrapper',factory)
    ALLMACore._ensure_mobile_llm(brain)
    assert brain.conversational_memory is memory
    assert json.loads((tmp_path/'model_binding.json').read_text())==MODEL
    if present:
        assert brain._llm_ready and not brain._model_selection_required
        assert brain.reasoning_engine.llm is brain.dream_manager.tot.llm is engine
        assert factory.call_args.kwargs['model_name']=='chosen.gguf'
        assert factory.call_args.kwargs['reasoning'] is True
    else:
        assert not brain._llm_ready and brain._model_selection_required
        factory.assert_not_called()


def test_missing_model_recovery_frontend():
    import subprocess
    root=Path(__file__).resolve().parents[2]
    subprocess.run(['node','tests/regression/model_restore_checks.cjs'],cwd=root,check=True,capture_output=True,text=True)

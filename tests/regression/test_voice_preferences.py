import hashlib
import io
import json
import tarfile
from pathlib import Path
import pytest
from allma_model.voice_system.languages import language_tag, voice_options
from allma_model.voice_system.preferences import VoicePreferences
from allma_model.core.module_state_manager import ModuleStateManager
from allma_model.voice_system import voice_pack


@pytest.mark.parametrize('value,expected',[('en','en-US'),('pt_br','pt-BR'),('de-DE','de-DE'),('ru','ru-RU'),('zh-Hant-TW','zh-Hant-TW'),('bad;tag',None),('',None),(None,None)])
def test_language_validation_does_not_relabel_foreign_languages_italian(value,expected):
    assert language_tag(value,fallback=None)==expected


def test_voice_preferences_survive_reload_in_existing_archive(tmp_path):
    manager=ModuleStateManager(str(tmp_path/'modules.db'))
    options={'language':'auto','voice':'if_sara','allow_service_fallback':True}
    VoicePreferences(manager).update(options)
    assert VoicePreferences(manager).options==options
    assert voice_options({'allow_service_fallback':'true','voice':'unknown'})==voice_options()


def test_corrupted_voice_preferences_remain_untouched(tmp_path):
    manager=ModuleStateManager(str(tmp_path/'modules.db'))
    import sqlite3
    with sqlite3.connect(manager.db_path) as connection:
        connection.execute('INSERT INTO module_states(module_name,state_json) VALUES(?,?)',(VoicePreferences.KEY,'{broken'))
    preferences=VoicePreferences(manager)
    with pytest.raises(ValueError):preferences.update({})
    with sqlite3.connect(manager.db_path) as connection:
        assert connection.execute('SELECT state_json FROM module_states').fetchone()[0]=='{broken'


def archive(tmp_path,monkeypatch,malicious=False):
    contents={'model.int8.onnx':b'model','voices.bin':b'voices','tokens.txt':b'tokens','espeak-ng-data/it_dict':b'it'}
    target=tmp_path/'voice.tar.bz2'
    with tarfile.open(target,'w:bz2') as package:
        for name,data in contents.items():
            member=tarfile.TarInfo(voice_pack.PACK_DIRECTORY+'/'+name)
            member.size=len(data);package.addfile(member,io.BytesIO(data))
        if malicious:
            member=tarfile.TarInfo('../escape');member.size=1;package.addfile(member,io.BytesIO(b'x'))
    monkeypatch.setattr(voice_pack,'PACK_BYTES',target.stat().st_size)
    monkeypatch.setattr(voice_pack,'PACK_SHA256',voice_pack.digest(target))
    monkeypatch.setattr(voice_pack,'FILES',{name:hashlib.sha256(data).hexdigest() for name,data in contents.items() if '/' not in name})
    return target


def test_model_archive_is_authenticated_before_extracting(tmp_path):
    target=tmp_path/'bad.tar.bz2';target.write_bytes(b'not a model')
    pack=voice_pack.VoicePack(tmp_path/'install')
    with pytest.raises(ValueError):pack.install_archive(target)
    assert not pack.directory.exists()


def test_model_archive_rejects_path_traversal_even_with_valid_hash(tmp_path,monkeypatch):
    target=archive(tmp_path,monkeypatch,True)
    pack=voice_pack.VoicePack(tmp_path/'install')
    with pytest.raises(ValueError):pack.install_archive(target)
    assert not (tmp_path/'escape').exists() and not pack.directory.exists()


def test_model_integrity_and_atomic_repair(tmp_path,monkeypatch):
    target=archive(tmp_path,monkeypatch)
    pack=voice_pack.VoicePack(tmp_path/'install')
    pack.install_archive(target)
    assert pack.ready and pack.verify()==str(pack.directory)
    (pack.directory/'voices.bin').write_bytes(b'corrupt')
    reloaded=voice_pack.VoicePack(pack.directory)
    with pytest.raises(ValueError):reloaded.verify()
    assert not reloaded.ready
    reloaded.install_archive(target)
    assert reloaded.ready and reloaded.verify()==str(pack.directory)
    assert not (tmp_path/'install.invalid').exists()


def test_verified_voice_assets_are_rechecked_after_file_replacement(tmp_path,monkeypatch):
    source=archive(tmp_path,monkeypatch)
    pack=voice_pack.VoicePack(tmp_path/'install')
    pack.install_archive(source);pack.verify()
    (pack.directory/'voices.bin').write_bytes(b'changed after verification')
    with pytest.raises(ValueError):pack.verify()
    assert not pack.ready


def test_voice_pack_close_prevents_late_download(tmp_path,monkeypatch):
    from unittest.mock import Mock
    thread=Mock();monkeypatch.setattr(voice_pack.threading,'Thread',thread)
    pack=voice_pack.VoicePack(tmp_path/'install')
    pack.close()
    assert pack.download() is False
    assert not pack.busy
    thread.assert_not_called()


def test_voice_download_cancelled_before_worker_starts_never_opens_network(tmp_path,monkeypatch):
    from unittest.mock import Mock
    pending=[]
    class DelayedThread:
        def __init__(self,target,**kwargs):self.target=target
        def start(self):pending.append(self.target)
    monkeypatch.setattr(voice_pack.threading,'Thread',DelayedThread)
    network=Mock();monkeypatch.setattr(voice_pack.urllib.request,'urlopen',network)
    pack=voice_pack.VoicePack(tmp_path/'install')
    assert pack.download()
    pack.close();pending.pop()()
    network.assert_not_called()
    assert not pack.busy and pack.download() is False

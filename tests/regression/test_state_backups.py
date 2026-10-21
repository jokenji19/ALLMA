"""Preservation, authenticated transfer and restart-safe restore challenges."""
from copy import deepcopy
from datetime import datetime
import json
from pathlib import Path
import sqlite3
from unittest.mock import patch
import zipfile

import pytest

from allma_model.utils.backup_crypto import encrypt_backup,decrypt_backup,BackupCryptoError,CHUNK
from allma_model.utils.state_backup import StateBackups,BackupError,verify_archive
from allma_model.utils.state_restore import stage_restore,apply_pending_restore,PENDING
from allma_model.utils.runtime_storage import prepare_runtime_storage

PASSWORD='Archivio-di-prova-2030!'


def data(root,text='Un ricordo di prova.',year=2026):
    root=Path(root);root.mkdir(parents=True,exist_ok=True)
    memory={'messages':[{'conversation_id':'c','role':'user','user_id':'u','content':text,
             'timestamp':datetime(year,1,1).isoformat(),'metadata':{}}],
            'conversations':{},'user_data':{}}
    (root/'allma_memory.json').write_text(json.dumps(memory,ensure_ascii=False))
    (root/'cognitive_state.json').write_text(json.dumps({'version':1,'sections':{'personality':{'learned':True}}}))
    with sqlite3.connect(root/'allma.db') as db:
        db.execute('CREATE TABLE IF NOT EXISTS facts(value TEXT)')
        db.execute('INSERT INTO facts VALUES (?)',(text,))
    return memory


@pytest.mark.parametrize('year',[1,1970,2038,2256,3000,9000,9999])
def test_backup_restore_preserves_far_dated_records_without_calendar_expiry(tmp_path,year):
    root=Path(prepare_runtime_storage(tmp_path))
    original=data(root,year=year)
    backups=StateBackups(root)
    result=backups.create()
    assert result['verified']
    archive=backups.latest()
    (root/'allma_memory.json').write_text(json.dumps({**original,'messages':[]}))
    stage_restore(root,archive)
    receipt=apply_pending_restore(tmp_path)
    assert json.loads((root/'allma_memory.json').read_text())==original
    assert json.loads((tmp_path/receipt['previous']/'allma_memory.json').read_text())['messages']==[]
    assert not (tmp_path/PENDING).exists()


def test_sqlite_snapshot_includes_committed_wal_without_copying_a_live_db(tmp_path):
    root=tmp_path/'state';data(root)
    db=sqlite3.connect(root/'allma.db')
    db.execute('PRAGMA journal_mode=WAL')
    db.execute("INSERT INTO facts VALUES ('written in WAL')");db.commit()
    try:
        backups=StateBackups(root);backups.create()
        dest=tmp_path/'extracted';dest.mkdir()
        verify_archive(backups.latest(),dest)
        with sqlite3.connect(dest/'allma.db') as restored:
            assert restored.execute('SELECT value FROM facts').fetchall()[-1]==('written in WAL',)
    finally:db.close()


def test_corrupt_source_cannot_replace_a_previous_good_backup(tmp_path):
    root=tmp_path/'state';data(root)
    backups=StateBackups(root);backups.create();good=backups.latest().read_bytes()
    (root/'allma_memory.json').write_text('{broken')
    with pytest.raises((BackupError,ValueError)):
        backups.create()
    assert backups.latest().read_bytes()==good
    assert (root/'allma_memory.json').read_text()=='{broken'


def test_models_code_and_vector_cache_are_not_part_of_personal_backup(tmp_path):
    root=tmp_path/'state';data(root)
    for name in ['models/model.gguf','private.py','data/allma_vectors.db','benchmarks/reports/r.json']:
        p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b'not authoritative')
    backups=StateBackups(root);backups.create()
    with zipfile.ZipFile(backups.latest()) as archive:
        assert set(archive.namelist())=={'manifest.json','state/allma.db','state/allma_memory.json','state/cognitive_state.json'}


@pytest.mark.parametrize('mutation',['password','truncate','append','tamper','header'])
def test_encrypted_import_rejects_mutation_and_preserves_target(tmp_path,mutation):
    source=tmp_path/'source';source.write_bytes(b'secret history'*40000)
    encrypted=tmp_path/'copy.allma';encrypt_backup(source,encrypted,PASSWORD)
    original=encrypted.read_bytes();blob=bytearray(original)
    password=PASSWORD
    if mutation=='password':password='A-different-password!'
    elif mutation=='truncate':blob=blob[:-16]
    elif mutation=='append':blob.extend(b'added')
    elif mutation=='tamper':blob[len(blob)//2]^=1
    else:blob[25]^=1
    encrypted.write_bytes(blob)
    target=tmp_path/'existing';target.write_bytes(b'keep this')
    with pytest.raises(BackupCryptoError):decrypt_backup(encrypted,target,password)
    assert target.read_bytes()==b'keep this'
    assert not list(tmp_path.glob('.allma-crypto-*'))


@pytest.mark.parametrize('size',[0,1,CHUNK-1,CHUNK,CHUNK+1,CHUNK*3+11])
def test_chunked_encrypted_roundtrip_is_exact(tmp_path,size):
    pattern=b'\x00\xffALLMA\n'
    source=tmp_path/'source';source.write_bytes((pattern*((size+len(pattern)-1)//len(pattern)))[:size])
    encoded=tmp_path/'encoded';decoded=tmp_path/'decoded'
    encrypt_backup(source,encoded,PASSWORD);decrypt_backup(encoded,decoded,PASSWORD)
    assert decoded.read_bytes()==source.read_bytes()
    assert source.stat().st_size==size


@pytest.mark.parametrize('rename_number',[1,2])
def test_restore_resumes_after_interrupted_directory_rename(tmp_path,rename_number):
    root=Path(prepare_runtime_storage(tmp_path));original=data(root,'Old source')
    backups=StateBackups(root);backups.create()
    data(root,'Current source')
    current=(root/'allma_memory.json').read_bytes()
    stage_restore(root,backups.latest())
    import allma_model.utils.state_restore as restore
    replace=restore.os.replace
    count=0
    def interrupted(source,target):
        nonlocal count
        replace(source,target)
        if Path(source).name.startswith('allma_state'):
            count+=1
            if count==rename_number:raise OSError('synthetic crash after rename')
    with patch.object(restore.os,'replace',side_effect=interrupted):
        with pytest.raises(OSError):apply_pending_restore(tmp_path)
    receipt=apply_pending_restore(tmp_path)
    assert json.loads((root/'allma_memory.json').read_text())==original
    assert (tmp_path/receipt['previous']/'allma_memory.json').read_bytes()==current


def test_damaged_staged_restore_never_replaces_live_directory(tmp_path):
    root=Path(prepare_runtime_storage(tmp_path));data(root)
    backups=StateBackups(root);backups.create();stage_restore(root,backups.latest())
    original=(root/'allma_memory.json').read_bytes()
    marker=json.loads((tmp_path/PENDING).read_text())
    (tmp_path/marker['candidate']/'allma_memory.json').write_text('changed')
    with pytest.raises(BackupError):apply_pending_restore(tmp_path)
    assert (root/'allma_memory.json').read_bytes()==original


def test_untrusted_zip_path_is_rejected_before_live_data_changes(tmp_path):
    malicious=tmp_path/'bad.zip'
    with zipfile.ZipFile(malicious,'w') as archive:
        archive.writestr('state/../../escape','bad')
        archive.writestr('manifest.json',json.dumps({'version':1,'primary_database':'allma.db',
            'files':{'../../escape':{'size':3,'sha256':'0'*64}}}))
    with pytest.raises(BackupError):verify_archive(malicious)
    assert not (tmp_path.parent/'escape').exists()


def test_manual_encrypted_export_can_be_staged_on_another_installation(tmp_path):
    source=Path(prepare_runtime_storage(tmp_path/'first'));original=data(source,'Esperienza condivisa.',year=3010)
    backups=StateBackups(source);backups.create()
    encrypted=tmp_path/'portable.allma';backups.export(encrypted,PASSWORD)
    target=Path(prepare_runtime_storage(tmp_path/'second'));data(target,'Other installation')
    result=StateBackups(target).stage_encrypted_restore(encrypted,PASSWORD)
    assert result['restart_required']
    prepare_runtime_storage(target.parent)
    assert json.loads((target/'allma_memory.json').read_text())==original


def test_catalog_corruption_preserves_backup_bytes_and_blocks_silent_reset(tmp_path):
    root=tmp_path/'state';data(root);backups=StateBackups(root);backups.create()
    existing=backups.latest();original=existing.read_bytes()
    backups.catalog.write_text('{broken')
    assert not backups.status()['available']
    with pytest.raises(BackupError):backups.create()
    assert existing.read_bytes()==original and backups.catalog.read_text()=='{broken'


def test_explicit_catalog_repair_rebuilds_only_verified_files(tmp_path):
    root=tmp_path/'state';data(root);store=StateBackups(root);store.create()
    good=store.latest();blob=good.read_bytes()
    bad=store.directory/('backup-0000000000000002-'+'a'*32+'.zip');bad.write_bytes(b'incomplete')
    store.catalog.write_text('{damaged')
    result=store.repair_catalog()
    assert result=={'verified':1,'rejected':1}
    assert store.latest().read_bytes()==blob and bad.read_bytes()==b'incomplete'
    assert store.catalog.with_name('index.json.invalid.bak').read_text()=='{damaged'


def test_catalog_retention_preserves_verified_generations_and_external_files(tmp_path):
    root=tmp_path/'state';data(root);store=StateBackups(root)
    for _ in range(9):store.create()
    other=store.directory/'personal.zip';other.write_bytes(b'never remove')
    store.create()
    assert len(store._index()['entries'])==7
    assert len(list(store.directory.glob('backup-*.zip')))==7
    assert other.read_bytes()==b'never remove'
    store.verify_latest()


@pytest.mark.parametrize('value',[True,-1,'9'])
def test_catalog_rejects_malformed_sequence_without_mutating_copies(tmp_path,value):
    root=tmp_path/'state';data(root);store=StateBackups(root);store.create()
    good=store.latest();blob=good.read_bytes()
    index=store._index();index['entries'][0]['sequence']=value
    store.catalog.write_text(json.dumps(index))
    with pytest.raises(BackupError):store.create()
    assert good.read_bytes()==blob


def test_no_space_never_rotates_or_deletes_good_backup(tmp_path):
    from types import SimpleNamespace
    root=tmp_path/'state';data(root);store=StateBackups(root);store.create()
    good=store.latest();blob=good.read_bytes();index=store.catalog.read_bytes()
    with patch('allma_model.utils.state_backup.shutil.disk_usage',return_value=SimpleNamespace(free=0)):
        with pytest.raises(BackupError):store.create()
    assert good.read_bytes()==blob and store.catalog.read_bytes()==index


def test_cancelled_copy_keeps_last_good_archive_and_catalog(tmp_path):
    from threading import Event
    root=tmp_path/'state';data(root);store=StateBackups(root);store.create()
    good=store.latest();blob=good.read_bytes();index=store.catalog.read_bytes()
    cancel=Event();cancel.set()
    with pytest.raises(BackupError):store.create(cancel_event=cancel)
    assert good.read_bytes()==blob and store.catalog.read_bytes()==index


def test_changing_source_is_not_admitted_as_consistent_snapshot(tmp_path):
    import allma_model.utils.state_backup as module
    root=tmp_path/'state';data(root);store=StateBackups(root);store.create()
    latest=store.latest();blob=latest.read_bytes()
    original=module._check_data
    def mutate(path,name):
        original(path,name)
        if name=='cognitive_state.json':
            (root/'allma_memory.json').write_text('{changed during snapshot}')
    with patch.object(module,'_check_data',side_effect=mutate):
        with pytest.raises(BackupError):store.create()
    assert store.latest().read_bytes()==blob


@pytest.mark.parametrize('name,value',[
    ('allma_memory.json',{'messages':[],'conversations':{'u':[{}]}}),
    ('cognitive_state.json',{'version':True,'sections':{}}),
    ('answer_recall.json',{'version':1,'records':{'bad':{}},'delivery_checkpoint':0}),
    ('incremental_cache/knowledge_states.json',{'schema_version':9000})])
def test_invalid_semantic_state_is_not_published_as_verified(tmp_path,name,value):
    root=tmp_path/'state';data(root);path=root/name;path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(value))
    with pytest.raises((BackupError,ValueError,KeyError)):StateBackups(root).create()
    assert not list(root.glob('.allma_backups/backup-*.zip'))


def test_non_finite_json_is_not_a_valid_backup(tmp_path):
    root=tmp_path/'state';data(root)
    (root/'allma_settings.json').write_text('{"age": NaN}')
    with pytest.raises(ValueError):StateBackups(root).create()


def test_restored_state_is_never_merged_with_bundled_legacy_state(tmp_path):
    root=Path(prepare_runtime_storage(tmp_path/'device'));original=data(root)
    store=StateBackups(root);store.create();stage_restore(root,store.latest())
    legacy=tmp_path/'legacy';legacy.mkdir()
    (legacy/'answer_recall.json').write_text('{"legacy":true}')
    prepare_runtime_storage(root.parent,legacy)
    prepare_runtime_storage(root.parent,legacy)
    assert not (root/'answer_recall.json').exists()
    assert json.loads((root/'allma_memory.json').read_text())==original


def test_unsupported_restore_target_fails_before_creating_marker(tmp_path):
    root=tmp_path/'allma_state';data(root);store=StateBackups(root);store.create()
    with pytest.raises(BackupError):stage_restore(root,store.latest(),primary='another.db')
    assert not (tmp_path/PENDING).exists()


def test_directory_fsync_failure_does_not_report_false_write_rollback(tmp_path):
    from allma_model.utils.persistence import atomic_write_json
    target=tmp_path/'state.json'
    with patch('allma_model.utils.persistence.os.open',side_effect=OSError('not supported')):
        # tempfile also uses os.open, so exercise the directory helper separately.
        from allma_model.utils.persistence import sync_directory
        assert sync_directory(tmp_path) is False
    with patch('allma_model.utils.persistence.sync_directory',return_value=False):
        atomic_write_json(target,{'new':True})
    assert json.loads(target.read_text())=={'new':True}


def test_automatic_backup_skips_unchanged_data_even_after_large_clock_jump(tmp_path):
    from datetime import timezone
    root=tmp_path/'state';data(root);store=StateBackups(root)
    assert store.due()
    store.create()
    assert not store.due(datetime(9000,1,1,tzinfo=timezone.utc))
    (root/'allma_settings.json').write_text('{"new":true}')
    assert store.due(datetime(9000,1,1,tzinfo=timezone.utc))
    assert store.due(datetime(1970,1,1,tzinfo=timezone.utc))


def test_dream_journal_and_review_database_are_preserved(tmp_path):
    root=tmp_path/'state';data(root);(root/'data').mkdir()
    (root/'data/dream_journal.json').write_text('[{"text":"Sogno di prova","user_id":"u"}]')
    with sqlite3.connect(root/'data/dream_journal.json.reviews.db') as db:
        db.execute('CREATE TABLE reviews(id TEXT,status TEXT)')
        db.execute("INSERT INTO reviews VALUES ('synthetic','corrected')")
    store=StateBackups(root);store.create();dest=tmp_path/'extracted';dest.mkdir()
    verify_archive(store.latest(),dest)
    assert (dest/'data/dream_journal.json').read_bytes()==(root/'data/dream_journal.json').read_bytes()
    with sqlite3.connect(dest/'data/dream_journal.json.reviews.db') as db:
        assert db.execute('SELECT status FROM reviews').fetchone()==('corrected',)


def test_corruption_preservation_never_copies_android_security_attributes(tmp_path):
    from allma_model.utils.persistence import preserve_invalid_file
    path=tmp_path/'damaged.json';path.write_bytes(b'{original bytes')
    with patch('shutil.copy2',side_effect=PermissionError('SELinux metadata')):
        backup=preserve_invalid_file(path)
        second=preserve_invalid_file(path)
    assert backup.read_bytes()==path.read_bytes()==second.read_bytes()
    assert backup.stat().st_mode&0o777==0o600

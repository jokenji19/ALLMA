"""Fixed 28 preservation challenges. Synthetic archives, native crypto on Android."""
from datetime import datetime
import json
from pathlib import Path
import sqlite3
from types import SimpleNamespace
from threading import RLock
from unittest.mock import patch
import zipfile

from memory_recovery_battery import require,run_challenges
from allma_model.utils.state_backup import StateBackups,BackupError,verify_archive
from allma_model.utils.state_restore import stage_restore,apply_pending_restore,PENDING
from allma_model.utils.backup_crypto import encrypt_backup,decrypt_backup,cipher_factory,BackupCryptoError,CHUNK

CASES=[]
PASSWORD='ALLMA-copia-sintetica-2040!'


def case(group,name,criterion):
    def register(fn):CASES.append((group,name,criterion,fn));return fn
    return register


def seed(root,year=2026,text='Esperienza sintetica'):
    root.mkdir(parents=True,exist_ok=True)
    archive={'messages':[{'conversation_id':'c','role':'user','content':text,'metadata':{},'user_id':'u',
                         'timestamp':datetime(year,1,1).isoformat()}],'conversations':{},'user_data':{}}
    (root/'allma_memory.json').write_text(json.dumps(archive))
    (root/'cognitive_state.json').write_text(json.dumps({'version':1,'sections':{'personality':{'learned':True}}}))
    (root/'data').mkdir(exist_ok=True)
    (root/'data/dream_journal.json').write_text('[{"text":"Ipotesi sintetica","user_id":"u"}]')
    with sqlite3.connect(root/'allma.db') as db:
        db.execute('CREATE TABLE IF NOT EXISTS facts(value TEXT)')
        db.execute('INSERT INTO facts VALUES (?)',(text,))
    return archive


for year in (2038,2256,3000,9000):
    def run(path,year=year):
        root=path/'allma_state';original=seed(root,year)
        store=StateBackups(root);store.create()
        (root/'allma_memory.json').write_text('{"messages":[]}')
        stage_restore(root,store.latest());receipt=apply_pending_restore(path)
        require(json.loads((root/'allma_memory.json').read_text())==original,'Date/history changed')
        require((path/receipt['previous']/'allma_memory.json').is_file(),'Original state not preserved')
    case('calendar','year_'+str(year),'No calendar expiry; exact history and prior directory survive restore')(run)


@case('database','committed_wal','Committed WAL rows are included by SQLite backup')
def wal(path):
    root=path/'allma_state';seed(root)
    db=sqlite3.connect(root/'allma.db');db.execute('PRAGMA journal_mode=WAL')
    db.execute("INSERT INTO facts VALUES ('wal row')");db.commit()
    try:
        store=StateBackups(root);store.create();target=path/'extract';target.mkdir();verify_archive(store.latest(),target)
        restored=sqlite3.connect(target/'allma.db')
        try:require(restored.execute('SELECT value FROM facts').fetchall()[-1]==('wal row',),'WAL lost')
        finally:restored.close()
    finally:db.close()


@case('snapshot','corrupt_source','Bad JSON never replaces a verified archive')
def corrupt(path):
    root=path/'allma_state';seed(root);store=StateBackups(root);store.create();original=store.latest().read_bytes()
    (root/'allma_memory.json').write_text('{broken')
    try:store.create()
    except ValueError:pass
    else:raise AssertionError('Corrupt source accepted')
    require(store.latest().read_bytes()==original,'Prior backup changed')


@case('snapshot','repair_catalog','Explicit repair reconstructs catalog from verified files')
def repair(path):
    root=path/'allma_state';seed(root);store=StateBackups(root);store.create()
    store.catalog.write_text('{broken')
    require(not store.status()['available'],'Bad catalog ignored')
    require(store.repair_catalog()['verified']==1,'Verified generation not recovered')
    store.verify_latest()


@case('snapshot','exclude_weights','Models, vector cache and source code never enter personal snapshots')
def exclusions(path):
    root=path/'allma_state';seed(root)
    (root/'model.gguf').write_text('weights');(root/'private.py').write_text('code')
    (root/'data/allma_vectors.db').write_text('cache')
    store=StateBackups(root);store.create()
    with zipfile.ZipFile(store.latest()) as archive:
        require(not any(n.endswith(('.gguf','.py','allma_vectors.db')) for n in archive.namelist()),'Excluded data copied')


@case('crypto','native_compatibility','Native AES-256-GCM matches the desktop reference including AAD and tag')
def crypto_fixture(path):
    backend=cipher_factory(bytes(range(32)));nonce=bytes(range(12));aad=b'ALLMA-test-v1'
    expected=bytes.fromhex('064e9a5684c5b274ff35f6e9dd8c580cf1b5ef5d861e587de6b05bcdcfe1f36cf91d5639089e')
    require(backend.encrypt(nonce,b'ALLMA portable archive',aad)==expected,'Native cipher differs from reference')
    require(backend.decrypt(nonce,expected,aad)==b'ALLMA portable archive','Reference decryption failed')


for size in (0,CHUNK,CHUNK+1):
    def run(path,size=size):
        source=path/'source';source.write_bytes(b'x'*size)
        encrypted=path/'copy.allma';target=path/'target'
        encrypt_backup(source,encrypted,PASSWORD);decrypt_backup(encrypted,target,PASSWORD)
        require(target.read_bytes()==source.read_bytes(),'Chunk roundtrip changed bytes')
    case('crypto','roundtrip_'+str(size),'Authenticated records roundtrip at exact chunk boundaries')(run)


for mutation in ('password','tamper','truncate','append'):
    def run(path,mutation=mutation):
        source=path/'source';source.write_bytes(b'private history'*100)
        encrypted=path/'copy.allma';target=path/'target';target.write_bytes(b'original')
        encrypt_backup(source,encrypted,PASSWORD);blob=bytearray(encrypted.read_bytes())
        password=PASSWORD
        if mutation=='password':password='different-password-000'
        elif mutation=='tamper':blob[-20]^=1
        elif mutation=='truncate':blob=blob[:-16]
        else:blob.extend(b'added')
        encrypted.write_bytes(blob)
        try:decrypt_backup(encrypted,target,password)
        except BackupCryptoError:pass
        else:raise AssertionError('Corrupt/authentication failure accepted')
        require(target.read_bytes()==b'original','Destination overwritten after failure')
    case('crypto','reject_'+mutation,'Authentication failure cannot publish or overwrite restored data')(run)


for boundary in (1,2):
    def run(path,boundary=boundary):
        import allma_model.utils.state_restore as restore
        root=path/'allma_state';original=seed(root);store=StateBackups(root);store.create()
        seed(root,text='Current state');current=(root/'allma_memory.json').read_bytes()
        stage_restore(root,store.latest());replace=restore.os.replace;count=0
        def crash(source,target):
            nonlocal count
            replace(source,target)
            if Path(source).name.startswith('allma_state'):
                count+=1
                if count==boundary:raise OSError('Synthetic interrupted rename')
        with patch.object(restore.os,'replace',side_effect=crash):
            try:apply_pending_restore(path)
            except OSError:pass
        receipt=apply_pending_restore(path)
        require(json.loads((root/'allma_memory.json').read_text())==original,'Restore not resumed')
        require((path/receipt['previous']/'allma_memory.json').read_bytes()==current,'Prior state lost')
    case('restore','interruption_'+str(boundary),'A process death at either rename boundary is recoverable')(run)


@case('restore','reject_paths','Unexpected archive paths fail before extraction')
def bad_paths(path):
    archive=path/'bad.zip'
    with zipfile.ZipFile(archive,'w') as zipped:
        zipped.writestr('state/../../escape','bad')
        zipped.writestr('manifest.json',json.dumps({'version':1,'primary_database':'allma.db','created':datetime.now().astimezone().isoformat(),
            'files':{'../../escape':{'size':3,'sha256':'0'*64}}}))
    try:verify_archive(archive)
    except BackupError:pass
    else:raise AssertionError('Path traversal accepted')
    require(not (path.parent/'escape').exists(),'Extracted outside staging')


@case('learning','logical_order','Learning sequence preserves historical checkpoints without depending on time')
def logical_order(path):
    from allma_model.core.delivery_updates import DeliveryUpdates
    core=SimpleNamespace(db_path=str(path/'allma.db'),answer_recall=SimpleNamespace(delivery_checkpoint=1792230000000000),
        conversational_memory=SimpleNamespace(lock=RLock(),messages=[]))
    updates=DeliveryUpdates(core)
    with patch('time.time_ns',side_effect=AssertionError('Calendar used for sequence')):
        first=updates.prepare_user('u','c','one')['sequence'];second=updates.prepare_user('u','c','two')['sequence']
    require(second==first+1 and first==1792230000000001,'Logical order changed')


def preferences(root):
    values={'model_binding.json':{'version':1,'model_name':'chosen.gguf','reasoning':True},
            'notifications.json':{'version':1,'enabled':True,'last_sent':{'message':1000}}}
    for name,value in values.items():(root/name).write_text(json.dumps(value))
    return values


def portable_install(path):
    from allma_model.utils.runtime_storage import prepare_runtime_storage
    source=Path(prepare_runtime_storage(path/'source'));seed(source);preferences(source)
    store=StateBackups(source);store.create();encrypted=path/'portable.allma';store.export(encrypted,PASSWORD)
    target=Path(prepare_runtime_storage(path/'target'));seed(target,text='Before restore')
    StateBackups(target).stage_encrypted_restore(encrypted,PASSWORD)
    prepare_runtime_storage(target.parent)
    return source,target


@case('portable','encrypted_install','An encrypted export restores preferences and exact history into a separate installation')
def portable_encrypted(path):
    source,target=portable_install(path)
    for name in ('allma_memory.json','cognitive_state.json','model_binding.json','notifications.json'):
        require((source/name).read_bytes()==(target/name).read_bytes(),'Portable state changed: '+name)
    require(not list(target.rglob('*.gguf')),'Model weights copied')
    from allma_model.llm.model_binding import saved_model_selection
    models=target.parent/'models';models.mkdir();(models/'chosen.gguf').write_bytes(b'GGUF')
    selected,reasoning=saved_model_selection(models,target/'model_binding.json')
    require(selected.name=='chosen.gguf' and reasoning is True,'Local model choice lost')


@case('portable','missing_motor','An unavailable saved model requires selection without replacing it or guessing another motor')
def portable_missing_motor(path):
    from allma_model.llm.model_binding import saved_model_selection,ModelSelectionRequired
    source,target=portable_install(path);models=target.parent/'models';models.mkdir()
    (models/'different.gguf').write_bytes(b'GGUF')
    try:saved_model_selection(models,target/'model_binding.json')
    except ModelSelectionRequired:pass
    else:raise AssertionError('Unrequested model selected')
    require((target/'model_binding.json').read_bytes()==(source/'model_binding.json').read_bytes(),'Missing choice discarded')


@case('portable','notification_permission','Restored app consent does not grant Android notification permission or send a notice')
def portable_notification_permission(path):
    from unittest.mock import Mock
    from allma_model.ui.system_notifications import SystemNotifications
    _,target=portable_install(path)
    native=Mock(allowed=Mock(return_value=False),post=Mock(return_value=True))
    notices=SystemNotifications(target/'notifications.json',native,clock=lambda:2000)
    require(notices.enabled and not notices.status()['active'],'System grant fabricated')
    require(not notices.publish('message'),'Notification sent without system permission')
    native.request.assert_not_called();native.post.assert_not_called()
    native.allowed.return_value=True
    require(notices.publish('message'),'Restored app preference lost after system permission granted')


for filename,invalid in [('model_binding.json',{'version':1,'model_name':'../outside.gguf','reasoning':True}),
                         ('notifications.json',{'version':1,'enabled':'true','last_sent':{}})]:
    def run(path,filename=filename,invalid=invalid):
        root=path/'allma_state';seed(root);preferences(root);store=StateBackups(root);store.create()
        old=store.latest();original=old.read_bytes();index=store.catalog.read_bytes()
        (root/filename).write_text(json.dumps(invalid))
        try:store.create()
        except ValueError:pass
        else:raise AssertionError('Invalid portable preference certified')
        require(store.latest()==old and old.read_bytes()==original and store.catalog.read_bytes()==index,'Last verified backup changed')
    case('portable','reject_'+filename.split('.')[0],'An invalid portable preference cannot replace a verified snapshot')(run)


@case('portable','older_snapshot','A backup without portable preferences restores without resurrecting bundled or previous settings')
def portable_older_snapshot(path):
    from allma_model.utils.runtime_storage import prepare_runtime_storage
    source=Path(prepare_runtime_storage(path/'source'));seed(source);store=StateBackups(source);store.create()
    target=Path(prepare_runtime_storage(path/'target'));seed(target);preferences(target)
    stage_restore(target,store.latest());legacy=path/'legacy';seed(legacy);preferences(legacy)
    prepare_runtime_storage(target.parent,legacy)
    require(not (target/'model_binding.json').exists() and not (target/'notifications.json').exists(),'Old preferences merged into restored state')


@case('portable','legacy_settings','Moving preferences to durable storage preserves newer current choices')
def portable_legacy(path):
    from allma_model.utils.runtime_storage import prepare_runtime_storage
    legacy=path/'legacy';seed(legacy);preferences(legacy)
    target=Path(prepare_runtime_storage(path/'device',legacy))
    require((target/'notifications.json').read_bytes()==(legacy/'notifications.json').read_bytes(),'Legacy consent lost')
    changed={'version':1,'model_name':'new.gguf','reasoning':False}
    (target/'model_binding.json').write_text(json.dumps(changed))
    prepare_runtime_storage(target.parent,legacy)
    require(json.loads((target/'model_binding.json').read_text())==changed,'Newer local choice overwritten')


@case('portable','notification_clock','A clock rollback permits one delivery and then reapplies the cooldown')
def portable_clock(path):
    from unittest.mock import Mock
    from allma_model.ui.system_notifications import SystemNotifications
    seed(path);preferences(path)
    native=Mock(allowed=Mock(return_value=True),post=Mock(return_value=True))
    notices=SystemNotifications(path/'notifications.json',native,clock=lambda:100)
    require(notices.publish('message') and not notices.publish('message'),'Clock rollback disabled notifications or cooldown')


def run_battery(output,*,scope='Host runtime; synthetic preservation data',cancel_event=None,progress_callback=None):
    require(len(CASES)==28,'Unexpected preservation plan size')
    return run_challenges(output,CASES,version='preservation-v2',scope=scope,cancel_event=cancel_event,
                          progress_callback=progress_callback,harness_path=__file__)

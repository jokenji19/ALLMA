"""The production recall must retain confirmed learning beyond its RAM cache."""
import json
import sqlite3
from contextlib import closing, contextmanager
from copy import deepcopy
from unittest.mock import patch

import pytest

from allma_model.core.allma_core import ALLMACore
from allma_model.learning_system.answer_recall import AnswerRecall
from allma_model.utils.persistence import StateRecoveryRequired


QUESTION = 'Spiega il significato della luce bianca.'
ANSWER = 'La luce bianca contiene diversi colori.'


def learned_record(user='u', confirmations=None):
    return {'user': user, 'question': QUESTION, 'answer': ANSWER,
            'observations': 1, 'confirmations': confirmations or [], 'rejected': False}


def test_production_retains_confirmed_answers_beyond_500_entries(tmp_path):
    rows = {'first': learned_record(confirmations=['one', 'two'])}
    rows.update({f'candidate-{i}': learned_record() for i in range(499)})
    legacy = tmp_path / 'answer_recall.json'
    legacy.write_text(json.dumps({'version': 1, 'records': rows, 'delivery_checkpoint': 9}))
    original = legacy.read_bytes()
    core = ALLMACore(mobile_mode=True, db_path=str(tmp_path / 'core.db'))
    try:
        recall = core.answer_recall
        recall.observe('new', 'u', QUESTION, ANSWER, 'next', delivery_sequence=10)
        assert recall.lookup('first', 'u') is not None
        assert recall.lookup('first', 'other') is None
    finally:
        core.close()
    restored = ALLMACore(mobile_mode=True, db_path=str(tmp_path / 'core.db'))
    try:
        assert restored.answer_recall.lookup('first', 'u') is not None
        assert restored.answer_recall.delivery_checkpoint == 10
        assert legacy.read_bytes() == original
    finally:
        restored.close()


def store(tmp_path):
    return AnswerRecall(tmp_path/'answer_recall.db', legacy_path=tmp_path/'answer_recall.json')


def confirm(recall, key='known', user='u', sequence=1):
    recall.observe(key,user,QUESTION,ANSWER,'generated',delivery_sequence=sequence)
    recall.feedback(key,user,'one',True)
    recall.feedback(key,user,'two',True)


def test_cache_eviction_changes_only_ram_and_rejection_survives_reload(tmp_path):
    recall = store(tmp_path)
    confirm(recall)
    # Exercise eviction cheaply; the archive has no small artificial capacity.
    recall._store.CACHE_SIZE = 3
    for i in range(12):
        recall.observe(f'candidate-{i}','other',QUESTION,ANSWER,str(i))
    for i in range(12):
        assert recall.records[f'candidate-{i}']['user']=='other'
    assert len(recall._store.cache) == 3
    assert 'known' not in recall._store.cache
    assert len(recall.records) == 13
    assert recall.lookup('known','u')['confirmations'] == ['one','two']
    assert not recall.feedback('known','other','attack',False)
    assert recall.feedback('known','u','reject',False)
    assert store(tmp_path).lookup('known','u') is None
    assert store(tmp_path).records['known']['rejected'] is True


def test_changed_answer_loses_confirmation_and_duplicate_feedback_is_not_learning(tmp_path):
    recall=store(tmp_path)
    confirm(recall)
    assert recall.feedback('known','u','one',True)
    assert len(recall.records['known']['confirmations'])==2
    recall.observe('known','u',QUESTION,'Una risposta differente.','new',delivery_sequence=2)
    assert recall.lookup('known','u') is None
    assert store(tmp_path).records['known']['confirmations']==[]


def test_replay_checkpoint_is_atomic_and_comes_from_current_database(tmp_path):
    first=store(tmp_path)
    second=store(tmp_path)
    confirm(first,sequence=8)
    second.observe('known','u',QUESTION,ANSWER,'replayed',delivery_sequence=8)
    assert second.delivery_checkpoint==8
    assert second.records['known']['observations']==1
    assert second.lookup('known','u') is not None
    first.feedback('known','u','reject',False)
    assert second.lookup('known','u') is None  # An old hot cache cannot defeat revocation.


@pytest.mark.parametrize('sequence',[-1,True,2**53,'8'])
def test_invalid_delivery_sequence_does_not_commit_record_or_checkpoint(tmp_path,sequence):
    recall=store(tmp_path)
    with pytest.raises(ValueError):
        recall.observe('invalid','u',QUESTION,ANSWER,'e',delivery_sequence=sequence)
    assert len(recall.records)==0
    assert store(tmp_path).delivery_checkpoint==0


def test_failed_save_cannot_publish_a_confirmation_or_advance_checkpoint(tmp_path):
    recall=store(tmp_path)
    recall.observe('known','u',QUESTION,ANSWER,'e',delivery_sequence=7)
    recall.feedback('known','u','one',True)
    before=deepcopy(recall.records)
    with patch.object(recall,'_save',side_effect=OSError('synthetic disk full')):
        with pytest.raises(OSError):recall.feedback('known','u','two',True)
        with pytest.raises(OSError):recall.observe('new','u',QUESTION,ANSWER,'new',delivery_sequence=8)
    assert recall.records==before
    assert store(tmp_path).delivery_checkpoint==7
    assert store(tmp_path).lookup('known','u') is None


def test_transaction_commit_failure_rolls_back_record_and_checkpoint(tmp_path):
    recall=store(tmp_path)
    confirm(recall,sequence=7)
    class Failure(sqlite3.Connection):
        def commit(self):
            raise OSError('synthetic commit failure')
    @contextmanager
    def failing_connect(readonly=False):
        with closing(sqlite3.connect(recall.path,factory=Failure)) as db:
            yield db
    with patch.object(recall._store,'connect',side_effect=failing_connect):
        with pytest.raises(OSError):
            recall.observe('known','u',QUESTION,'Nuova risposta.','new',delivery_sequence=8)
    assert recall.delivery_checkpoint==7
    restored=store(tmp_path)
    assert restored.delivery_checkpoint==7 and restored.lookup('known','u')['answer']==ANSWER


def test_failed_migration_keeps_original_bytes_and_retries_safely(tmp_path):
    legacy=tmp_path/'answer_recall.json'
    legacy.write_text(json.dumps({'version':1,'records':{'known':learned_record(confirmations=['one','two'])},'delivery_checkpoint':7}))
    original=legacy.read_bytes()
    with patch('allma_model.learning_system.recall_store.os.replace',side_effect=OSError('synthetic publication failure')):
        failed=store(tmp_path)
    assert failed.load_error is not None and not failed.path.exists()
    assert legacy.read_bytes()==original
    assert failed.lookup('known','u') is None
    restored=store(tmp_path)
    assert restored.load_error is None and restored.lookup('known','u') is not None
    assert restored.delivery_checkpoint==7 and legacy.read_bytes()==original
    assert not list(tmp_path.glob('answer_recall.db.migration-*'))


@pytest.mark.parametrize('kind',['broken','future','partial','checkpoint'])
def test_invalid_legacy_archive_cannot_publish_a_partial_migration(tmp_path,kind):
    data={'version':1,'records':{'known':learned_record(confirmations=['one','two'])},'delivery_checkpoint':7}
    if kind=='future':data['version']=2
    if kind=='partial':data['records']['broken']={}
    if kind=='checkpoint':data['delivery_checkpoint']=True
    raw='{broken' if kind=='broken' else json.dumps(data)
    legacy=tmp_path/'answer_recall.json';legacy.write_text(raw)
    recall=store(tmp_path)
    assert recall.load_error is not None and not recall.path.exists()
    assert legacy.read_text()==raw and recall.lookup('known','u') is None
    with pytest.raises(StateRecoveryRequired):
        recall.observe('new','u',QUESTION,ANSWER,'e')


def test_damaged_new_archive_never_falls_back_to_outdated_legacy(tmp_path):
    legacy=tmp_path/'answer_recall.json'
    legacy.write_text(json.dumps({'version':1,'records':{'known':learned_record(confirmations=['one','two'])}}))
    recall=store(tmp_path)
    recall.feedback('known','u','reject',False)
    recall.path.write_bytes(b'{damaged')
    restored=store(tmp_path)
    assert restored.load_error is not None
    assert restored.lookup('known','u') is None
    assert recall.path.read_bytes()==b'{damaged'


def test_missing_loaded_database_is_not_silently_recreated(tmp_path):
    recall=store(tmp_path)
    confirm(recall)
    recall.path.unlink()
    assert recall.load_state() is False
    with pytest.raises(StateRecoveryRequired):recall._save()
    assert not recall.path.exists()


def test_lookup_detects_live_corruption_without_breaking_ordinary_chat_path(tmp_path):
    recall=store(tmp_path);confirm(recall)
    recall.path.write_bytes(b'{damaged while running')
    assert recall.lookup('known','u') is None
    assert recall.load_error is not None
    with pytest.raises(StateRecoveryRequired):
        recall.observe('new','u',QUESTION,ANSWER,'e')
    assert recall.path.read_bytes()==b'{damaged while running'


def test_another_user_cannot_replace_an_existing_key(tmp_path):
    recall=store(tmp_path)
    confirm(recall)
    with pytest.raises(ValueError,match='another user'):
        recall.observe('known','other',QUESTION,ANSWER,'attack')
    assert recall.lookup('known','u') is not None


def test_snapshot_includes_durable_learning_and_restores_revocations(tmp_path):
    from allma_model.utils.state_backup import StateBackups,verify_archive
    root=tmp_path/'allma_state';root.mkdir()
    recall=store(root);confirm(recall)
    recall.feedback('known','u','reject',False)
    backups=StateBackups(root)
    result=backups.create()
    destination=tmp_path/'restored';destination.mkdir()
    manifest=verify_archive(backups.directory/result['id'],destination)
    assert 'answer_recall.db' in manifest['files']
    restored=store(destination)
    assert restored.lookup('known','u') is None
    assert restored.records['known']['rejected'] is True
    assert restored.delivery_checkpoint==1


@pytest.mark.parametrize('damage',['schema_version','invalid_record','invalid_checkpoint'])
def test_invalid_database_is_preserved_and_excluded_from_backup(tmp_path,damage):
    from allma_model.utils.state_backup import StateBackups,BackupError
    recall=store(tmp_path);confirm(recall)
    with sqlite3.connect(recall.path) as db:
        if damage=='schema_version':db.execute('PRAGMA user_version=99')
        if damage=='invalid_record':db.execute("UPDATE answers SET record='{}'")
        if damage=='invalid_checkpoint':db.execute("UPDATE recall_meta SET value=-1 WHERE key='delivery_checkpoint'")
    original=recall.path.read_bytes()
    failed=store(tmp_path)
    assert failed.load_error is not None and failed.lookup('known','u') is None
    assert failed.path.read_bytes()==original
    with pytest.raises(BackupError):StateBackups(tmp_path).create()


def test_each_observation_updates_only_its_row_not_the_whole_archive(tmp_path):
    recall=store(tmp_path)
    for i in range(20):recall.observe(str(i),'u',QUESTION,ANSWER,str(i))
    statements=[]
    original=recall._store.connect
    @contextmanager
    def traced(readonly=False):
        with original(readonly) as db:
            db.set_trace_callback(statements.append)
            yield db
    with patch.object(recall._store,'connect',side_effect=traced):
        recall.observe('21','u',QUESTION,ANSWER,'next',delivery_sequence=21)
    reads=[s for s in statements if s.startswith('SELECT record FROM answers')]
    writes=[s for s in statements if s.startswith('INSERT INTO answers')]
    assert len(reads)==len(writes)==1
    assert all('WHERE key=' in s for s in reads)
    assert len(recall.records)==21


def test_fixed_android_storage_challenges_pass(tmp_path):
    from allma_model.learning_system.recall_diagnostics import run_battery
    from reliability_android import AndroidRecallStorageRun
    summary=run_battery(tmp_path/'reports')
    assert summary['complete'] and summary['passed']==summary['planned']==8,summary['failures']
    assert AndroidRecallStorageRun.battery_module=='allma_model.learning_system.recall_diagnostics'


def test_android_hard_link_denial_cannot_prevent_migration(tmp_path):
    legacy=tmp_path/'answer_recall.json'
    legacy.write_text(json.dumps({'version':1,'records':{'known':learned_record(confirmations=['one','two'])}}))
    with patch('os.link',side_effect=PermissionError(13,'synthetic Android restriction')) as link:
        recall=store(tmp_path)
    assert recall.load_error is None and recall.lookup('known','u') is not None
    link.assert_not_called()


def test_concurrent_openers_publish_one_migration_without_replacing_live_updates(tmp_path):
    from concurrent.futures import ThreadPoolExecutor
    legacy=tmp_path/'answer_recall.json'
    legacy.write_text(json.dumps({'version':1,'records':{'known':learned_record(confirmations=['one','two'])}}))
    with ThreadPoolExecutor(max_workers=4) as workers:
        stores=list(workers.map(lambda _:store(tmp_path),range(4)))
    assert all(s.load_error is None and s.lookup('known','u') is not None for s in stores)
    for i,s in enumerate(stores):s.observe(str(i),'u',QUESTION,ANSWER,'e',delivery_sequence=i+1)
    assert len(store(tmp_path).records)==5 and store(tmp_path).delivery_checkpoint==4


@pytest.mark.parametrize('after_publication',[False,True])
def test_process_death_releases_migration_lock_and_keeps_original(tmp_path,after_publication):
    import os
    from pathlib import Path
    import subprocess
    import sys
    legacy=tmp_path/'answer_recall.json'
    legacy.write_text(json.dumps({'version':1,'records':{'known':learned_record(confirmations=['one','two'])},'delivery_checkpoint':7}))
    original=legacy.read_bytes()
    script='''
import os,sys
from pathlib import Path
from unittest.mock import patch
from allma_model.learning_system.answer_recall import AnswerRecall
root=Path(sys.argv[1]);after=sys.argv[2]=='True'
replace=os.replace
def interrupt(source,destination):
    if after:replace(source,destination)
    os._exit(73)
with patch('allma_model.learning_system.recall_store.os.replace',side_effect=interrupt):
    AnswerRecall(root/'answer_recall.db',legacy_path=root/'answer_recall.json')
'''
    env=dict(os.environ,PYTHONPATH=str(Path(__file__).resolve().parents[2]))
    result=subprocess.run([sys.executable,'-c',script,str(tmp_path),str(after_publication)],env=env,
                          capture_output=True,text=True,timeout=30)
    assert result.returncode==73,result.stderr
    restored=store(tmp_path)
    assert restored.load_error is None and restored.lookup('known','u') is not None
    assert restored.delivery_checkpoint==7 and legacy.read_bytes()==original

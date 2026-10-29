"""Canonical learning deltas, immutable migration and recoverable failures."""
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
import json
import sqlite3

import pytest

from allma_model.learning_system.incremental_learning import IncrementalLearner,LearningUnit,ConfidenceLevel,FeedbackType
from allma_model.learning_system.learning_store import LearningStore
from allma_model.utils.persistence import StateRecoveryRequired

NOW=datetime(2026,10,24,12)


def unit(topic='navigation',content='The compass points north'):
    return LearningUnit(topic,content,'user_u',ConfidenceLevel.LOW,NOW,{'user_id':'u'})


def create(path):
    learner=IncrementalLearner(str(path))
    assert learner.load_error is None
    return learner


def interaction(topic='navigation'):
    return {'input':'A synthetic user report','response':'Not verified knowledge','topic':topic,'feedback':'neutral'}


def test_complete_legacy_migration_keeps_all_state_and_original_bytes(tmp_path):
    legacy=create(tmp_path/'learning.json');legacy.learn_from_interaction(interaction(),'u',delivery_sequence=7)
    legacy.integrate_feedback('navigation',FeedbackType.NEGATIVE,'More examples',{'detail':[1]})
    legacy.record_success('navigation');legacy.add_response_variants('navigation',['A variant'])
    original=Path(legacy.storage_path).read_bytes();canonical=create(tmp_path/'learning.db')
    assert canonical._snapshot()==legacy._snapshot()
    canonical.learn_from_interaction(interaction('new'),'u',delivery_sequence=8)
    assert Path(legacy.storage_path).read_bytes()==original
    assert create(tmp_path/'learning.db')._snapshot()==canonical._snapshot()


def test_schema_one_migration_recovers_legacy_units_and_preserves_source(tmp_path):
    source=tmp_path/'learning.json';data={'knowledge_states':{'sea':{'topic':'sea','content':'Blue','confidence':2,
        'last_updated':NOW.isoformat(),'sources':['legacy']}}}
    original=json.dumps(data);source.write_text(original)
    learner=create(tmp_path/'learning.db')
    assert learner.knowledge_base['sea'][0].content=='Blue'
    assert source.read_text()==original


def test_api_never_rewrites_other_topics_or_creates_a_json_mirror(tmp_path):
    learner=create(tmp_path/'learning.db');learner.add_learning_unit(unit('old'))
    with learner._store.connect(readonly=True) as db:
        before=db.execute("SELECT kind,key,position,data FROM learning_lists WHERE key='old'").fetchall()
    with patch('allma_model.learning_system.incremental_learning.atomic_write_json',side_effect=AssertionError('JSON mirror')):
        learner.add_learning_unit(unit('new'))
    with learner._store.connect(readonly=True) as db:
        assert db.execute("SELECT kind,key,position,data FROM learning_lists WHERE key='old'").fetchall()==before
    assert not (tmp_path/'learning.json').exists()


def test_append_serialization_is_bounded_with_a_large_same_topic_history(tmp_path):
    import allma_model.learning_system.learning_store as module
    learner=create(tmp_path/'learning.db');learner.add_learning_unit(unit(content='header'))
    learner.knowledge_base['navigation']=[unit(content='old payload '*100) for _ in range(1000)];learner.save_state()
    original=module._dump;encoded=[]
    def dump(value):
        text=original(value);encoded.append(len(text.encode()));return text
    with patch.object(module,'_dump',side_effect=dump):learner.add_learning_unit(unit(content='new'))
    assert sum(encoded)<4096
    assert len(create(tmp_path/'learning.db').knowledge_base['navigation'])==1001


def test_feedback_and_user_progress_append_tails_without_reencoding_prefixes(tmp_path):
    import allma_model.learning_system.learning_store as module
    learner=create(tmp_path/'learning.db');learner.learn_from_interaction(interaction(),'u')
    learner.knowledge_states['navigation'].feedback_history=[('old '*100,NOW) for _ in range(1000)]
    learner.user_progress['u']['recent_learning']=[{'topic':'old','timestamp':NOW.isoformat(),'confidence':1,'detail':'old '*100} for _ in range(1000)]
    learner.save_state();original=module._dump;encoded=[]
    def dump(value):
        text=original(value);encoded.append(len(text.encode()));return text
    with patch.object(module,'_dump',side_effect=dump):learner.learn_from_interaction(interaction(),'u')
    assert sum(encoded)<8192
    restored=create(tmp_path/'learning.db')
    assert len(restored.knowledge_states['navigation'].feedback_history)==1001
    assert len(restored.user_progress['u']['recent_learning'])==1001


@pytest.mark.parametrize('operation',['add','learn','feedback','success','variants'])
def test_failure_after_row_writes_rolls_back_disk_ram_and_checkpoint(tmp_path,operation):
    learner=create(tmp_path/'learning.db');learner.add_learning_unit(unit());before=deepcopy(learner._snapshot())
    connect=sqlite3.connect
    class Failure(sqlite3.Connection):
        def execute(self,sql,*args,**kwargs):
            if "SET value=value+1" in sql:raise OSError('Synthetic commit interruption')
            return super().execute(sql,*args,**kwargs)
    with patch('allma_model.learning_system.learning_store.sqlite3.connect',side_effect=lambda *a,**k:connect(*a,**dict(k,factory=Failure))):
        with pytest.raises(OSError):
            if operation=='add':learner.add_learning_unit(unit('failed'))
            if operation=='learn':learner.learn_from_interaction(interaction(),'u',delivery_sequence=9)
            if operation=='feedback':learner.integrate_feedback('navigation',FeedbackType.POSITIVE,'Useful')
            if operation=='success':learner.record_success('navigation')
            if operation=='variants':learner.add_response_variants('navigation',['variant'])
    assert learner._snapshot()==before
    assert create(tmp_path/'learning.db')._snapshot()==before
    learner.add_learning_unit(unit('retry'))
    assert 'retry' in create(tmp_path/'learning.db').knowledge_base


def test_replayed_delivery_is_exactly_once_after_restart(tmp_path):
    path=tmp_path/'learning.db';learner=create(path)
    learner.learn_from_interaction(interaction(),'u',delivery_sequence=8)
    restored=create(path);before=restored._snapshot()
    assert restored.learn_from_interaction(interaction(),'u',delivery_sequence=8) is None
    assert restored._snapshot()==before and create(path)._snapshot()==before


def test_stale_writer_cannot_erase_other_updates_and_can_reload(tmp_path):
    path=tmp_path/'learning.db';one=create(path);two=create(path)
    one.add_learning_unit(unit('first'))
    with pytest.raises(StateRecoveryRequired):two.add_learning_unit(unit('stale'))
    assert not two.knowledge_base
    with pytest.raises(StateRecoveryRequired):two.flush_state()
    assert two.load_state();two.add_learning_unit(unit('second'))
    assert set(create(path).knowledge_base)=={'first','second'}


@pytest.mark.parametrize('mutation',['future','orphan','gap','bad_date','bad_counter'])
def test_invalid_database_never_publishes_a_partial_state_or_overwrites_sources(tmp_path,mutation):
    path=tmp_path/'learning.db';learner=create(path);learner.add_learning_unit(unit())
    with sqlite3.connect(path) as db:
        if mutation=='future':db.execute('PRAGMA user_version=9000')
        if mutation=='orphan':db.execute("INSERT INTO learning_sets VALUES('sources','missing','source')")
        if mutation=='gap':db.execute("UPDATE learning_lists SET position=4")
        if mutation=='bad_date':
            row=json.loads(db.execute("SELECT data FROM learning_maps WHERE kind='state'").fetchone()[0]);row['last_updated']='bad'
            db.execute("UPDATE learning_maps SET data=? WHERE kind='state'",(json.dumps(row),))
        if mutation=='bad_counter':db.execute("INSERT INTO learning_maps VALUES('counter','bad','true')")
    original=path.read_bytes();restored=IncrementalLearner(str(path))
    assert restored.load_error is not None and not restored.knowledge_base
    with pytest.raises(StateRecoveryRequired):restored.add_learning_unit(unit('ghost'))
    assert path.read_bytes()==original
    with pytest.raises((ValueError,sqlite3.Error)):LearningStore.validate_database(path)


def test_missing_migrated_database_cannot_resurrect_older_json(tmp_path):
    old=create(tmp_path/'learning.json');old.add_learning_unit(unit('old'))
    path=tmp_path/'learning.db';current=create(path);current.add_learning_unit(unit('new'));path.unlink()
    restored=IncrementalLearner(str(path))
    assert restored.load_error is not None and not path.exists()
    with pytest.raises(StateRecoveryRequired):restored.save_state()


def test_failed_migration_never_publishes_a_database_or_changes_legacy_bytes(tmp_path):
    path=tmp_path/'learning.json';path.write_text('{broken');original=path.read_bytes()
    learner=IncrementalLearner(str(tmp_path/'learning.db'))
    assert learner.load_error is not None and not (tmp_path/'learning.db').exists()
    assert path.read_bytes()==original


def test_two_initializers_publish_one_valid_archive(tmp_path):
    old=create(tmp_path/'learning.json');old.add_learning_unit(unit())
    path=tmp_path/'learning.db'
    with ThreadPoolExecutor(max_workers=2) as pool:learners=list(pool.map(lambda _:create(path),range(2)))
    assert learners[0]._snapshot()==learners[1]._snapshot()
    assert len(create(path).knowledge_base['navigation'])==1


def test_manual_save_can_replace_and_remove_records_without_changing_legacy(tmp_path):
    learner=create(tmp_path/'learning.db');learner.add_learning_unit(unit());learner.add_learning_unit(unit('other'))
    del learner.knowledge_base['other'];del learner.knowledge_states['other']
    learner.knowledge_states['navigation'].metadata['manual']=True;learner.save_state()
    restored=create(tmp_path/'learning.db')
    assert set(restored.knowledge_base)=={'navigation'} and restored.knowledge_states['navigation'].metadata['manual']


def backup_root(path):
    from allma_model.utils.runtime_storage import prepare_runtime_storage
    root=Path(prepare_runtime_storage(path))
    with sqlite3.connect(root/'allma.db') as db:db.execute('CREATE TABLE facts(value TEXT)')
    return root


def test_new_backup_restores_current_learning_and_omits_stale_json(tmp_path):
    from allma_model.utils.state_backup import StateBackups,verify_archive
    from allma_model.utils.state_restore import stage_restore,apply_pending_restore
    root=backup_root(tmp_path/'source');folder=root/'incremental_cache';folder.mkdir()
    old=create(folder/'knowledge_states.json');old.add_learning_unit(unit('old'));legacy=(folder/'knowledge_states.json').read_bytes()
    learner=create(folder/'knowledge_states.db');learner.learn_from_interaction(interaction('current'),'u',delivery_sequence=9)
    store=StateBackups(root);store.create();manifest=verify_archive(store.latest())
    assert 'incremental_cache/knowledge_states.db' in manifest['files']
    assert 'incremental_cache/knowledge_states.json' not in manifest['files']
    target=backup_root(tmp_path/'target');stage_restore(target,store.latest());apply_pending_restore(target.parent)
    restored=create(target/'incremental_cache/knowledge_states.db')
    assert restored._snapshot()==learner._snapshot()
    assert (folder/'knowledge_states.json').read_bytes()==legacy


def test_old_backup_migrates_without_relearning_or_losing_checkpoints(tmp_path):
    from allma_model.utils.state_backup import StateBackups
    from allma_model.utils.state_restore import stage_restore,apply_pending_restore
    root=backup_root(tmp_path/'source');folder=root/'incremental_cache';folder.mkdir()
    learner=create(folder/'knowledge_states.json');learner.learn_from_interaction(interaction(),'u',delivery_sequence=5)
    store=StateBackups(root);store.create()
    target=backup_root(tmp_path/'target');stage_restore(target,store.latest());apply_pending_restore(target.parent)
    restored=create(target/'incremental_cache/knowledge_states.db')
    assert restored.delivery_checkpoint==5
    assert restored.learn_from_interaction(interaction(),'u',delivery_sequence=5) is None
    assert restored._snapshot()==learner._snapshot()


def test_backup_cannot_certify_stale_json_when_migrated_database_is_missing(tmp_path):
    from allma_model.utils.state_backup import StateBackups,BackupError
    root=backup_root(tmp_path);folder=root/'incremental_cache';folder.mkdir()
    old=create(folder/'knowledge_states.json');old.add_learning_unit(unit())
    current=create(folder/'knowledge_states.db');store=StateBackups(root);store.create()
    original=store.latest().read_bytes();Path(current.storage_path).unlink()
    with pytest.raises(BackupError):store.create()
    assert store.latest().read_bytes()==original


def test_backup_includes_committed_learning_rows_in_wal(tmp_path):
    from allma_model.utils.state_backup import StateBackups,verify_archive
    root=backup_root(tmp_path);path=root/'incremental_cache/knowledge_states.db';learner=create(path);learner.add_learning_unit(unit())
    with sqlite3.connect(path) as writer:
        assert writer.execute('PRAGMA journal_mode=WAL').fetchone()==('wal',)
        row=learner._snapshot()['knowledge_base']['navigation'][0];row['content']='WAL report'
        writer.execute('INSERT INTO learning_lists VALUES(?,?,?,?)',('unit','navigation',1,json.dumps(row)))
        writer.execute("UPDATE learning_meta SET value=value+1 WHERE key='generation'");writer.commit()
        store=StateBackups(root);store.create();target=tmp_path/'extract';target.mkdir();verify_archive(store.latest(),target)
        restored=create(target/'incremental_cache/knowledge_states.db')
        assert restored.knowledge_base['navigation'][-1].content=='WAL report'


from allma_model.learning_system.learning_diagnostics import CASES,run_battery


@pytest.mark.parametrize('challenge',CASES,ids=[row[1] for row in CASES])
def test_learning_native_challenge(tmp_path,challenge):
    challenge[3](tmp_path)


def test_complete_learning_runner_uses_isolated_case_directories(tmp_path):
    summary=run_battery(tmp_path/'reports')
    assert summary['complete'] and summary['passed']==summary['total']==18
    assert not summary['failures']

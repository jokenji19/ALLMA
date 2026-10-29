"""Fixed synthetic migration/delta/recovery challenges for the native runtime."""
from datetime import datetime
from pathlib import Path
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
import json
import sqlite3

from memory_recovery_battery import require,run_challenges
from .incremental_learning import IncrementalLearner,LearningUnit,KnowledgeState,ConfidenceLevel,FeedbackType
from .learning_store import LearningStore
from allma_model.utils.persistence import StateRecoveryRequired
from allma_model.utils.state_backup import StateBackups,BackupError,verify_archive
from allma_model.utils.runtime_storage import prepare_runtime_storage
from allma_model.utils.state_restore import stage_restore,apply_pending_restore

CASES=[]
NOW=datetime(2026,10,24,12)


def case(group,name,criterion):
    def register(fn):CASES.append((group,name,criterion,fn));return fn
    return register


def create(path):
    learner=IncrementalLearner(str(path));require(learner.load_error is None,'Learning unavailable');return learner


def unit(topic='navigation',content='Synthetic report'):
    return LearningUnit(topic,content,'user_u',ConfidenceLevel.LOW,NOW,{'user_id':'u'})


def interaction(topic='navigation'):
    return {'input':'A synthetic report','response':'Unverified generation','topic':topic,'feedback':'neutral'}


@case('migration','legacy_v2','All legacy knowledge, feedback, variants, progress and checkpoint migrate without modifying the source JSON')
def legacy_v2(path):
    old=create(path/'learning.json');old.learn_from_interaction(interaction(),'u',delivery_sequence=7)
    old.integrate_feedback('navigation',FeedbackType.NEGATIVE,'More examples');old.record_success('navigation')
    old.add_response_variants('navigation',['variant']);original=(path/'learning.json').read_bytes()
    current=create(path/'learning.db');require(current._snapshot()==old._snapshot(),'Migration lost learning fields')
    current.add_learning_unit(unit('new'));require((path/'learning.json').read_bytes()==original,'Legacy source rewritten')


@case('migration','legacy_v1','Schema-one states recover the same legacy unit and confidence')
def legacy_v1(path):
    data={'knowledge_states':{'sea':{'topic':'sea','content':'Blue','confidence':2,'last_updated':NOW.isoformat(),'sources':['legacy']}}}
    (path/'learning.json').write_text(json.dumps(data));learner=create(path/'learning.db')
    require(learner.knowledge_base['sea'][0].content=='Blue' and learner.knowledge_states['sea'].confidence==ConfidenceLevel.MEDIUM,'Legacy meaning changed')


@case('migration','invalid_legacy','Invalid legacy bytes cannot publish a partial database')
def invalid_legacy(path):
    source=path/'learning.json';source.write_text('{broken');learner=IncrementalLearner(str(path/'learning.db'))
    require(learner.load_error is not None and not (path/'learning.db').exists(),'Invalid migration published')
    require(source.read_text()=='{broken','Invalid source overwritten')


@case('delta','same_topic','One new unit serializes only its tail even with 1000 previous units in the same topic')
def same_topic(path):
    from . import learning_store as module
    learner=create(path/'learning.db');learner.add_learning_unit(unit(content='Short header'))
    learner.knowledge_base['navigation']=[unit(content='Old payload '*100) for _ in range(1000)];learner.save_state()
    original=module._dump;encoded=[]
    def dump(value):
        text=original(value);encoded.append(len(text.encode()));return text
    with patch.object(module,'_dump',side_effect=dump):learner.add_learning_unit(unit(content='new'))
    require(sum(encoded)<4096,'Historical units reencoded')
    require(len(create(path/'learning.db').knowledge_base['navigation'])==1001,'Unit tail lost')


@case('delta','feedback_progress','New feedback and recent progress append without serializing their historical prefixes')
def feedback_progress(path):
    from . import learning_store as module
    learner=create(path/'learning.db');learner.learn_from_interaction(interaction(),'u')
    learner.knowledge_states['navigation'].feedback_history=[('old '*50,NOW) for _ in range(200)]
    learner.user_progress['u']['recent_learning']=[{'topic':'old','timestamp':NOW.isoformat(),'confidence':1,'detail':'old '*50} for _ in range(200)]
    learner.save_state();original=module._dump;encoded=[]
    def dump(value):
        text=original(value);encoded.append(len(text.encode()));return text
    with patch.object(module,'_dump',side_effect=dump):learner.learn_from_interaction(interaction(),'u')
    require(sum(encoded)<8192,'Historical feedback/progress reencoded')
    restored=create(path/'learning.db')
    require(len(restored.knowledge_states['navigation'].feedback_history)==201 and len(restored.user_progress['u']['recent_learning'])==201,'Historical list changed')


for operation in ('add','learn','feedback','success','variants'):
    def run(path,operation=operation):
        learner=create(path/'learning.db');learner.add_learning_unit(unit());before=deepcopy(learner._snapshot());connect=sqlite3.connect
        class Failure(sqlite3.Connection):
            def execute(self,sql,*args,**kwargs):
                if 'SET value=value+1' in sql:raise OSError('Synthetic commit interruption')
                return super().execute(sql,*args,**kwargs)
        with patch('allma_model.learning_system.learning_store.sqlite3.connect',side_effect=lambda *a,**k:connect(*a,**dict(k,factory=Failure))):
            try:
                if operation=='add':learner.add_learning_unit(unit('failed'))
                elif operation=='learn':learner.learn_from_interaction(interaction(),'u',delivery_sequence=9)
                elif operation=='feedback':learner.integrate_feedback('navigation',FeedbackType.POSITIVE,'Useful')
                elif operation=='success':learner.record_success('navigation')
                else:learner.add_response_variants('navigation',['variant'])
            except OSError:pass
            else:raise AssertionError('Injected commit failure ignored')
        require(learner._snapshot()==before and create(path/'learning.db')._snapshot()==before,'Partial mutation leaked')
        learner.add_learning_unit(unit('retry'));require('retry' in create(path/'learning.db').knowledge_base,'Retry failed')
    case('rollback','failed_'+operation,'A failure after data writes rolls back RAM, rows and replay checkpoint')(run)


@case('recovery','delivery_replay','Restart and replay cannot learn a delivered event twice')
def delivery_replay(path):
    learner=create(path/'learning.db');learner.learn_from_interaction(interaction(),'u',delivery_sequence=8)
    restored=create(path/'learning.db');before=restored._snapshot()
    require(restored.learn_from_interaction(interaction(),'u',delivery_sequence=8) is None,'Replay was learned twice')
    require(create(path/'learning.db')._snapshot()==before,'Replay changed committed state')


@case('recovery','stale_writer','A stale learning instance cannot overwrite another writer and recovers after reload')
def stale_writer(path):
    one=create(path/'learning.db');two=create(path/'learning.db');one.add_learning_unit(unit('first'))
    try:two.add_learning_unit(unit('stale'))
    except StateRecoveryRequired:pass
    else:raise AssertionError('Stale writer accepted')
    require(not two.knowledge_base and two.load_state(),'Stale writer did not recover')
    two.add_learning_unit(unit('second'));require(set(create(path/'learning.db').knowledge_base)=={'first','second'},'Concurrent update lost')


@case('recovery','missing_database','A missing migrated database cannot resurrect the read-only older JSON or become a verified backup')
def missing_database(path):
    root=root_at(path/'device');folder=root/'incremental_cache';folder.mkdir()
    old=create(folder/'knowledge_states.json');old.add_learning_unit(unit('old'))
    learner=create(folder/'knowledge_states.db');learner.add_learning_unit(unit('new'))
    store=StateBackups(root);store.create();original=store.latest().read_bytes()
    Path(learner.storage_path).unlink();restored=IncrementalLearner(learner.storage_path)
    require(restored.load_error is not None and not Path(learner.storage_path).exists(),'Old JSON resurrected')
    try:store.create()
    except BackupError:pass
    else:raise AssertionError('Stale legacy JSON certified after database loss')
    require(store.latest().read_bytes()==original,'Last verified backup lost')


@case('recovery','initialization_race','Two initializers publish one complete migrated archive without duplicates')
def initialization_race(path):
    old=create(path/'learning.json');old.add_learning_unit(unit())
    with ThreadPoolExecutor(max_workers=2) as pool:values=list(pool.map(lambda _:create(path/'learning.db'),range(2)))
    require(values[0]._snapshot()==values[1]._snapshot() and len(values[0].knowledge_base['navigation'])==1,'Migration race lost or duplicated data')


@case('recovery','invalid_database','Malformed logical records block loading, backup validation and further mutation')
def invalid_database(path):
    learner=create(path/'learning.db');learner.add_learning_unit(unit())
    with sqlite3.connect(path/'learning.db') as db:db.execute("INSERT INTO learning_sets VALUES('sources','orphan','source')")
    bad=IncrementalLearner(str(path/'learning.db'));require(bad.load_error is not None and not bad.knowledge_base,'Partial invalid state loaded')
    try:LearningStore.validate_database(path/'learning.db')
    except ValueError:pass
    else:raise AssertionError('Invalid archive certified')


def root_at(path):
    root=Path(prepare_runtime_storage(path))
    with sqlite3.connect(root/'allma.db') as db:db.execute('CREATE TABLE facts(value TEXT)')
    return root


@case('backup','portable_restore','Encrypted export and a separate installation preserve current learning and omit stale legacy JSON')
def portable_restore(path):
    root=root_at(path/'source');folder=root/'incremental_cache';folder.mkdir()
    old=create(folder/'knowledge_states.json');old.add_learning_unit(unit('old'))
    learner=create(folder/'knowledge_states.db');learner.learn_from_interaction(interaction(),'u',delivery_sequence=8)
    store=StateBackups(root);store.create();manifest=verify_archive(store.latest())
    require('incremental_cache/knowledge_states.db' in manifest['files'] and 'incremental_cache/knowledge_states.json' not in manifest['files'],'Backup contains stale learning projection')
    encrypted=path/'portable.allma';store.export(encrypted,'Synthetic-learning-copy-2026!')
    target=root_at(path/'target');StateBackups(target).stage_encrypted_restore(encrypted,'Synthetic-learning-copy-2026!');apply_pending_restore(target.parent)
    require(create(target/'incremental_cache/knowledge_states.db')._snapshot()==learner._snapshot(),'Portable learning changed')


@case('backup','legacy_restore','An older JSON-only backup migrates and preserves its delivery checkpoint')
def legacy_restore(path):
    root=root_at(path/'source');folder=root/'incremental_cache';folder.mkdir()
    old=create(folder/'knowledge_states.json');old.learn_from_interaction(interaction(),'u',delivery_sequence=6)
    store=StateBackups(root);store.create();target=root_at(path/'target');stage_restore(target,store.latest());apply_pending_restore(target.parent)
    require(create(target/'incremental_cache/knowledge_states.db')._snapshot()==old._snapshot(),'Old backup lost learning or checkpoint')


@case('manual','explicit_save','Explicit manual save can remove a topic while ordinary APIs retain JSON compatibility')
def explicit_save(path):
    learner=create(path/'learning.db');learner.add_learning_unit(unit());learner.add_learning_unit(unit('remove'))
    del learner.knowledge_base['remove'];del learner.knowledge_states['remove'];learner.save_state()
    require(set(create(path/'learning.db').knowledge_base)=={'navigation'},'Explicit removal lost')
    legacy=create(path/'compatibility.json');legacy.add_learning_unit(unit())
    require(bool(create(path/'compatibility.json').knowledge_base),'JSON compatibility lost')


def run_battery(output,*,scope=None,cancel_event=None,progress_callback=None):
    require(len(CASES)==18,'Unexpected incremental learning plan')
    return run_challenges(output,CASES,version='learning-store-v1',scope=scope,cancel_event=cancel_event,
        progress_callback=progress_callback,harness_path=__file__)

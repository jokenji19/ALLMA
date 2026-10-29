"""Fixed synthetic idle-work challenges; no live history or GGUF inference."""
from datetime import datetime,timedelta
from pathlib import Path
from threading import Event,Thread
from unittest.mock import patch
import sqlite3

from memory_recovery_battery import require,run_challenges
from allma_model.core.autobiographical_identity import POLICY_VERSION
from allma_model.memory_system.activity_snapshot import activity_snapshot,MAX_USERS
from allma_model.memory_system.conversational_memory import ConversationalMemory,Message
from allma_model.learning_system.incremental_learning import IncrementalLearner,LearningUnit,ConfidenceLevel
from allma_model.utils.persistence import StateRecoveryRequired

NOW=datetime(2026,10,24,12)
CASES=[]


def case(group,name,criterion):
    def register(fn):CASES.append((group,name,criterion,fn));return fn
    return register


def history(path,count=8):
    memory=ConversationalMemory(storage_dir=str(path),incremental=True);memory.vector_engine=None
    memory.messages.extend(Message('c','user','Synthetic '+str(i),NOW-timedelta(hours=8)+timedelta(seconds=i),{},'u') for i in range(count))
    memory.save_memory();return memory


def view(memory,user='u',now=NOW):return activity_snapshot(memory,user,now,POLICY_VERSION,21600)


def outbox(memory,identifier,age):
    memory.messages.append(Message('c','assistant','Saved synthetic initiative',NOW-age,
        {'source':'proactive','is_valid':True,'identity_policy':POLICY_VERSION,'request_id':'PROACTIVE:'+identifier*32,
         'proactive_delivery':{'version':1,'state':'pending'}},'u'))
    memory.save_memory();return memory.messages[-1]


@case('initiative','cached_scan','Unchanged idle ticks decode no further history rows after one complete scan')
def cached_scan(path):
    memory=history(path,800)
    with patch.object(memory._history_store,'_decode_page',wraps=memory._history_store._decode_page) as decode:
        initial=view(memory);require(decode.call_count==800,'Initial history not scanned exactly once')
        require(view(memory) is initial and view(memory,now=NOW+timedelta(minutes=1)) is initial,'Idle view not reused')
        require(decode.call_count==800,'Unchanged idle tick reread old pages')


@case('initiative','changed_source','A corrected source and a reload both invalidate the disposable view')
def changed_source(path):
    memory=history(path);initial=view(memory)
    memory.messages[-1].content='Corrected synthetic report';memory.save_memory()
    changed=view(memory);require(changed is not initial and changed.last_user.content=='Corrected synthetic report','Correction ignored')
    require(memory.load_memory(),'Reload failed');require(view(memory) is not changed,'Reload retained old source view')


@case('initiative','revoked_outbox','Unsaved revocation immediately excludes a cached pending message and survives commit')
def revoked_outbox(path):
    memory=history(path);row=outbox(memory,'a',timedelta(minutes=1));require(view(memory).pending is row,'Pending source lost')
    row.metadata['revoked']=True;require(view(memory).pending is None,'Cached revoked delivery retained')
    memory.save_memory();require(view(memory).pending is None,'Revocation lost after commit')


@case('initiative','pending_expiry','Expiring the last pending position reveals another eligible saved message without generating again')
def pending_expiry(path):
    memory=history(path);first=outbox(memory,'a',timedelta(minutes=1));second=outbox(memory,'b',timedelta(minutes=5))
    require(view(memory).pending is second,'Archive order changed')
    require(view(memory,now=NOW+timedelta(hours=5,minutes=57)).pending is first,'Expiry hid another pending source')


@case('initiative','clock_rollback','A clock rollback rechecks a source that was expired in the later view')
def clock_rollback(path):
    memory=history(path);row=outbox(memory,'a',timedelta(hours=7));require(view(memory).pending is None,'Expired source retained')
    require(view(memory,now=NOW-timedelta(hours=2)).pending is row,'Earlier clock reused later eligibility')


@case('initiative','external_writer','A different durable writer prevents reuse until the history is explicitly reloaded')
def external_writer(path):
    memory=history(path);view(memory)
    other=ConversationalMemory(storage_dir=str(path),incremental=True);other.vector_engine=None
    other.store_message('c','External synthetic report',{},'user','u')
    other.messages[-1].timestamp=NOW+timedelta(minutes=1);other.save_memory()
    try:view(memory)
    except StateRecoveryRequired:pass
    else:raise AssertionError('Cached source survived a newer writer')
    require(memory.load_memory() and view(memory).last_user.content=='External synthetic report','Reload did not recover current source')


@case('initiative','raw_write','SQLite changes without a generation update cannot hide malformed source bytes behind the cache')
def raw_write(path):
    memory=history(path);view(memory)
    with sqlite3.connect(memory._history_store.path) as db:db.execute("UPDATE history_messages SET data='{}' WHERE position=0")
    try:view(memory)
    except ValueError:pass
    else:raise AssertionError('Invalid source hidden by idle cache')


@case('initiative','bounded_users','User views remain isolated with a fixed maximum of eight cached users')
def bounded_users(path):
    memory=history(path)
    for i in range(MAX_USERS+2):memory.messages.append(Message('c','user',str(i),NOW,{},'u'+str(i)))
    memory.save_memory()
    for i in range(MAX_USERS+2):require(view(memory,'u'+str(i)).last_user.content==str(i),'Cross-user activity leak')
    require(len(memory._activity_snapshots)==MAX_USERS,'Unbounded user cache')


def unit(topic='navigation'):
    return LearningUnit(topic,'Synthetic learned report','user_u',ConfidenceLevel.LOW,NOW,{'user_id':'u'})


@case('learning','pause_no_write','The pause barrier does not rewrite already committed learning and restart keeps exact data')
def pause_no_write(path):
    learner=IncrementalLearner(str(path/'learning.json'));learner.add_learning_unit(unit());before=Path(learner.storage_path).read_bytes()
    with patch('allma_model.learning_system.incremental_learning.atomic_write_json',side_effect=AssertionError('Redundant write')):
        learner.flush_state();learner.flush_state()
    require(Path(learner.storage_path).read_bytes()==before,'Pause changed committed learning')
    require(bool(IncrementalLearner(learner.storage_path).knowledge_base.get('navigation')),'Restart lost learning')


@case('learning','commit_barrier','Pause waits for an in-flight synchronous learning commit')
def commit_barrier(path):
    import allma_model.learning_system.incremental_learning as module
    learner=IncrementalLearner(str(path/'learning.json'));writer=module.atomic_write_json
    entered,release,flushed=Event(),Event(),Event();errors=[]
    def held(*args,**kwargs):entered.set();require(release.wait(3),'Commit not released');return writer(*args,**kwargs)
    def mutate():
        try:learner.add_learning_unit(unit())
        except Exception as error:errors.append(error)
    worker=Thread(target=mutate);barrier=Thread(target=lambda:(learner.flush_state(),flushed.set()))
    with patch.object(module,'atomic_write_json',side_effect=held):
        try:
            worker.start();require(entered.wait(2),'Writer did not start');barrier.start()
            require(not flushed.wait(.05),'Pause acknowledged an uncommitted update')
        finally:
            release.set();worker.join(3)
            if barrier.ident is not None:barrier.join(3)
    require(flushed.is_set() and not errors,'Commit/barrier did not complete')
    require(bool(IncrementalLearner(learner.storage_path).knowledge_base.get('navigation')),'Committed data lost')


@case('learning','failed_commit','A failed learning mutation is rolled back and cannot be committed silently by pause')
def failed_commit(path):
    learner=IncrementalLearner(str(path/'learning.json'));learner.add_learning_unit(unit())
    with patch('allma_model.learning_system.incremental_learning.atomic_write_json',side_effect=OSError('Synthetic disk full')):
        try:learner.add_learning_unit(unit('failed'))
        except OSError:pass
        else:raise AssertionError('Failed write accepted')
        learner.flush_state()
    require('failed' not in learner.knowledge_base and 'failed' not in IncrementalLearner(learner.storage_path).knowledge_base,'Failed unit leaked')


@case('learning','explicit_save','Deliberate manual edits still persist through explicit save and invalid loads stay blocked')
def explicit_save(path):
    learner=IncrementalLearner(str(path/'learning.json'));learner.add_learning_unit(unit())
    learner.knowledge_states['navigation'].metadata['manual']=True;learner.save_state();learner.flush_state()
    require(IncrementalLearner(learner.storage_path).knowledge_states['navigation'].metadata['manual'] is True,'Explicit save ignored')
    Path(learner.storage_path).write_text('{broken');require(not learner.load_state(),'Malformed learning accepted')
    try:learner.flush_state()
    except StateRecoveryRequired:pass
    else:raise AssertionError('Invalid archive reported flushed')


def run_battery(output,*,scope=None,cancel_event=None,progress_callback=None):
    require(len(CASES)==12,'Unexpected idle-work plan')
    return run_challenges(output,CASES,version='idle-work-v1',scope=scope,cancel_event=cancel_event,
        progress_callback=progress_callback,harness_path=__file__)

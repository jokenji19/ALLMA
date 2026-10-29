"""Idle cost bounds must preserve source changes, outbox recovery and commits."""
from datetime import datetime,timedelta
from pathlib import Path
from threading import Event,Thread
from unittest.mock import patch
import sqlite3

import pytest

from allma_model.core.autobiographical_identity import POLICY_VERSION
from allma_model.memory_system.activity_snapshot import activity_snapshot,MAX_USERS
from allma_model.memory_system.conversational_memory import ConversationalMemory,Message
from allma_model.learning_system.incremental_learning import IncrementalLearner,LearningUnit,ConfidenceLevel
from allma_model.utils.persistence import StateRecoveryRequired

NOW=datetime(2026,10,24,12)
COOLDOWN=21600


def memory_at(path,count=8):
    memory=ConversationalMemory(storage_dir=str(path),incremental=True);memory.vector_engine=None
    memory.messages.extend(Message('c','user','Synthetic '+str(i),NOW-timedelta(hours=8)+timedelta(seconds=i),{},'u') for i in range(count))
    memory.save_memory()
    return memory


def view(memory,user='u',now=NOW):return activity_snapshot(memory,user,now,POLICY_VERSION,COOLDOWN)


def pending(memory,identifier,age):
    memory.messages.append(Message('c','assistant','Saved synthetic initiative',NOW-age,
        {'source':'proactive','is_valid':True,'identity_policy':POLICY_VERSION,'request_id':'PROACTIVE:'+identifier*32,
         'proactive_delivery':{'version':1,'state':'pending'}},'u'))
    memory.save_memory()
    return memory.messages[-1]


def test_one_scan_then_no_page_decode_for_unchanged_idle_history(tmp_path):
    memory=memory_at(tmp_path,800)
    with patch.object(memory._history_store,'_decode_page',wraps=memory._history_store._decode_page) as decode:
        first=view(memory)
        assert decode.call_count==800
        assert view(memory) is first and view(memory,now=NOW+timedelta(seconds=60)) is first
        assert decode.call_count==800


@pytest.mark.parametrize('operation',['content','timestamp','owner','delete','append','reload'])
def test_saved_source_changes_invalidate_the_idle_view(tmp_path,operation):
    memory=memory_at(tmp_path);before=view(memory)
    if operation=='content':memory.messages[-1].content='Corrected'
    if operation=='timestamp':memory.messages[0].timestamp=NOW
    if operation=='owner':memory.messages[-1].user_id='other'
    if operation=='delete':del memory.messages[-1]
    if operation=='append':memory.messages.append(Message('c','user','New',NOW,{},'u'))
    memory.save_memory()
    if operation=='reload':
        assert memory.load_memory()
        assert not getattr(memory,'_activity_snapshots',{})
    after=view(memory)
    assert after is not before
    expected=max((row for row in memory.messages if row.user_id=='u'),key=lambda row:row.timestamp)
    assert after.last_user.content==expected.content


def test_unsaved_nested_revocation_cannot_reuse_a_pending_delivery(tmp_path):
    memory=memory_at(tmp_path);row=pending(memory,'a',timedelta(minutes=1))
    assert view(memory).pending is row
    row.metadata['revoked']=True
    assert view(memory).pending is None
    assert not memory._activity_snapshots


@pytest.mark.parametrize('kind',['revoked','superseded','invalid','queued'])
def test_ineligible_pending_message_never_reappears_after_cache_or_restart(tmp_path,kind):
    memory=memory_at(tmp_path);row=pending(memory,'a',timedelta(minutes=1));view(memory)
    if kind in ('revoked','superseded'):row.metadata['status']=kind
    if kind=='invalid':row.metadata['is_valid']=False
    if kind=='queued':row.metadata['proactive_delivery']['state']='queued'
    memory.save_memory()
    assert view(memory).pending is None
    assert view(ConversationalMemory(storage_dir=str(tmp_path),incremental=True)).pending is None


def test_pending_expiry_reveals_an_older_position_with_a_later_deadline(tmp_path):
    memory=memory_at(tmp_path)
    first=pending(memory,'a',timedelta(minutes=1));second=pending(memory,'b',timedelta(minutes=5))
    assert view(memory).pending is second
    later=view(memory,now=NOW+timedelta(hours=5,minutes=57))
    assert later.pending is first
    assert view(memory,now=NOW+timedelta(hours=6)).pending is None


def test_clock_rollback_rechecks_previously_expired_pending_messages(tmp_path):
    memory=memory_at(tmp_path);row=pending(memory,'a',timedelta(hours=7))
    assert view(memory).pending is None
    assert view(memory,now=NOW-timedelta(hours=2)).pending is row


def test_archive_order_and_timestamp_order_remain_distinct(tmp_path):
    memory=memory_at(tmp_path)
    memory.messages[0].timestamp=NOW;memory.save_memory()
    assert view(memory).last_user.content=='Synthetic 0'
    first=pending(memory,'a',timedelta(minutes=1));second=pending(memory,'b',timedelta(minutes=1))
    assert view(memory).pending is second
    memory.messages.reverse();memory.save_memory()
    assert view(memory).pending is first


def test_external_writer_requires_reload_before_a_cached_source_is_used(tmp_path):
    memory=memory_at(tmp_path);view(memory)
    other=ConversationalMemory(storage_dir=str(tmp_path),incremental=True)
    other.store_message('c','External current report',{},'user','u')
    other.messages[-1].timestamp=NOW+timedelta(minutes=1);other.save_memory()
    with pytest.raises(StateRecoveryRequired):view(memory)
    assert memory.load_memory()
    assert view(memory).last_user.content=='External current report'


def test_sqlite_change_outside_generation_protocol_is_not_hidden_by_cache(tmp_path):
    memory=memory_at(tmp_path);view(memory)
    with sqlite3.connect(memory._history_store.path) as db:
        db.execute("UPDATE history_messages SET data='{}' WHERE position=0")
    with pytest.raises(ValueError):view(memory)


def test_unversioned_wal_write_invalidates_a_cached_view_without_touching_the_main_file(tmp_path):
    memory=memory_at(tmp_path)
    with sqlite3.connect(memory._history_store.path) as db:
        assert db.execute('PRAGMA journal_mode=WAL').fetchone()==('wal',)
        db.execute('UPDATE history_meta SET generation=generation');db.commit()
        view(memory);before=memory._history_store.path.stat().st_mtime_ns
        db.execute("UPDATE history_messages SET data='{}' WHERE position=0");db.commit()
        assert memory._history_store.path.stat().st_mtime_ns==before
        with pytest.raises(ValueError):view(memory)


def test_users_are_isolated_and_cache_has_a_fixed_user_limit(tmp_path):
    memory=memory_at(tmp_path)
    for i in range(MAX_USERS+3):memory.messages.append(Message('c','user',str(i),NOW,{},'user'+str(i)))
    memory.save_memory()
    for i in range(MAX_USERS+3):assert view(memory,'user'+str(i)).last_user.content==str(i)
    assert len(memory._activity_snapshots)==MAX_USERS
    assert 'user0' not in memory._activity_snapshots
    assert view(memory,'unknown').last_user is None


def test_unknown_policy_never_replays_an_old_pending_message(tmp_path):
    memory=memory_at(tmp_path);pending(memory,'a',timedelta(minutes=1));assert view(memory).pending
    assert activity_snapshot(memory,'u',NOW,'future-policy',COOLDOWN).pending is None


def unit(topic='navigation'):
    return LearningUnit(topic,'Synthetic learned report','user_u',ConfidenceLevel.LOW,NOW,{'user_id':'u'})


def test_learning_flush_never_reserializes_an_already_committed_archive(tmp_path):
    learner=IncrementalLearner(str(tmp_path/'learning.json'));learner.add_learning_unit(unit())
    before=Path(learner.storage_path).read_bytes()
    with patch('allma_model.learning_system.incremental_learning.atomic_write_json',side_effect=AssertionError('Redundant write')):
        learner.flush_state();learner.flush_state()
    assert Path(learner.storage_path).read_bytes()==before
    assert IncrementalLearner(learner.storage_path).knowledge_base['navigation'][0].content=='Synthetic learned report'


def test_flush_waits_for_a_synchronous_commit_before_acknowledging_pause(tmp_path):
    import allma_model.learning_system.incremental_learning as module
    learner=IncrementalLearner(str(tmp_path/'learning.json'));writer=module.atomic_write_json
    entered,release,flushed=Event(),Event(),Event();failures=[]
    def held(*args,**kwargs):
        entered.set();assert release.wait(3);return writer(*args,**kwargs)
    def mutate():
        try:learner.add_learning_unit(unit())
        except Exception as error:failures.append(error)
    worker=Thread(target=mutate);barrier=Thread(target=lambda:(learner.flush_state(),flushed.set()))
    with patch.object(module,'atomic_write_json',side_effect=held):
        try:
            worker.start();assert entered.wait(2);barrier.start()
            assert not flushed.wait(.05)
            release.set();worker.join(3);barrier.join(3)
        finally:release.set();worker.join(3)
    assert flushed.is_set() and not failures
    assert IncrementalLearner(learner.storage_path).knowledge_base['navigation']


def test_failed_learning_commit_is_not_promoted_by_a_later_pause(tmp_path):
    learner=IncrementalLearner(str(tmp_path/'learning.json'));learner.add_learning_unit(unit())
    with patch('allma_model.learning_system.incremental_learning.atomic_write_json',side_effect=OSError('Synthetic disk full')):
        with pytest.raises(OSError):learner.add_learning_unit(unit('failed'))
        learner.flush_state()
    assert 'failed' not in learner.knowledge_base
    assert 'failed' not in IncrementalLearner(learner.storage_path).knowledge_base


def test_explicit_save_still_persists_deliberate_manual_edits(tmp_path):
    learner=IncrementalLearner(str(tmp_path/'learning.json'));learner.add_learning_unit(unit())
    learner.knowledge_states['navigation'].metadata['manual']=True;learner.save_state();learner.flush_state()
    assert IncrementalLearner(learner.storage_path).knowledge_states['navigation'].metadata['manual'] is True


def test_flush_cannot_hide_a_failed_load(tmp_path):
    path=tmp_path/'learning.json';path.write_text('{broken')
    learner=IncrementalLearner(str(path))
    with pytest.raises(StateRecoveryRequired):learner.flush_state()
    assert path.read_text()=='{broken'


from allma_model.utils.idle_diagnostics import CASES,run_battery


@pytest.mark.parametrize('challenge',CASES,ids=[case[1] for case in CASES])
def test_idle_native_challenge(tmp_path,challenge):
    challenge[3](tmp_path)


def test_complete_idle_runner_uses_isolated_case_directories(tmp_path):
    result=run_battery(tmp_path/'reports')
    assert result['complete'] and result['passed']==result['total']==12
    assert not result['failures']

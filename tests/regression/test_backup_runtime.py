from pathlib import Path
from types import SimpleNamespace
from threading import Event,Lock,RLock,Thread
from unittest.mock import patch
import json
import pytest

from allma_model.utils.backup_runtime import BackupRuntime
from allma_model.utils.state_backup import BackupError
from allma_model.core.delivery_updates import DeliveryUpdates


def core(tmp_path):
    root=tmp_path/'allma_state';root.mkdir(exist_ok=True)
    (root/'allma_settings.json').write_text('{}')
    return SimpleNamespace(db_path=str(root/'allma.db'),_lock=RLock(),_turn_lock=Lock(),
        _user_active=Event(),_shutdown_event=Event(),_benchmark_active=False,
        conversational_memory=SimpleNamespace(lock=RLock(),messages=[]),
        dream_manager=SimpleNamespace(_state_lock=RLock(),is_dreaming=False))


@pytest.mark.parametrize('busy',['turn','user','dream','benchmark','switch','shutdown'])
def test_snapshot_never_takes_over_active_subsystem(tmp_path,busy):
    c=core(tmp_path);runtime=BackupRuntime(c)
    if busy=='turn':c._turn_lock.acquire()
    if busy=='user':c._user_active.set()
    if busy=='dream':c.dream_manager.is_dreaming=True
    if busy=='benchmark':c._benchmark_active=True
    if busy=='switch':c._model_switching=True
    if busy=='shutdown':c._shutdown_event.set()
    with pytest.raises(BackupError):runtime.create()
    assert c._user_active.is_set()==(busy=='user')
    if busy=='turn':c._turn_lock.release()
    assert c._turn_lock.acquire(False);c._turn_lock.release()


def test_snapshot_is_interruptible_and_always_releases_admission(tmp_path):
    c=core(tmp_path);runtime=BackupRuntime(c)
    with runtime.idle():
        assert c._user_active.is_set()
        assert not c._turn_lock.acquire(False)
        runtime.interrupt()
        with pytest.raises(BackupError):runtime.store.create(cancel_event=runtime.cancel)
    assert not c._user_active.is_set()
    assert c._turn_lock.acquire(False);c._turn_lock.release()
    assert runtime.create()['verified']


@pytest.mark.parametrize('checkpoint',[0,1,1792230000000000,2**53-3])
def test_learning_sequence_survives_calendar_jumps_and_preserves_legacy_high_water(tmp_path,checkpoint):
    c=core(tmp_path);c.answer_recall=SimpleNamespace(delivery_checkpoint=checkpoint)
    updates=DeliveryUpdates(c)
    # Neither date forward nor backward can affect logical delivery order.
    with patch('time.time_ns',side_effect=AssertionError('wall clock must not order learning')):
        first=updates.prepare_user('u','c','Esperienza uno')['sequence']
        second=updates.prepare_user('u','c','Esperienza due')['sequence']
    assert (first,second)==(checkpoint+1,checkpoint+2)


def test_learning_sequence_reconstructs_history_high_water_without_journal(tmp_path):
    c=core(tmp_path)
    c.conversational_memory.messages=[SimpleNamespace(metadata={'experience_update':{'sequence':9000}})]
    assert DeliveryUpdates(c).prepare_user('u','c','next')['sequence']==9001


def test_sequence_exhaustion_requires_migration_and_never_wraps(tmp_path):
    c=core(tmp_path);c.answer_recall=SimpleNamespace(delivery_checkpoint=2**53-1)
    with pytest.raises(ValueError):DeliveryUpdates(c).prepare_user('u','c','next')

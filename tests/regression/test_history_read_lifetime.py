"""A suspended page reader must not retain locks or republish old cache positions."""
from contextlib import contextmanager
from threading import Thread,Event
import sqlite3
import pytest
from allma_model.memory_system.conversational_memory import ConversationalMemory


def seeded(path,count=3):
    memory=ConversationalMemory(storage_dir=str(path),incremental=True)
    memory.vector_engine=None
    for i in range(count):memory.store_message('c',f'Item {i}',{},'user','u')
    return memory


@pytest.mark.parametrize('reverse',[False,True])
def test_suspended_reader_does_not_hold_a_database_connection(tmp_path,reverse):
    memory=seeded(tmp_path)
    original=memory._history_store.connect
    active=[]
    @contextmanager
    def counted(*args,**options):
        active.append(True)
        try:
            with original(*args,**options) as db:yield db
        finally:active.pop()
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(memory._history_store,'connect',counted)
        iterator=reversed(memory.messages) if reverse else iter(memory.messages)
        next(iterator)
        assert not active
        memory.store_message('c','New',{},'user','u')
        with pytest.raises(RuntimeError):next(iterator)
    assert [row.content for row in memory.messages]==['Item 0','Item 1','Item 2','New']


@pytest.mark.parametrize('wal',[False,True])
@pytest.mark.parametrize('reverse',[False,True])
def test_reorder_invalidates_old_reader_without_replacing_current_cache(tmp_path,wal,reverse):
    memory=seeded(tmp_path)
    if wal:
        with sqlite3.connect(tmp_path/'conversation_history.db') as db:db.execute('PRAGMA journal_mode=WAL')
    iterator=reversed(memory.messages) if reverse else iter(memory.messages)
    next(iterator)
    memory.messages.reverse();memory.save_memory()
    with pytest.raises(RuntimeError):list(iterator)
    expected=['Item 2','Item 1','Item 0']
    assert [memory.messages[i].content for i in range(3)]==expected
    assert [row.content for row in ConversationalMemory(storage_dir=str(tmp_path)).messages]==expected


def test_writer_completes_while_another_thread_leaves_a_reader_suspended(tmp_path):
    memory=seeded(tmp_path)
    iterator=iter(memory.messages);next(iterator)
    complete=Event();errors=[]
    def write():
        try:memory.store_message('c','New',{},'user','u')
        except Exception as error:errors.append(error)
        finally:complete.set()
    writer=Thread(target=write);writer.start()
    try:assert complete.wait(2),'Writer depends on closing a suspended reader'
    finally:
        iterator.close();writer.join(10)
    assert not errors and len(memory.messages)==4


def test_external_write_cannot_mix_new_pages_into_an_old_read(tmp_path):
    first=seeded(tmp_path,100)
    second=ConversationalMemory(storage_dir=str(tmp_path),incremental=True)
    iterator=iter(first.messages);next(iterator)
    second.store_message('c','External',{},'user','u')
    with pytest.raises(RuntimeError):list(iterator)
    assert first.load_memory() and len(first.messages)==101


def test_explicit_reload_invalidates_the_previous_collection_reader(tmp_path):
    memory=seeded(tmp_path)
    iterator=iter(memory.messages);next(iterator)
    assert memory.load_memory()
    with pytest.raises(RuntimeError):next(iterator)

from concurrent.futures import ThreadPoolExecutor
from itertools import count
from allma_model.ui.chat_session import ChatSession


def session():
    ids = count(1)
    return ChatSession(lambda: f'conversation-{next(ids)}')


def test_parallel_submissions_have_one_owner():
    chat = session()
    with ThreadPoolExecutor(max_workers=8) as pool:
        turns = list(pool.map(lambda _: chat.begin(), range(16)))
    assert sum(turn is not None for turn in turns) == 1


def test_new_chat_cancels_then_waits_for_worker_to_release_model():
    chat = session()
    first = chat.begin()
    assert chat.new_conversation() is None
    assert first.cancelled.is_set()
    assert chat.begin() is None
    assert chat.conversation_id == 'conversation-1'
    assert chat.finish(first) == 'conversation-2'
    second = chat.begin()
    assert second.request_id > first.request_id
    assert second.conversation_id == 'conversation-2'
    assert chat.finish(first) is None  # Stale worker cannot release a newer turn.
    assert chat.begin() is None


def test_cancel_keeps_conversation_and_repeated_reset_is_one_change():
    chat = session()
    first = chat.begin()
    chat.cancel()
    chat.finish(first)
    assert chat.conversation_id == 'conversation-1'
    second = chat.begin()
    chat.new_conversation()
    chat.new_conversation()
    assert chat.finish(second) == 'conversation-2'


def test_idle_new_chat_creates_backend_conversation():
    chat = session()
    assert chat.new_conversation() == 'conversation-2'
    assert chat.begin().conversation_id == 'conversation-2'


def test_stale_cancel_cannot_interrupt_later_request():
    chat=session();first=chat.begin();chat.finish(first);second=chat.begin()
    assert not chat.cancel(first.request_id)
    assert not second.cancelled.is_set()
    assert chat.cancel(second.request_id)
    assert second.cancelled.is_set()
    assert not chat.cancel(second.request_id)


def test_invalid_cancel_id_and_idle_cancel_do_not_change_state():
    chat=session()
    assert not chat.cancel(1)
    turn=chat.begin()
    for bad in (True,'1',-1,0):
        assert not chat.cancel(bad)
        assert not turn.cancelled.is_set()

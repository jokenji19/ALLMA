"""Turn ordering and final flush under a slow or paused WebView."""
from allma_model.ui.stream_delivery import StreamDelivery
import ast
from pathlib import Path
from types import SimpleNamespace, ModuleType
from unittest.mock import Mock
import sys


class Event:
    def __init__(self, callback):
        self.callback = callback
        self.cancelled = False

    def cancel(self):
        self.cancelled = True


def delivery():
    events, calls = [], []
    def schedule(callback, interval):
        event = Event(callback)
        events.append((event, interval))
        return event
    return StreamDelivery(calls.append, schedule), events, calls


def test_many_tokens_cross_bridge_once_with_same_text_and_unicode():
    stream, scheduled, calls = delivery()
    stream.start(7)
    pieces = ['Ciao ', '👩‍💻', '\n', '🌊'] * 25
    for piece in pieces:
        stream.push(piece, False, 7)
    assert calls == []
    assert len(scheduled) == 1
    assert scheduled[0][1] <= 0.1
    scheduled[0][0].callback(0)
    assert calls == [[[''.join(pieces), False, 7]]]


def test_final_delivery_precedes_completion_and_late_chunks_are_ignored():
    stream, scheduled, calls = delivery()
    stream.start(3)
    stream.push('ragiono ', True, 3)
    stream.push('ancora', True, 3)
    stream.push('Risposta', False, 3)
    stream.finish(3)
    calls.append('endStream')
    stream.push('in ritardo', False, 3)
    scheduled[0][0].callback(0)
    assert calls == [[['ragiono ancora', True, 3], ['Risposta', False, 3]], 'endStream']


def test_new_turn_drops_old_pending_events_without_mixing_requests():
    stream, scheduled, calls = delivery()
    stream.start(1)
    stream.push('vecchio', True, 1)
    stream.start(2)
    stream.push('tardivo', False, 1)
    stream.push('nuovo', False, 2)
    stream.finish(1)  # A stale completion cannot flush the new request.
    assert calls == []
    stream.finish(2)
    assert calls == [[['nuovo', False, 2]]]
    assert scheduled[0][0].cancelled


def test_pause_clears_scheduled_updates_and_late_callbacks():
    stream, scheduled, calls = delivery()
    stream.start(None)
    stream.push('parziale', False, None)
    stream.clear()
    scheduled[0][0].callback(0)
    stream.push('tardivo', True, None)
    assert calls == []
    assert scheduled[0][0].cancelled


def test_slow_webview_has_only_one_outstanding_poll(monkeypatch):
    path = Path(__file__).resolve().parents[2]/'allma_model/ui/webview_bridge.py'
    tree = ast.parse(path.read_text())
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'WebViewBridge')
    method = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == '_poll_js')
    namespace = {'logging': Mock()}
    exec(compile(ast.Module(body=[method], type_ignores=[]), str(path), 'exec'), namespace)
    queued = []
    runnable = ModuleType('android.runnable')
    runnable.run_on_ui_thread = lambda fn: lambda: queued.append(fn)
    monkeypatch.setitem(sys.modules, 'android.runnable', runnable)
    bridge = SimpleNamespace(running=True, webview=object(), poll_callback=object(),
                             _closed=False, _poll_inflight=False, _evaluate_js=Mock())
    poll = lambda: namespace['_poll_js'](bridge, 0)
    for _ in range(20):
        poll()
    assert len(queued) == 1
    queued.pop()()
    assert bridge._evaluate_js.call_count == 1
    poll()
    assert queued == []  # The callback has not acknowledged that result yet.
    bridge._poll_inflight = False
    poll()
    assert len(queued) == 1
    bridge._closed = True
    queued.pop()()
    assert bridge._evaluate_js.call_count == 1
    assert bridge._poll_inflight is False


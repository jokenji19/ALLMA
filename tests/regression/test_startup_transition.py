"""Check native startup handoff ownership without a live Android UI."""
import ast
import json
import sys
from pathlib import Path
from types import SimpleNamespace, MethodType
from unittest.mock import Mock

ROOT=Path(__file__).resolve().parents[2]


def bridge(monkeypatch, motion=True):
    source=ROOT/'allma_model/ui/webview_bridge.py'
    tree=ast.parse(source.read_text())
    cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='WebViewBridge')
    methods=[n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name in ('reveal_startup','resume')]
    env={'json':json}
    monkeypatch.setitem(sys.modules,'android',SimpleNamespace())
    monkeypatch.setitem(sys.modules,'android.runnable',SimpleNamespace(run_on_ui_thread=lambda fn:fn))
    monkeypatch.setitem(sys.modules,'startup_ui',SimpleNamespace(native_motion_allowed=lambda:motion))
    exec(compile(ast.Module(body=methods,type_ignores=[]),str(source),'exec'),env)
    view=SimpleNamespace(_closed=False,running=True,_startup_revealed=False,_startup_ready=False,
                         _startup_reveal_event=Mock(),webview=Mock(),_evaluate_js=Mock(),is_android=True,
                         call_js_function=Mock(),_start_polling=Mock())
    view.reveal_startup=MethodType(env['reveal_startup'],view)
    view.resume=MethodType(env['resume'],view)
    return view


def test_ready_handoff_cancels_guard_and_reveals_once(monkeypatch):
    b=bridge(monkeypatch);guard=b._startup_reveal_event
    b.reveal_startup();b.reveal_startup()
    guard.cancel.assert_called_once()
    b.webview.animate.assert_called_once()
    b.webview.animate().alpha.assert_called_once_with(1.0)
    b.webview.animate().alpha().setDuration.assert_called_once_with(320)
    assert b._startup_revealed and b._startup_ready
    assert '"native": true' in b._evaluate_js.call_args.args[0]
    b._evaluate_js.assert_called_once()


def test_reduced_motion_is_immediate_and_acknowledged(monkeypatch):
    b=bridge(monkeypatch,motion=False);b.reveal_startup()
    b.webview.animate.assert_not_called()
    b.webview.setAlpha.assert_called_once_with(1.0)
    assert '"motion": false' in b._evaluate_js.call_args.args[0]


def test_ready_while_paused_waits_for_resume(monkeypatch):
    b=bridge(monkeypatch);b.running=False;b.reveal_startup()
    assert b._startup_ready and not b._startup_revealed
    b.webview.animate.assert_not_called()
    b.resume()
    assert b._startup_revealed
    b.webview.animate.assert_called_once()


def test_closed_bridge_never_restarts_transition(monkeypatch):
    b=bridge(monkeypatch);b._closed=True;b.reveal_startup();b.resume()
    b.webview.animate.assert_not_called()
    b._evaluate_js.assert_not_called()

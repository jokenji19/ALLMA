import ast
import json
from pathlib import Path
from threading import Event, Thread
from types import SimpleNamespace
from unittest.mock import Mock
import pytest
from allma_model.utils.brain_activity import BrainActivity
from allma_model.utils.generation_control import GenerationCancelled


def test_real_call_is_visible_while_running_and_never_retains_arguments_or_outputs():
    activity=BrainActivity();entered=Event();release=Event()
    def work():
        activity.begin()
        def actual(secret):
            entered.set();assert release.wait(2);return secret
        assert activity.call('memory',actual,'private-test-input')=='private-test-input'
        activity.finish()
    thread=Thread(target=work);thread.start();assert entered.wait(2)
    try:
        view=activity.snapshot()
        assert view['active']
        assert next(n for n in view['nodes'] if n['id']=='memory')['state']['phase']=='running'
        # A different thread cannot invent foreground activity.
        activity.emit('model','completed')
        assert not any(e['module']=='model' for e in activity.snapshot()['events'])
    finally:
        release.set();thread.join(2)
    view=activity.snapshot()
    assert not view['active'] and view['status']=='completed'
    assert 'private-test-input' not in json.dumps(view)
    assert not any(e['module']=='model' for e in view['events'])
    view['nodes'].clear()
    assert activity.snapshot()['nodes']


def test_bounded_history_new_turn_cursor_and_observed_links():
    activity=BrainActivity();activity.begin()
    for _ in range(110):
        activity.emit('memory','completed');activity.emit('model','completed')
    view=activity.snapshot()
    assert len(view['events'])==96
    assert any(e.get('from')=='memory' and e['module']=='model' for e in view['events'])
    assert activity.snapshot(view['seq'])['events']==[]
    activity.finish();activity.begin()
    view=activity.snapshot(-1)
    assert view['turn']==2 and len(view['events'])==1 and view['events'][0]['module']=='input'
    assert all(n['state'] is None for n in view['nodes'] if n['id']!='input')


def test_observation_preserves_exception_and_closes_running_state_on_cancellation():
    activity=BrainActivity();activity.begin()
    error=GenerationCancelled('cancelled')
    def actual():raise error
    with pytest.raises(GenerationCancelled) as caught:
        activity.call('model',actual)
    assert caught.value is error
    activity.finish('cancelled')
    view=activity.snapshot()
    assert view['status']=='cancelled'
    assert all(n['state'] is None or n['state']['phase']!='running' for n in view['nodes'])


def test_bridge_snapshot_never_calls_model_or_memory_queries():
    source=Path(__file__).resolve().parents[2]/'allma_model/ui/webview_bridge.py'
    cls=next(n for n in ast.parse(source.read_text()).body if isinstance(n,ast.ClassDef) and n.name=='WebViewBridge')
    method=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='handle_brain_activity')
    env={'json':json};exec(compile(ast.fix_missing_locations(ast.Module(body=[method],type_ignores=[])),str(source),'exec'),env)
    engine=SimpleNamespace(model_path='/private/models/selected.gguf',generate=Mock())
    core=SimpleNamespace(brain_activity=BrainActivity(),_llm=engine,module_orchestrator=SimpleNamespace(modules={}))
    bridge=SimpleNamespace(core=core,call_js_function=Mock())
    env['handle_brain_activity'](bridge,'invalid cursor')
    name,payload=bridge.call_js_function.call_args.args
    data=json.loads(payload)
    assert name=='receiveBrainActivity' and data['available']
    assert data['model']=='selected.gguf' and '/private/' not in payload
    assert next(n for n in data['nodes'] if n['id']=='creativity')['available'] is False
    assert 'avatar' not in data
    assert not hasattr(bridge, '_avatar_presence'), 'Inspecting the brain must not create or read a visual identity'
    engine.generate.assert_not_called()


def test_native_lifecycle_explicitly_suspends_and_resumes_viewer():
    source=Path(__file__).resolve().parents[2]/'allma_model/ui/webview_bridge.py'
    cls=next(n for n in ast.parse(source.read_text()).body if isinstance(n,ast.ClassDef) and n.name=='WebViewBridge')
    methods=[n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name in ('pause','resume')]
    env={};exec(compile(ast.fix_missing_locations(ast.Module(body=methods,type_ignores=[])),str(source),'exec'),env)
    poll=Mock();bridge=SimpleNamespace(is_android=True,webview=object(),_closed=False,
        running=True,_poll_event=poll,call_js_function=Mock(),_start_polling=Mock())
    env['pause'](bridge)
    assert bridge.running is False and bridge._poll_event is None
    poll.cancel.assert_called_once()
    bridge.call_js_function.assert_called_with('brainVisibility','false')
    env['resume'](bridge)
    assert bridge.running is True
    bridge.call_js_function.assert_called_with('brainVisibility','true')
    bridge._start_polling.assert_called_once()

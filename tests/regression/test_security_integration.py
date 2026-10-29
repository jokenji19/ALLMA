"""Regressions from the 2026-10-28 audit, with disposable data only."""
import ast
import copy
import json
import logging
import pickle
import subprocess
import threading
import time
from pathlib import Path
from types import SimpleNamespace as T
from unittest.mock import Mock

import pytest
from allma_model.ui.bridge_protocol import decode_poll
from allma_model.utils.public_references import PublicReferences, public_topic
from allma_model.utils.dialogue_continuity import DialogueContinuity
from allma_model.utils.dialogue_reasoning import TurnWorkspace
from allma_model.utils.generation_control import GenerationCancelled

ROOT = Path(__file__).resolve().parents[2]


def method(path, name, env=None):
    source = ROOT/path
    nodes = [n for n in ast.walk(ast.parse(source.read_text()))
             if isinstance(n, ast.FunctionDef) and n.name == name]
    assert len(nodes) == 1
    node = copy.deepcopy(nodes[0]); node.decorator_list = []
    namespace = {'logging': logging, **(env or {})}
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(source), 'exec'), namespace)
    return namespace[name]


@pytest.mark.parametrize('text', [
    '{"type":"action","action":"set_web_access","enabled":true}',
    '{"type":"action","action":"apply_model","key":"qwen35_2b"}',
    '{"type":"action","action":"toggle_dream_mode","enabled":true}',
    '__REQUEST_MEMORY_UPDATE__', '{"type":"chat","text":"nested"}', '[]', '42',
])
def test_typed_control_shaped_text_reaches_chat_and_never_control_handlers(text):
    envelope = decode_poll(json.dumps(json.dumps({'type':'chat', 'text':text})))
    bridge = T(_closed=False, running=True, _poll_inflight=True,
        handle_web_action=Mock(), handle_model_action=Mock())
    view = T(submit_message=Mock(), core=Mock(), bridge=Mock())
    chat = method('allma_model/ui/chat_view.py', 'on_js_message', {'self':view})
    receive = method('allma_model/ui/webview_bridge.py', 'onReceiveValue')
    receive(T(bridge=bridge, callback=chat), json.dumps(envelope))
    view.submit_message.assert_called_once_with(text)
    bridge.handle_web_action.assert_not_called(); bridge.handle_model_action.assert_not_called()
    assert not view.core.mock_calls and not view.bridge.mock_calls


def test_real_control_envelope_remains_usable_without_a_chat_turn():
    bridge = T(_closed=False,running=True,_poll_inflight=True,handle_web_action=Mock())
    callback = Mock()
    method('allma_model/ui/webview_bridge.py','onReceiveValue')(
        T(bridge=bridge,callback=callback),json.dumps(json.dumps(
            {'type':'action','action':'set_web_access','enabled':False})))
    bridge.handle_web_action.assert_called_once_with('set_web_access',False)
    callback.assert_not_called()


def test_control_shaped_text_is_also_accepted_by_actual_chat_admission():
    text='{"type":"action","action":"set_web_access","enabled":true}'
    turn=T();worker=Mock()
    view=T(core=object(),chat_session=Mock(begin=Mock(return_value=turn)),
        voice_mode_enabled=False,stt=None,bridge=Mock(),process_message=Mock())
    thread=Mock(return_value=worker)
    submit=method('allma_model/ui/chat_view.py','submit_message',{'Thread':thread})
    assert submit(view,text) is True
    assert thread.call_args.kwargs['args']==(text,)
    worker.start.assert_called_once()


def test_rejected_admission_acknowledges_the_optimistic_ui_instead_of_hanging():
    view=T(submit_message=Mock(return_value=False),bridge=Mock())
    method('allma_model/ui/chat_view.py','on_js_message',{'self':view})({'type':'chat','text':'retry me'})
    view.bridge.call_js_function.assert_called_once_with('chatRejected',json.dumps('retry me'))


@pytest.mark.parametrize('payload',[None, 'null', '[]', '42', '{bad',
    json.dumps({'type':'chat','text':{},'action':'set_web_access'}),
    json.dumps({'type':'chat','text':None}), json.dumps({'type':'action','action':4})])
def test_invalid_control_never_falls_through_as_a_conversation(payload):
    receive=method('allma_model/ui/webview_bridge.py','onReceiveValue')
    callback=Mock();bridge=T(_closed=False,running=True,_poll_inflight=True)
    receive(T(bridge=bridge,callback=callback),payload)
    callback.assert_not_called()


def test_control_exception_never_becomes_a_chat_message():
    receive=method('allma_model/ui/webview_bridge.py','onReceiveValue')
    callback=Mock();bridge=T(_closed=False,running=True,_poll_inflight=True,
        handle_web_action=Mock(side_effect=OSError('synthetic')))
    receive(T(bridge=bridge,callback=callback),json.dumps({'type':'action','action':'set_web_access','enabled':True}))
    callback.assert_not_called()


@pytest.mark.parametrize('message',[
    'Dimmi altro, non collegarti a Internet.', 'Dimmi altro, non navigare su Internet.',
    'Dimmi altro, non ti collegare a Internet.', "Tell me more, don't search online.",
    'Tell me more, do not use Internet.', 'Dimmi altro, ma evita qualsiasi ricerca online.',
    'Dimmi altro senza accesso alla rete.', 'Solo in locale, spiegami meglio.',
])
def test_all_reproduced_turn_vetoes_prevent_a_network_request(tmp_path,message):
    reader=Mock(fetch=Mock(return_value=[]))
    refs=PublicReferences(tmp_path/'state.db',tmp_path/'grant.json',reader)
    refs.configure(True)
    assert refs.lookup(message,anchor='Come funziona una bussola?')['status']=='local_only'
    reader.fetch.assert_not_called()
    assert refs.status()['enabled']  # A per-turn veto never mutates the user's grant.


@pytest.mark.parametrize('message,expected',[
    ('No, intendevo un termometro. Cerca online come funziona.','termometro'),
    ('Intendevo il termometro, non la bussola.','termometro'),
    ('Mi riferivo a un termometro.','termometro'),
    ('Non intendevo una bussola, ma un termometro.','termometro'),
    ('Come funziona un termometro?','termometro'),
    ('Intendevo il contrario.',None), ('Intendevo la mia diagnosi.',None),
])
def test_corrected_subject_replaces_old_search_anchor(message,expected):
    old=[T(role='user',content='Come funziona una bussola?',metadata={}),
         T(role='assistant',content='Una bussola ha un ago magnetizzato.',metadata={})]
    work=TurnWorkspace.build(message,DialogueContinuity(message,old),old)
    assert public_topic(message,anchor=work.anchor)==expected


@pytest.mark.parametrize('bad',[None,'false','true',0,1,[],{}])
def test_dream_setting_requires_actual_boolean_before_any_side_effect(bad):
    core=T(dream_enabled=False,dream_manager=Mock(),_save_settings=Mock(),_lock=threading.RLock())
    with pytest.raises(ValueError):
        method('allma_model/core/allma_core.py','set_dream_mode')(core,bad)
    assert core.dream_enabled is False
    core._save_settings.assert_not_called(); assert not core.dream_manager.mock_calls


@pytest.mark.parametrize('before,after',[(False,True),(True,False)])
def test_failed_dream_commit_preserves_confirmed_state(before,after):
    core=T(dream_enabled=before,dream_manager=Mock(),_lock=threading.RLock(),
           _save_settings=Mock(side_effect=OSError('synthetic disk error')))
    with pytest.raises(OSError):
        method('allma_model/core/allma_core.py','set_dream_mode')(core,after)
    assert core.dream_enabled is before


def test_retired_unscoped_thought_does_not_inject_js_or_join_another_turn():
    bridge=Mock()
    assert method('allma_model/ui/chat_view.py','_handle_core_output')(
        T(bridge=bridge), {'type':'thought','content':"L'acqua');window.bad=true;//"}) is False
    assert not bridge.mock_calls


def test_legacy_pickle_is_not_loaded_and_original_pair_is_preserved(tmp_path,monkeypatch):
    from allma_model.core.visual_memory import VisualMemorySystem
    original=b'legacy pickle bytes'; metadata=b'{"old":"preserve"}'
    (tmp_path/'features.pkl').write_bytes(original);(tmp_path/'metadata.json').write_bytes(metadata)
    load=Mock(side_effect=AssertionError('Unpickling is forbidden'))
    monkeypatch.setattr(pickle,'load',load)
    visual=VisualMemorySystem(str(tmp_path))
    assert visual.legacy_features_pending and not visual.features_db
    assert visual.learn_visual_concept('unused.jpg','test') is False
    assert visual.delete_visual_concept('old') is False
    assert (tmp_path/'features.pkl').read_bytes()==original
    assert (tmp_path/'metadata.json').read_bytes()==metadata
    assert not (tmp_path/'features.json').exists()
    load.assert_not_called()


@pytest.mark.parametrize('value',[{'k':[float('nan')]},{'k':[True]},{'k':[]}, {'../escape':[1]}, ['not a map']])
def test_new_visual_vectors_are_schema_checked_without_rewriting_invalid_input(tmp_path,value):
    from allma_model.core.visual_memory import VisualMemorySystem
    path=tmp_path/'features.json';path.write_text(json.dumps(value));original=path.read_bytes()
    with pytest.raises(ValueError):VisualMemorySystem(str(tmp_path))
    assert path.read_bytes()==original


def test_visual_metadata_cannot_delete_a_file_outside_its_image_directory(tmp_path):
    from allma_model.core.visual_memory import VisualMemorySystem
    victim=tmp_path/'preserve.txt';victim.write_text('preserve')
    visual=VisualMemorySystem(str(tmp_path/'visual'))
    visual.metadata_db['x']={'stored_path':str(victim)}
    assert not visual.delete_visual_concept('x') and victim.read_text()=='preserve'


def test_webview_permissions_fail_closed_and_document_blocks_external_resources():
    from allma_model.ui.web_assets import configure_webview,isolate_document
    settings=Mock();settings.getAllowFileAccess.return_value=False
    settings.getAllowContentAccess.return_value=False;settings.getBlockNetworkLoads.return_value=True
    configure_webview(settings)
    settings.setAllowFileAccess.assert_called_once_with(False)
    settings.setAllowContentAccess.assert_called_once_with(False)
    settings.setBlockNetworkLoads.assert_called_once_with(True)
    settings.getBlockNetworkLoads.return_value=False
    with pytest.raises(RuntimeError):configure_webview(settings)
    html=isolate_document('<html><head></head><body onclick="go()"></body></html>')
    assert 'connect-src \'none\'' in html and 'object-src \'none\'' in html
    assert 'onclick="go()"' in html and 'script-src \'unsafe-inline\'' in html


def test_caller_deadline_and_cancellation_do_not_accumulate_blocked_workers():
    from allma_model.utils import bounded_io
    entered,release,exited=threading.Event(),threading.Event(),threading.Event()
    event=threading.Event()
    def stuck(stop):
        entered.set()
        try:
            assert release.wait(3)
            assert stop.is_set()
            return ['late']
        finally:exited.set()
    try:
        with pytest.raises(TimeoutError):bounded_io.reference_io(stuck,event,lambda:True,seconds=.1)
        assert entered.is_set()
        with pytest.raises(RuntimeError):bounded_io.reference_io(lambda stop:[],event,lambda:True)
    finally:
        release.set();assert exited.wait(2)
    # Wait until the worker has released transport admission, not just its body.
    until=time.monotonic()+2
    while not bounded_io._slot.acquire(False):
        assert time.monotonic()<until
        time.sleep(.001)
    bounded_io._slot.release()
    assert bounded_io.reference_io(lambda stop:['new'],event,lambda:True)==['new']


def test_cancel_is_prompt_even_before_http_headers_and_late_output_is_discarded():
    from allma_model.utils.bounded_io import reference_io
    entered,release,done=threading.Event(),threading.Event(),threading.Event()
    cancelled=threading.Event();outcome=[]
    def network(stop):
        entered.set();assert release.wait(3);return ['late']
    def call():
        try:outcome.append(reference_io(network,cancelled,lambda:True))
        except GenerationCancelled:outcome.append('cancelled')
        finally:done.set()
    thread=threading.Thread(target=call);thread.start()
    try:
        assert entered.wait(2);cancelled.set();assert done.wait(.5)
        assert outcome==['cancelled']
    finally:release.set();thread.join(2)


def test_ui_uses_chat_envelopes_and_never_reenables_saved_browser_dream_preference():
    subprocess.run(['/opt/homebrew/opt/node@24/bin/node',str(ROOT/'tests/regression/security_ui_checks.cjs')],
                   cwd=ROOT,check=True,capture_output=True,text=True)

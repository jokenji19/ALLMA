import json
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from allma_model.utils.avatar_presence import AvatarPresence
from allma_model.utils.cognitive_state import CognitiveStateStore


def core(growth=None, emotion=None):
    p=SimpleNamespace(emotion_growth_view=Mock(return_value=growth or {}),
                      expression_view=Mock(return_value={}))
    return SimpleNamespace(coalescence_processor=p,
        emotional_core=SimpleNamespace(get_user_emotional_state=Mock(return_value=emotion)))


def emotion(owner='alice', now=1000, **changes):
    return dict(confidence=.9,intensity=.8,valence=.8,arousal=.5,
                context={'user_id':owner,'observed_at':now,'conversation_id':'synthetic'},**changes)


def test_seed_is_persistent_isolated_and_never_derived_from_identity_information(tmp_path):
    db=tmp_path/'allma.db';a=AvatarPresence(db)
    first=a.snapshot(core(),'alice',now=1000)
    assert AvatarPresence(db).snapshot(core(),'alice',now=1000)==first
    assert a.snapshot(core(),'bob',now=1000)['seed']!=first['seed']
    assert a.snapshot(core(),'alice',now=1000)['seed']==first['seed']
    assert not {'alice','bob'}&set(first)
    assert 'alice' not in json.dumps(first)


def test_transient_affect_changes_expression_never_identity_or_morphology(tmp_path):
    a=AvatarPresence(tmp_path/'allma.db');c=core()
    initial=a.snapshot(c,'alice',now=1000)
    for valence in [-1,.8]:
        c.emotional_core.get_user_emotional_state.return_value=emotion()
        c.emotional_core.get_user_emotional_state.return_value['valence']=valence
        observed=a.snapshot(c,'alice',now=1000)
        assert observed['seed']==initial['seed'] and observed['shape']==initial['shape']
        assert observed['expression']!=initial['expression']
    expired=a.snapshot(c,'alice',now=1181)
    assert expired['expression']==initial['expression']
    assert expired['expression_basis']=='neutral'


@pytest.mark.parametrize('changes',[
    {'context':{'user_id':'bob','observed_at':1000}},
    {'context':{'user_id':'alice','observed_at':1200}},
    {'confidence':.2}, {'confidence':float('nan')},
])
def test_other_people_future_and_uncertain_affect_do_not_drive_face(changes):
    e=emotion();e.update(changes)
    r=AvatarPresence().snapshot(core(emotion=e),'alice',now=1000)
    assert r['expression_basis']=='neutral'
    assert r['expression']['smile']==r['expression']['concern']==0


def test_only_small_recomputable_consolidated_growth_shapes_the_portrait(tmp_path):
    a=AvatarPresence(tmp_path/'allma.db');c=core();base=a.snapshot(c,'alice',now=1000)
    c.coalescence_processor.emotion_growth_view.return_value={
        'trait_deltas':{'empathy':.05,'curiosity':.04},
        'associations':{'joy':{'stage':'integrated'},'sadness':{'stage':'suspended'}},
        'response_disposition':{'mode':'care'}}
    r=a.snapshot(c,'alice',now=1000)
    assert r['shape']['softness']==pytest.approx(.025)
    assert r['shape']['openness']==pytest.approx(.012)
    assert r['growth']['integrated']==1
    for key in ['jaw','eyes','nose','cheeks','brow']:assert r['shape'][key]==base['shape'][key]
    # Watching it repeatedly cannot train it or accumulate fake facial changes.
    before=deepcopy(c.coalescence_processor.emotion_growth_view.return_value)
    for _ in range(12):assert a.snapshot(c,'alice',now=1000)==r
    assert c.coalescence_processor.emotion_growth_view.return_value==before
    c.coalescence_processor.emotion_growth_view.return_value={}
    assert a.snapshot(c,'alice',now=1000)['shape']==base['shape']


def test_snapshot_is_a_bounded_whitelist_no_text_or_model_call(tmp_path):
    c=core(emotion=emotion());c.emotional_core.get_user_emotional_state.return_value['context']['text']='private-conversation'
    c.coalescence_processor.expression_view.return_value={'secret':'private-preference'}
    c._llm=SimpleNamespace(generate=Mock())
    r=AvatarPresence(tmp_path/'allma.db').snapshot(c,'alice',now=1000)
    assert len(json.dumps(r))<1600
    assert 'private-' not in json.dumps(r)
    assert r['symbolic'] and r['subject']=='ALLMA_visual_representation'
    c._llm.generate.assert_not_called()


def test_damaged_visual_identity_is_never_replaced(tmp_path):
    db=tmp_path/'allma.db';store=CognitiveStateStore(db)
    store.put('avatar_identity',{'version':1,'profiles':{'alice':'damaged'}})
    before=store.path.read_bytes()
    with pytest.raises(ValueError):AvatarPresence(db).snapshot(core(),'alice',now=1000)
    assert store.path.read_bytes()==before


def test_avatar_identity_survives_verified_backup_restore(tmp_path):
    from allma_model.utils.runtime_storage import prepare_runtime_storage
    from allma_model.utils.state_backup import StateBackups
    from allma_model.utils.state_restore import stage_restore, apply_pending_restore
    import sqlite3
    root=Path(prepare_runtime_storage(tmp_path))
    with sqlite3.connect(root/'allma.db') as db:db.execute('CREATE TABLE initial(value TEXT)')
    a=AvatarPresence(root/'allma.db');a.appearance('alice','neutral')
    avatar=a.snapshot(core(),'alice',now=1000)
    backups=StateBackups(root);backups.create()
    CognitiveStateStore(root/'allma.db').put('avatar_identity',{'version':1,'profiles':{}})
    stage_restore(root,backups.latest());apply_pending_restore(tmp_path)
    restored=AvatarPresence(root/'allma.db').snapshot(core(),'alice',now=1000)
    assert restored==avatar


def test_suspended_style_does_not_change_face_but_consolidated_style_can():
    a=AvatarPresence();c=core();base=a.snapshot(c,'alice',now=1000)
    c.coalescence_processor.expression_view.return_value={'tendencies':{
        'questions':{'stage':'suspended','value':'exploratory'}}}
    assert a.snapshot(c,'alice',now=1000)['shape']==base['shape']
    c.coalescence_processor.expression_view.return_value['tendencies']['questions']['stage']='integrated'
    assert a.snapshot(c,'alice',now=1000)['shape']['openness']>base['shape']['openness']


def test_first_open_requires_explicit_choice_even_with_an_existing_identity(tmp_path):
    db=tmp_path/'allma.db';a=AvatarPresence(db)
    seed=a.identity('alice')
    r=a.snapshot(core(),'alice',now=1000)
    assert not r['configured'] and r['presentation'] is None
    assert r['visual_age_months']==96 and r['life_stage']=='child'
    assert r['seed']==seed
    assert not CognitiveStateStore(db).get('avatar_appearance')


@pytest.mark.parametrize('choice',['feminine','masculine','neutral'])
def test_each_presentation_survives_restart_without_changing_memory_or_seed(tmp_path,choice):
    db=tmp_path/'allma.db';a=AvatarPresence(db)
    store=CognitiveStateStore(db);store.put('test_memory',{'fact':'synthetic'})
    before=a.snapshot(core(),'alice',now=1000)
    a.appearance('alice',choice)
    after=AvatarPresence(db).snapshot(core(),'alice',now=1000)
    assert after['configured'] and after['presentation']==choice
    for key in ['seed','shape','expression','growth']:assert after[key]==before[key]
    assert store.get('test_memory')=={'fact':'synthetic'}
    assert not a.snapshot(core(),'bob')['configured']
    assert after['visual_age_months']==96


@pytest.mark.parametrize('bad',['female','automatic','',True,1,{},[]])
def test_invalid_choice_cannot_modify_archive(tmp_path,bad):
    a=AvatarPresence(tmp_path/'allma.db');a.appearance('alice','neutral')
    before=a.store.path.read_bytes()
    with pytest.raises(ValueError):a.appearance('alice',bad)
    assert a.store.path.read_bytes()==before


def test_failed_save_never_claims_a_choice_was_saved(tmp_path,monkeypatch):
    a=AvatarPresence(tmp_path/'allma.db')
    monkeypatch.setattr(a.store,'put',Mock(side_effect=OSError('synthetic full disk')))
    with pytest.raises(OSError):a.appearance('alice','feminine')
    assert a.appearance('alice') is None


def test_bad_appearance_section_is_preserved(tmp_path):
    a=AvatarPresence(tmp_path/'allma.db')
    a.store.put('avatar_appearance',{'version':1,'profiles':{'alice':'automatic'}})
    before=a.store.path.read_bytes()
    with pytest.raises(ValueError):a.appearance('alice','neutral')
    assert a.store.path.read_bytes()==before


def test_changing_presentation_preserves_other_profiles(tmp_path):
    a=AvatarPresence(tmp_path/'allma.db');a.appearance('bob','masculine')
    a.appearance('alice','feminine');a.appearance('alice','neutral')
    assert a.appearance('alice')=='neutral' and a.appearance('bob')=='masculine'


def configuration_handler():
    import ast
    path=Path(__file__).resolve().parents[2]/'allma_model/ui/webview_bridge.py'
    cls=next(n for n in ast.parse(path.read_text()).body if isinstance(n,ast.ClassDef) and n.name=='WebViewBridge')
    fn=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='handle_avatar_configuration')
    env={'json':json};exec(compile(ast.fix_missing_locations(ast.Module(body=[fn],type_ignores=[])),str(path),'exec'),env)
    return env[fn.name]


def test_native_configuration_uses_current_profile_and_confirms_only_after_save(tmp_path):
    bridge=SimpleNamespace(core=SimpleNamespace(db_path=tmp_path/'allma.db',_current_user_id='alice'),
                           call_js_function=Mock(),handle_brain_activity=Mock())
    configuration_handler()(bridge,'feminine','synthetic-request')
    name,payload=bridge.call_js_function.call_args.args;result=json.loads(payload)
    assert name=='receiveAvatarConfiguration' and result['ok']
    assert result['request_id']=='synthetic-request'
    assert AvatarPresence(tmp_path/'allma.db').appearance('alice')=='feminine'
    assert AvatarPresence(tmp_path/'allma.db').appearance('user_default') is None
    bridge.handle_brain_activity.assert_called_once()


def test_native_configuration_reports_write_failure_without_refresh(tmp_path):
    presence=SimpleNamespace(appearance=Mock(side_effect=OSError('synthetic')))
    bridge=SimpleNamespace(core=SimpleNamespace(_current_user_id='alice'),_avatar_presence=presence,
                           call_js_function=Mock(),handle_brain_activity=Mock())
    configuration_handler()(bridge,'neutral','synthetic-request')
    assert json.loads(bridge.call_js_function.call_args.args[1])['ok'] is False
    bridge.handle_brain_activity.assert_not_called()

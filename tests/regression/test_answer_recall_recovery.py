"""Synthetic corruption must not turn partial answer learning into a fresh archive."""
from copy import deepcopy
import json
from unittest.mock import patch
import pytest

from allma_model.learning_system.answer_recall import AnswerRecall
from allma_model.utils.persistence import StateRecoveryRequired

QUESTION='Spiega come funziona la luce bianca.'

def record(question=QUESTION):
    return {'user':'u','question':question,'answer':'La luce bianca contiene diversi colori.',
            'observations':2,'confirmations':['one','two'],'rejected':False}

def state():
    return {'version':1,'records':{'known':record()},'delivery_checkpoint':7}

@pytest.mark.parametrize('kind',['truncated','root','version_bool','version_future','partial','checkpoint'])
def test_corrupt_archive_cannot_be_overwritten_by_new_observation(tmp_path,kind):
    data=state()
    if kind=='version_bool': data['version']=True
    if kind=='version_future': data['version']=2
    if kind=='partial': data['records']['broken']={}
    if kind=='checkpoint': data['delivery_checkpoint']=True
    raw=b'{truncated' if kind=='truncated' else json.dumps([] if kind=='root' else data).encode()
    path=tmp_path/'recall.json';path.write_bytes(raw)
    recall=AnswerRecall(path)
    with pytest.raises(StateRecoveryRequired):
        recall.observe('new','u',QUESTION,'Una nuova risposta.','new-event',delivery_sequence=8)
    assert path.read_bytes()==raw
    assert not recall.records and recall.delivery_checkpoint==0
    assert path.with_name(path.name+'.invalid.bak').read_bytes()==raw


def test_partial_archive_cannot_supply_a_confirmed_answer(tmp_path):
    data=state();data['records']['broken']={}
    path=tmp_path/'recall.json';path.write_text(json.dumps(data))
    recall=AnswerRecall(path)
    assert recall.lookup('known','u') is None
    assert not recall.feedback('known','u','third',True)
    assert not recall.records


def test_distinct_corruptions_keep_distinct_recovery_copies(tmp_path):
    path=tmp_path/'recall.json'
    first=b'{first';second=b'{second'
    path.write_bytes(first);AnswerRecall(path)
    path.write_bytes(second);AnswerRecall(path)
    assert {p.read_bytes() for p in tmp_path.glob('recall.json.invalid*.bak')}=={first,second}
    assert path.read_bytes()==second


@pytest.mark.parametrize('question',['Qual è il meteo oggi?','Qual è il tuo colore preferito?'])
def test_old_ineligible_confirmed_entries_cannot_bypass_current_recall_policy(tmp_path,question):
    data=state();data['records']['known']=record(question)
    path=tmp_path/'recall.json';path.write_text(json.dumps(data))
    assert AnswerRecall(path).lookup('known','u') is None


def test_failed_reload_keeps_live_snapshot_but_disables_it_until_verified_repair(tmp_path):
    path=tmp_path/'recall.json';path.write_text(json.dumps(state()))
    recall=AnswerRecall(path);before=deepcopy(recall.records)
    path.write_text('{broken')
    assert recall.load_state() is False
    assert recall.records==before and recall.delivery_checkpoint==7
    assert recall.lookup('known','u') is None
    assert not recall.feedback('known','u','third',True)
    with pytest.raises(StateRecoveryRequired): recall._save()
    path.write_text(json.dumps(state()))
    assert recall.load_state() is True and recall.load_error is None
    assert recall.lookup('known','u')['answer']==record()['answer']
    recall.observe('new','u',QUESTION,'Una nuova risposta.','event',delivery_sequence=8)
    assert AnswerRecall(path).delivery_checkpoint==8


def test_failed_recovery_copy_still_cannot_authorize_overwriting_original(tmp_path):
    path=tmp_path/'recall.json';path.write_bytes(b'{broken')
    with patch('allma_model.learning_system.answer_recall.preserve_invalid_file',side_effect=OSError('no space')):
        recall=AnswerRecall(path)
    with pytest.raises(StateRecoveryRequired):
        recall.observe('new','u',QUESTION,'Una risposta.','event')
    assert path.read_bytes()==b'{broken'


def test_removed_loaded_archive_requires_explicit_recovery(tmp_path):
    path=tmp_path/'recall.json';path.write_text(json.dumps(state()))
    recall=AnswerRecall(path);path.unlink()
    assert recall.load_state() is False
    with pytest.raises(StateRecoveryRequired): recall._save()
    assert not path.exists()


def test_healthy_state_without_old_checkpoint_remains_compatible(tmp_path):
    data=state();del data['delivery_checkpoint']
    path=tmp_path/'recall.json';path.write_text(json.dumps(data))
    recall=AnswerRecall(path)
    assert recall.load_error is None and recall.delivery_checkpoint==0
    assert recall.lookup('known','u') is not None


@pytest.mark.parametrize('feedback',['Risposta corretta','Risposta sbagliata'])
def test_real_chat_cannot_claim_unsaved_feedback_or_call_model_to_acknowledge_it(tmp_path,monkeypatch,feedback):
    from unittest.mock import Mock
    from allma_model.core.allma_core import ALLMACore
    monkeypatch.chdir(tmp_path)
    core=ALLMACore(mobile_mode=True,db_path=str(tmp_path/'core.db'))
    core._ensure_mobile_llm=lambda:None;core._llm=Mock()
    core._llm.generate.return_value=record()['answer']
    core._llm.get_generation_meta.return_value={'finish_reason':'stop'}
    try:
        conversation=core.start_conversation('u')
        first=core.process_message('u',conversation,QUESTION)
        assert first.is_valid
        path=core.answer_recall.path;path.write_text('{broken')
        assert core.answer_recall.load_state() is False
        core._llm.generate.reset_mock()
        response=core.process_message('u',conversation,feedback)
        assert response.is_valid and not response.knowledge_integrated
        assert response.metadata['source']=='learning_feedback_unavailable'
        assert response.metadata['learning_feedback']['status']=='not_saved'
        assert response.metadata['generation']['llm_used'] is False
        core._llm.generate.assert_not_called()
        assert path.read_text()=='{broken'
    finally: core.close()


def test_normal_chat_remains_available_with_corrupt_recall_and_pending_learning(tmp_path,monkeypatch):
    from unittest.mock import Mock
    from allma_model.core.allma_core import ALLMACore
    monkeypatch.chdir(tmp_path)
    core=ALLMACore(mobile_mode=True,db_path=str(tmp_path/'core.db'))
    core._ensure_mobile_llm=lambda:None;core._llm=Mock()
    core._llm.generate.return_value=record()['answer']
    core._llm.get_generation_meta.return_value={'finish_reason':'stop'}
    try:
        core.answer_recall._save()
        healthy=core.answer_recall.path.read_bytes()
        core.answer_recall.path.write_text('{broken')
        assert core.answer_recall.load_state() is False
        response=core.process_message('u',core.start_conversation('u'),QUESTION)
        assert response.is_valid and response.content==record()['answer']
        assert response.metadata['delivery_updates']['status']=='pending'
        assert core.answer_recall.path.read_text()=='{broken'
        core.answer_recall.path.write_bytes(healthy)
        assert core.answer_recall.load_state() is True
        assert core.delivery_updates.recover()['pending']==0
        assert sum(r['observations'] for r in core.answer_recall.records.values())==1
        assert core.identity_engine_v5.accepted_turns==1
        assert core.delivery_updates.recover()['pending']==0
        assert sum(r['observations'] for r in core.answer_recall.records.values())==1
        assert core.identity_engine_v5.accepted_turns==1
    finally: core.close()

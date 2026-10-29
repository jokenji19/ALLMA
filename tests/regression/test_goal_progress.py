from pathlib import Path
from unittest.mock import Mock, patch
import json

import pytest

from allma_model.agency_system.action_authority import ActionAuthority
from allma_model.agency_system.goal_progress import GoalProgress
from allma_model.utils.cognitive_state import CognitiveStateStore
from allma_model.utils.goal_dialogue import command, prepare

CREATE='Nuovo obiettivo: Preparare una lista di prova\nCriterio: tre voci controllate\nProssimo passo: scrivere la prima voce'

@pytest.fixture
def core(tmp_path,monkeypatch):
    monkeypatch.chdir(tmp_path)
    from allma_model.core.allma_core import ALLMACore
    value=ALLMACore(mobile_mode=True,db_path=str(tmp_path/'allma.db'))
    value._ensure_mobile_llm=lambda:None
    value._llm=Mock()
    value._llm.generate.side_effect=AssertionError('Task continuity must not call the model')
    value.decision_runtime.route=Mock(side_effect=AssertionError('No Decider for explicit task controls'))
    yield value
    value.close()


def say(core,text,cid=None,user='u'):
    cid=cid or core.start_conversation(user)
    return core.process_message(user,cid,text)


def only(core,user='u'):
    return core.goal_progress.goals(user)[0]


def test_creation_has_no_permissions_beyond_review_and_is_attributed(core):
    result=say(core,CREATE)
    assert result.is_valid and result.metadata['generation']['llm_used'] is False
    goal=only(core)
    assert goal['allowed_actions']=={'review_goal':'read'}
    assert goal['workflow']['verification'] is None
    assert goal['workflow']['last_event']['source']=='user_report'
    assert not core.action_authority.permits('u',goal['id'],'write','state_write')
    assert result.metadata['knowledge_verified'] is False
    core._llm.generate.assert_not_called()


def test_new_chat_and_reload_keep_progress_and_correction(core):
    say(core,CREATE)
    say(core,'Progresso obiettivo: prima voce controllata\nProssimo passo: controllare la seconda voce')
    say(core,'Criterio obiettivo: quattro voci controllate')
    restored=GoalProgress(ActionAuthority(CognitiveStateStore(core.db_path)))
    goal=restored.goals('u')[0]
    assert goal['workflow']['progress']=='prima voce controllata'
    assert goal['workflow']['criterion']=='quattro voci controllate'
    assert goal['workflow']['next_step']=='controllare la seconda voce'
    reply=say(core,'Riprendiamo l’obiettivo')
    assert 'quattro voci controllate' in reply.content and reply.is_valid


def test_result_is_not_completion_until_explicit_confirmation(core):
    say(core,CREATE)
    result=say(core,'Risultato obiettivo: elenco controllato')
    goal=only(core)
    assert result.is_valid and goal['status']=='active'
    assert goal['workflow']['phase']=='awaiting_verification'
    assert goal['workflow']['result']['source']=='user_report'
    assert 'dichiarazione' in result.content
    confirmed=say(core,'Confermo il risultato dell’obiettivo')
    goal=only(core)
    assert confirmed.is_valid and goal['status']=='completed'
    assert goal['workflow']['verification']=='confirmed_by_user'
    assert goal['workflow']['outcomes']['confirmed']==1
    assert confirmed.metadata['knowledge_verified'] is False


def test_changing_criterion_invalidates_old_result_and_confirmation(core):
    say(core,CREATE)
    say(core,'Risultato obiettivo: elenco completato')
    say(core,'Criterio obiettivo: cinque voci controllate')
    response=say(core,'Confermo il risultato dell’obiettivo')
    assert 'Non c’è un risultato' in response.content
    goal=only(core)
    assert goal['status']=='active' and goal['workflow']['result'] is None
    assert goal['workflow']['verification'] is None


def test_reject_and_reopen_preserve_outcome_history(core):
    say(core,CREATE)
    say(core,'Risultato obiettivo: elenco incompleto')
    say(core,'Risultato obiettivo sbagliato: mancava una voce')
    assert only(core)['workflow']['outcomes']['rejected']==1
    say(core,'Risultato obiettivo: elenco corretto')
    say(core,'Confermo il risultato dell’obiettivo')
    response=say(core,'Per l’obiettivo “Preparare una lista di prova”: Riapri obiettivo')
    assert response.is_valid and only(core)['status']=='active'
    assert only(core)['workflow']['result'] is None
    assert only(core)['workflow']['outcomes']['confirmed']==1


def test_multiple_tasks_require_disambiguation_and_do_not_cross_users(core):
    say(core,CREATE)
    say(core,'Nuovo obiettivo: Seconda lista')
    ambiguous=say(core,'Progresso obiettivo: aggiornamento ambiguo')
    assert 'A quale obiettivo' in ambiguous.content
    assert all(not g['workflow']['progress'] for g in core.goal_progress.goals('u'))
    targeted=say(core,'Per l’obiettivo “Seconda lista”: Progresso: prima voce')
    assert targeted.is_valid
    assert core.goal_progress.goals('u')[1]['workflow']['progress']=='prima voce'
    assert core.goal_progress.goals('other')==[]
    assert 'Non hai ancora' in say(core,'Quali sono i miei obiettivi?',user='other').content


def test_stop_and_revoke_suppress_future_initiative(core):
    say(core,CREATE)
    assert core.goal_progress.initiative('u') is None
    say(core,'Puoi propormi il prossimo passo dell’obiettivo')
    reference=core.goal_progress.initiative('u')
    assert reference and core.goal_progress.current_reference('u',reference)
    say(core,'Sospendi obiettivo')
    assert core.goal_progress.initiative('u') is None
    assert not core.goal_progress.current_reference('u',reference)
    say(core,'Riprendi obiettivo')
    assert core.goal_progress.initiative('u')
    say(core,'Annulla obiettivo')
    assert core.goal_progress.initiative('u') is None
    assert only(core)['status']=='revoked'


def test_user_event_save_failure_creates_no_goal(core):
    with patch.object(core.conversational_memory._history_store,'commit',side_effect=OSError('disk full')):
        with pytest.raises(OSError):say(core,CREATE)
    assert core.goal_progress.goals('u')==[]


def test_goal_save_failure_is_pending_and_recoverable_without_duplicate(core):
    store=core.action_authority.store
    original=store.put
    def fail(section,value):
        if section==ActionAuthority.SECTION:raise OSError('goal write unavailable')
        return original(section,value)
    with patch.object(store,'put',side_effect=fail):
        reply=say(core,CREATE)
    assert not reply.is_valid and reply.metadata['goal_update']['status']=='pending'
    assert core.goal_progress.goals('u')==[]
    assert core.delivery_updates.recover(synchronize=True)['status']=='completed'
    assert len(core.goal_progress.goals('u'))==1
    core.delivery_updates.recover(synchronize=True)
    assert len(core.goal_progress.goals('u'))==1


def test_ack_failure_after_commit_never_repeats_a_goal_mutation(core):
    with patch.object(core.delivery_updates,'_ack',side_effect=OSError('ack unavailable')):
        reply=say(core,CREATE)
    assert reply.is_valid
    first=only(core)
    assert core.delivery_updates.recover(synchronize=True)['status']=='completed'
    assert only(core)['id']==first['id'] and only(core)['workflow']['revision']==1


def test_stale_update_is_acknowledged_without_overwriting_newer_state(core):
    say(core,CREATE)
    tracker=core.goal_progress
    control,_=tracker.prepare('u',command('Progresso obiettivo: vecchio progresso'))
    say(core,'Progresso obiettivo: progresso più recente')
    reference={'event':'synthetic-stale','conversation':'c','timestamp':'2026-10-24T00:00:00','input_sha256':'a'*64,'source':'user_report'}
    seq=tracker.delivery_checkpoint+1
    result=tracker.apply('u',control,reference,seq)
    assert result['status']=='stale' and only(core)['workflow']['progress']=='progresso più recente'


def test_bad_cognitive_archive_never_claims_no_goals_or_overwrites_it(core):
    say(core,CREATE)
    path=core.action_authority.store.path
    path.write_text('{broken',encoding='utf-8')
    result=say(core,'Quali sono i miei obiettivi?')
    assert not result.is_valid and 'Non posso leggere' in result.content
    assert path.read_text()=='{broken'


@pytest.mark.parametrize('text',[
    'Vorrei preparare un elenco.', 'Ho finito.', 'Il modello dice: Nuovo obiettivo: inventato',
    'Scrivi una storia: Nuovo obiettivo: inventato', 'Nuovo obiettivo:',
    'Nuovo obiettivo: prova\nPermessi: external', 'Confermo il risultato',
])
def test_normal_text_and_incomplete_or_untrusted_controls_do_not_admit_tasks(text):
    assert command(text) is None


def test_diagnostic_runner_covers_actual_core_lifecycle(tmp_path):
    from allma_model.agency_system.goal_diagnostics import run_battery
    summary=run_battery(tmp_path/'diagnostic',scope='pytest synthetic')
    assert summary['passed']==summary['total']==26 and summary['complete']


def test_goal_backup_preserves_provenance_and_rejects_inconsistent_completion(core,tmp_path):
    from allma_model.utils.state_backup import StateBackups,_check_data,BackupError
    from allma_model.utils.backup_crypto import decrypt_backup
    import zipfile
    say(core,CREATE)
    say(core,'Progresso obiettivo: prima voce')
    expected=only(core)
    root=Path(core.db_path).parent
    backup=StateBackups(root,primary=Path(core.db_path).name)
    exported=tmp_path/'task-backup.allma'
    assert backup.create()['verified']
    backup.export(exported,'Synthetic-goal-backup-2026!')
    plain=tmp_path/'task-verified.zip'
    decrypt_backup(exported,plain,'Synthetic-goal-backup-2026!')
    with zipfile.ZipFile(plain) as archive:
        entries=[name for name in archive.namelist() if name.endswith('cognitive_state.json')]
        assert len(entries)==1
        saved=json.loads(archive.read(entries[0]))
    assert saved['sections']['action_authority']['goals'][expected['id']]['workflow']==expected['workflow']
    from allma_model.utils.runtime_storage import prepare_runtime_storage
    from allma_model.utils.state_restore import apply_pending_restore
    receiver_base=tmp_path/'receiver'
    receiver=Path(prepare_runtime_storage(receiver_base))
    StateBackups(receiver,primary=Path(core.db_path).name).stage_encrypted_restore(exported,'Synthetic-goal-backup-2026!')
    apply_pending_restore(receiver_base)
    transferred=GoalProgress(ActionAuthority(CognitiveStateStore(str(receiver/Path(core.db_path).name))))
    assert transferred.goals('u')[0]==expected
    invalid=tmp_path/'invalid-cognitive.json'
    saved['sections']['action_authority']['goals'][expected['id']]['workflow']['phase']='completed'
    invalid.write_text(json.dumps(saved))
    with pytest.raises(BackupError):_check_data(invalid,'cognitive_state.json')


def test_ordinary_messages_never_read_task_storage():
    tracker=Mock()
    tracker.goals.side_effect=AssertionError('No storage work on ordinary dialogue')
    assert prepare(tracker,'u','Spiega come si forma un arcobaleno.') is None
    tracker.goals.assert_not_called()


def test_pending_goal_proposal_is_cancelled_after_correction(core):
    from allma_model.utils.proactive_runtime import _deliver_saved
    say(core,CREATE)
    say(core,'Puoi propormi il prossimo passo dell’obiettivo')
    reference=core.goal_progress.initiative('u')
    cid=core.start_conversation('u')
    metadata={'source':'proactive','request_id':'PROACTIVE:synthetic-goal',
        'proactive_delivery':{'version':1,'state':'pending'},
        'goal_reference':{'id':reference['id'],'revision':reference['revision']}}
    core.conversational_memory.store_message(cid,'Vuoi riprendere la lista?',metadata,'assistant','u')
    record=core.conversational_memory.messages[-1]
    say(core,'Prossimo passo obiettivo: controllare una voce diversa')
    core.dream_enabled=True;core._foreground=True;core._current_user_id='u';core._proactive_cancel.clear()
    callback=Mock(return_value=True)
    result=_deliver_saved(core,callback,record)
    assert result['status']=='cancelled' and result['reason']=='goal_changed'
    callback.assert_not_called()
    assert record.metadata['proactive_delivery']['state']=='cancelled'


def test_open_goal_question_uses_current_state_without_mutating_goal(core):
    say(core,CREATE)
    before=only(core)
    core.decision_runtime.route=Mock(return_value={'status':'selected','choice':'reason'})
    core._llm.generate.side_effect=None
    core._llm.generate.return_value='Puoi controllare una voce alla volta.'
    core._llm.get_generation_meta.return_value={'finish_reason':'stop'}
    result=say(core,'Come posso organizzare questo obiettivo?')
    prompt=core._llm.generate.call_args.kwargs['prompt']
    assert 'Stato attuale dell’obiettivo' in prompt and 'tre voci controllate' in prompt
    assert result.metadata['decision']['goal_reference']['id']==before['id']
    assert only(core)==before

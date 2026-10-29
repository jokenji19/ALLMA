from copy import deepcopy
from pathlib import Path
import json
from unittest.mock import Mock, patch

import pytest

from allma_model.learning_system.plan_experience import context, assessment, find, valid
from allma_model.learning_system.plan_experience_diagnostics import CASES, failed, evaluate, row, say as task_say


@pytest.mark.parametrize('group,name,criterion,fn',CASES,ids=[c[1] for c in CASES])
def test_shared_android_scenario(tmp_path,group,name,criterion,fn):
    (tmp_path/name).mkdir()
    fn(tmp_path/name)


@pytest.fixture
def core(tmp_path,monkeypatch):
    monkeypatch.chdir(tmp_path)
    from allma_model.core.allma_core import ALLMACore
    c=ALLMACore(mobile_mode=True,db_path=str(tmp_path/'allma.db'))
    c._ensure_mobile_llm=lambda:None
    c._llm=Mock()
    c._llm.generate.return_value='Proposta di piano\n1. Prepara la lista dei documenti necessari.\n2. Controlla i documenti della lista.'
    c._llm.get_generation_meta.return_value={'finish_reason':'stop'}
    c.decision_runtime.route=Mock(return_value={'status':'selected','choice':'reason'})
    yield c
    c.close()


def say(core,text,user='u'):
    return core.process_message(user,core.start_conversation(user),text)


def experience(core):
    say(core,'Nuovo obiettivo: Lista viaggio mare\nCriterio: documenti viaggio controllati')
    say(core,'Proponi un piano per questo obiettivo');say(core,'Adotta questo piano')
    say(core,'Risultato del passo: lista preparata')
    say(core,'Risultato del passo sbagliato: mancava il documento richiesto per il viaggio')
    source=core.goal_progress.goals('u')[0]
    lesson=source['workflow']['learning']['cases']['step_0_rejected']['id']
    say(core,'Risultato obiettivo: lista corretta e controllata');say(core,'Confermo il risultato dell’obiettivo')
    return lesson


def test_real_chat_path_feeds_a_new_plan_with_experience_and_no_extra_generation(core):
    lesson=experience(core)
    say(core,'Nuovo obiettivo: Lista viaggio montagna\nCriterio: documenti viaggio controllati')
    reply=say(core,'Proponi un piano per questo obiettivo')
    assert reply.is_valid and lesson in reply.metadata['plan_experience']['case_ids']
    prompt=core._llm.generate.call_args.kwargs['prompt']
    assert 'mancava il documento' in prompt and 'non una causa certa' in prompt
    assert core._llm.generate.call_count==2
    assert core.goal_progress.goals('u')[-1]['workflow'].get('plan') is None
    assert reply.metadata['plan_experience']['hypotheses_are_unverified'] is True


def test_status_view_and_user_feedback_use_host_logic_without_qwen_or_decider(core):
    lesson=experience(core)
    core._llm.generate.reset_mock();core.decision_runtime.route.reset_mock()
    reply=say(core,'Cosa hai imparato dai piani?')
    assert reply.is_valid and lesson in reply.content and 'ipotesi da verificare' in reply.content
    assert reply.metadata['knowledge_verified'] is False
    core._llm.generate.assert_not_called();core.decision_runtime.route.assert_not_called()


def test_generated_unadopted_and_unconfirmed_plans_cannot_train_experience(core):
    say(core,'Nuovo obiettivo: Lista viaggio mare\nCriterio: documenti viaggio controllati')
    say(core,'Proponi un piano per questo obiettivo')
    assert 'learning' not in core.goal_progress.goals('u')[0]['workflow']
    say(core,'Adotta questo piano');say(core,'Risultato del passo: lista pronta')
    assert 'learning' not in core.goal_progress.goals('u')[0]['workflow']


def test_goal_commit_and_learning_share_replay_checkpoint(core):
    say(core,'Nuovo obiettivo: Lista viaggio mare\nCriterio: documenti viaggio controllati')
    say(core,'Proponi un piano per questo obiettivo');say(core,'Adotta questo piano')
    say(core,'Risultato del passo: lista pronta')
    with patch.object(core.delivery_updates,'_ack',side_effect=OSError('synthetic lost acknowledgement')):
        reply=say(core,'Risultato del passo sbagliato: mancava il documento per il viaggio')
    before=deepcopy(core.goal_progress.goals('u')[0]['workflow']['learning'])
    assert reply.is_valid
    assert core.delivery_updates.recover(synchronize=True)['status']=='completed'
    assert core.goal_progress.goals('u')[0]['workflow']['learning']==before
    assert len(before['cases'])==1


def test_repeated_task_instances_are_deduplicated_even_when_both_have_feedback(tmp_path):
    f,lesson=failed(tmp_path);evaluate(f,'Lista viaggio montagna',lesson)
    goals=f.tracker.goals('u');duplicate=deepcopy(goals[-1]);duplicate['id']='new-instance'
    g,c=find(goals,lesson)
    assert assessment(goals+[duplicate],g,c)['supporting_tasks']==1


def test_counterexample_is_shown_as_contested_in_a_new_plan_context(tmp_path):
    f,lesson=failed(tmp_path);evaluate(f,'Lista viaggio montagna',lesson,False)
    target=deepcopy(f.tracker.goals('u')[-1]);target['id']='unseen';target['objective']='Lista viaggio lavoro'
    items=context(f.tracker.goals('u'),target)
    found=next(item for item in items if item['id']==lesson)
    assert found['status']=='contested' and found['counterexamples']==1


def test_oldest_same_score_case_is_not_mistaken_for_proof(tmp_path):
    f,lesson=failed(tmp_path)
    g,c=row(f,lesson)
    assert assessment(f.tracker.goals('u'),g,c)['status']=='candidate'
    assert 'non da verifiche fisiche' in f.tracker.experience_view('u')


def test_foreign_and_quoted_lesson_controls_cannot_train(core):
    lesson=experience(core)
    assert not say(core,'Lezione utile: '+lesson,user='other').metadata.get('goal_update')
    reply=say(core,'Nel racconto un personaggio dice «Lezione utile: '+lesson+'».')
    assert not reply.metadata.get('goal_update')
    assert all(not g['workflow'].get('learning',{}).get('feedback') for g in core.goal_progress.goals('u'))


def test_malformed_learning_stops_updates_without_overwriting_state(core):
    experience(core)
    path=core.action_authority.store.path
    saved=json.loads(path.read_text());goals=saved['sections']['action_authority']['goals']
    next(iter(goals.values()))['workflow']['learning']['cases']['step_0_rejected']['reviewed']['source']='model_generated'
    path.write_text(json.dumps(saved));before=deepcopy(saved['sections']['action_authority'])
    reply=say(core,'Cosa hai imparato dai piani?')
    assert not reply.is_valid and json.loads(path.read_text())['sections']['action_authority']==before


def test_backup_semantics_validate_experiences_and_cross_device_restore(core,tmp_path):
    from allma_model.utils.state_backup import StateBackups,_check_data,BackupError
    from allma_model.utils.backup_crypto import decrypt_backup
    from allma_model.utils.state_restore import apply_pending_restore
    from allma_model.utils.runtime_storage import prepare_runtime_storage
    from allma_model.agency_system.goal_progress import GoalProgress
    from allma_model.agency_system.action_authority import ActionAuthority
    from allma_model.utils.cognitive_state import CognitiveStateStore
    import zipfile
    lesson=experience(core)
    backups=StateBackups(tmp_path);assert backups.create()['verified']
    encrypted=tmp_path/'experience.allma';backups.export(encrypted,'Synthetic-learning-2026!')
    archive=tmp_path/'experience.zip';decrypt_backup(encrypted,archive,'Synthetic-learning-2026!')
    with zipfile.ZipFile(archive) as z:
        name=next(n for n in z.namelist() if n.endswith('cognitive_state.json'))
        data=json.loads(z.read(name))
    receiver_base=tmp_path/'receiver';receiver=Path(prepare_runtime_storage(receiver_base))
    StateBackups(receiver).stage_encrypted_restore(encrypted,'Synthetic-learning-2026!');apply_pending_restore(receiver_base)
    restored=GoalProgress(ActionAuthority(CognitiveStateStore(str(receiver/'allma.db'))))
    assert lesson in restored.experience_view('u')
    state=next(iter(data['sections']['action_authority']['goals'].values()))['workflow']['learning']
    state['cases']['step_0_rejected']['reviewed']['input_sha256']='bad'
    invalid=tmp_path/'invalid.json';invalid.write_text(json.dumps(data))
    with pytest.raises(BackupError):_check_data(invalid,'cognitive_state.json')


def test_real_model_experience_probe_isolates_profiles_and_transfers_context(core,tmp_path):
    from allma_model.agency_system.plan_diagnostics import PlanExperienceModelRun
    worker=PlanExperienceModelRun()
    try:
        worker.setup_brain(core);worker.report_path=str(tmp_path/'report'/'transfer.md')
        worker.run_tests()
        summary=worker.manifest['summary']
        assert summary['completed']==2 and summary['state_isolated']
        assert all(r['experience_context']['case_ids'] and r['adopted'] for r in summary['results'])
        assert core.goal_progress.goals('u')==[]
        assert summary['semantic_accuracy'] is None
    finally:worker.close()
    assert not core._user_active.is_set()



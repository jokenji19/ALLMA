from datetime import datetime
from types import SimpleNamespace
from unittest.mock import Mock,patch
import json

import pytest

from allma_model.agency_system.goal_plans import extract_steps,proposal,selection,valid_plan
from allma_model.agency_system.goal_progress import GoalProgress
from allma_model.agency_system.action_authority import ActionAuthority
from allma_model.utils.cognitive_state import CognitiveStateStore
from allma_model.utils.goal_dialogue import prepare

CREATE='Nuovo obiettivo: Preparare una lista di prova\nCriterio: tre voci controllate\nProssimo passo: scrivere la prima voce'
PLAN='Proposta di piano\n1. Scrivi tre voci distinte nella lista.\n2. Controlla ogni voce e correggi gli errori.'

@pytest.fixture
def core(tmp_path,monkeypatch):
    monkeypatch.chdir(tmp_path)
    from allma_model.core.allma_core import ALLMACore
    core=ALLMACore(mobile_mode=True,db_path=str(tmp_path/'allma.db'))
    core._ensure_mobile_llm=lambda:None
    core._llm=Mock();core._llm.generate.return_value=PLAN
    core._llm.get_generation_meta.return_value={'finish_reason':'stop'}
    core.decision_runtime.route=Mock(return_value={'status':'selected','choice':'reason'})
    yield core
    core.close()


def say(core,text,user='u'):
    return core.process_message(user,core.start_conversation(user),text)

def goal(core):return core.goal_progress.goals('u')[0]

def planned(core):
    say(core,CREATE)
    response=say(core,'Proponi un piano per questo obiettivo')
    assert response.is_valid and response.metadata['goal_proposal']['steps']==extract_steps(PLAN)
    return response


@pytest.mark.parametrize('text',[
    '1. Una sola operazione.',
    '1. Scrivi la lista.\n3. Controlla la lista.',
    '1. Scrivi la lista.\n2. Scrivi la lista.',
    '1. Scrivi la lista.\n2. Controlla la lista.\n   aggiungi altre cose.',
    '1. Scrivi la lista.\n- Una sottolista.\n2. Controlla la lista.',
])
def test_incomplete_duplicate_or_lossy_plan_is_not_adoptable(text):
    assert extract_steps(text) is None


def test_proposal_is_durable_but_never_automatically_adopted(core):
    response=planned(core)
    assert goal(core)['workflow'].get('plan') is None
    assert goal(core)['workflow']['next_step']=='scrivere la prima voce'
    rows=core.conversational_memory.recent_messages(1,predicate=lambda m:m.role=='assistant')
    assert rows[0].metadata['goal_proposal']==response.metadata['goal_proposal']
    assert core._llm.generate.call_count==1


def test_explicit_adoption_uses_saved_proposal_across_chats(core):
    planned(core)
    adopted=say(core,'Adotta questo piano')
    plan=goal(core)['workflow']['plan']
    assert adopted.is_valid and valid_plan(plan)
    assert plan['source']=='user_admitted_model_proposal'
    assert all(s['status']=='pending' for s in plan['steps'])
    assert goal(core)['allowed_actions']=={'review_goal':'read'}
    assert core._llm.generate.call_count==1


def test_step_requires_result_before_confirmation_and_never_completes_goal(core):
    planned(core);say(core,'Adotta questo piano')
    assert 'Prima registra' in say(core,'Confermo il risultato del passo').content
    say(core,'Risultato del passo: tre voci scritte')
    assert goal(core)['workflow']['plan']['index']==0
    say(core,'Confermo il risultato del passo')
    assert goal(core)['workflow']['plan']['index']==1
    say(core,'Risultato del passo: tutte le voci controllate')
    say(core,'Confermo il risultato del passo')
    g=goal(core)
    assert g['status']=='active' and g['workflow']['verification'] is None
    assert g['workflow']['plan']['index']==2
    assert 'criterio complessivo' in say(core,'Quali sono i miei obiettivi?').content


def test_step_rejection_keeps_position_and_corrected_feedback(core):
    planned(core);say(core,'Adotta questo piano')
    say(core,'Risultato del passo: lista scritta')
    say(core,'Risultato del passo sbagliato: mancava una voce')
    plan=goal(core)['workflow']['plan']
    assert plan['index']==0 and plan['steps'][0]['status']=='pending'
    assert goal(core)['workflow']['outcomes']['rejected']==1
    assert 'mancava una voce' in goal(core)['workflow']['progress']


def test_changed_task_invalidates_proposal_and_accepted_plan(core):
    planned(core)
    say(core,'Criterio obiettivo: quattro voci controllate')
    assert 'Non trovo una proposta' in say(core,'Adotta questo piano').content
    core._llm.generate.return_value=PLAN
    say(core,'Proponi un piano per questo obiettivo');say(core,'Adotta questo piano')
    say(core,'Criterio obiettivo: cinque voci controllate')
    g=goal(core)
    assert g['workflow']['plan']['status']=='needs_review'
    assert not g['workflow']['next_step']
    assert 'Non c’è un passo attivo' in say(core,'Risultato del passo: dichiarazione tardiva').content


def test_generated_or_quoted_adoption_is_not_a_user_control(core):
    planned(core)
    core._llm.generate.return_value='Puoi valutare il piano proposto.'
    say(core,'Nel racconto un personaggio dice «Adotta questo piano».')
    assert goal(core)['workflow'].get('plan') is None


def test_altered_or_other_users_proposal_is_not_admitted(core):
    planned(core)
    row=core.conversational_memory.messages[-1]
    assert selection(row,'other',goal(core)['id'],goal(core)['workflow']['revision']) is None
    row.content='Un testo diverso dalla proposta salvata.'
    core.conversational_memory.save_memory()
    assert 'Non trovo una proposta' in say(core,'Adotta questo piano').content
    assert goal(core)['workflow'].get('plan') is None


def test_plan_commit_ack_recovery_cannot_advance_step_twice(core):
    planned(core);say(core,'Adotta questo piano');say(core,'Risultato del passo: lista scritta')
    with patch.object(core.delivery_updates,'_ack',side_effect=OSError('synthetic ack failure')):
        result=say(core,'Confermo il risultato del passo')
    assert result.is_valid and goal(core)['workflow']['plan']['index']==1
    core.delivery_updates.recover(synchronize=True)
    assert goal(core)['workflow']['plan']['index']==1


def test_plan_step_and_source_survive_reload(core):
    planned(core);say(core,'Adotta questo piano');say(core,'Risultato del passo: prima stesura')
    fresh=GoalProgress(ActionAuthority(CognitiveStateStore(core.db_path)))
    wf=fresh.goals('u')[0]['workflow']
    assert wf['plan']['steps'][0]['status']=='awaiting_confirmation'
    assert wf['plan']['adopted_by']['source']=='user_report'


def test_old_planning_adapter_never_invents_durations_or_claims_plan():
    from allma_model.core.planning_adapter import PlanningSystemAdapter
    adapter=PlanningSystemAdapter()
    result=adapter.process('Pianifica il progetto.',{})
    assert result['has_plan'] is False and result['tasks']==[] and result['timeline'] is None
    assert adapter.process('Suona il pianoforte',{})=={}


def test_newer_failed_attempt_never_silently_adopts_an_older_plan(core):
    planned(core)
    core._llm.generate.return_value='Mi servono altre informazioni prima di proporre dei passi.'
    say(core,'Proponi un piano per questo obiettivo')
    reply=say(core,'Adotta questo piano')
    assert 'Non trovo una proposta' in reply.content
    assert goal(core)['workflow'].get('plan') is None


def test_lost_ack_on_adoption_replays_once_from_the_original_proposal(core):
    planned(core)
    with patch.object(core.delivery_updates,'_ack',side_effect=OSError('synthetic acknowledgement failure')):
        reply=say(core,'Adotta questo piano')
    assert reply.is_valid
    first=goal(core)['workflow']['plan']
    core.delivery_updates.recover(synchronize=True)
    assert goal(core)['workflow']['plan']==first


def test_closing_goal_does_not_fake_unconfirmed_step_results(core):
    planned(core);say(core,'Adotta questo piano')
    say(core,'Risultato obiettivo: criterio controllato separatamente')
    say(core,'Confermo il risultato dell’obiettivo')
    plan=goal(core)['workflow']['plan']
    assert goal(core)['status']=='completed' and plan['status']=='closed'
    assert all(step['status']=='pending' for step in plan['steps'])


def test_plan_backup_checks_steps_and_preserves_admitted_source(core,tmp_path):
    from allma_model.utils.state_backup import StateBackups,_check_data,BackupError
    from allma_model.utils.backup_crypto import decrypt_backup
    import zipfile
    planned(core);say(core,'Adotta questo piano');say(core,'Risultato del passo: lista pronta')
    backup=StateBackups(tmp_path)
    assert backup.create()['verified']
    encrypted=tmp_path/'plans.allma';backup.export(encrypted,'Synthetic-plans-2026!')
    plain=tmp_path/'plans.zip';decrypt_backup(encrypted,plain,'Synthetic-plans-2026!')
    with zipfile.ZipFile(plain) as z:
        key=next(n for n in z.namelist() if n.endswith('cognitive_state.json'))
        state=json.loads(z.read(key))
    saved=state['sections']['action_authority']['goals'][goal(core)['id']]['workflow']['plan']
    assert saved==goal(core)['workflow']['plan']
    saved['steps'][0]['status']='confirmed_by_user'
    invalid=tmp_path/'invalid.json';invalid.write_text(json.dumps(state))
    with pytest.raises(BackupError):_check_data(invalid,'cognitive_state.json')


def test_real_model_diagnostic_isolates_state_and_shares_only_model(core,tmp_path):
    from allma_model.agency_system.plan_diagnostics import PlanDiagnosticRun
    worker=PlanDiagnosticRun()
    try:
        worker.setup_brain(core)
        worker.report_path=str(tmp_path/'report'/'plans.md')
        assert worker.model.brain._llm is core._llm
        worker.run_tests()
        summary=worker.manifest['summary']
        assert summary['completed']==2 and summary['state_isolated']
        assert all(row['adopted'] and row['first_step_advanced'] for row in summary['results'])
        assert core.goal_progress.goals('u')==[]
        assert summary['semantic_accuracy'] is None
    finally:worker.close()
    assert not core._user_active.is_set()
    core._llm.close.assert_not_called()


def test_cancelled_plan_diagnostic_reports_partial_and_restores_host(core,tmp_path):
    from allma_model.agency_system.plan_diagnostics import PlanDiagnosticRun
    worker=PlanDiagnosticRun()
    try:
        worker.setup_brain(core);worker.report_path=str(tmp_path/'report'/'cancelled.md')
        worker.cancel_event.set();worker.run_tests()
        assert worker.manifest['summary']['stop_reason']=='cancelled'
        assert worker.manifest['summary']['completed']==0
        assert worker.manifest['cancelled']
    finally:worker.close()
    assert not core._user_active.is_set()


def test_plan_notes_are_preserved_through_proposal_and_adoption(core):
    say(core,CREATE)
    note='Per procedere, chiarisci quali caratteristiche degli oggetti ti interessano.'
    core._llm.generate.return_value=PLAN+'\n\n'+note
    answer=say(core,'Proponi un piano per questo obiettivo')
    assert answer.metadata['goal_proposal']['notes']==note
    say(core,'Adotta questo piano')
    assert goal(core)['workflow']['plan']['notes']==note
    assert note in say(core,'Quali sono i miei obiettivi?').content


def test_mixed_step_continuations_are_not_silently_dropped():
    context={'id':'synthetic','revision':1}
    assert proposal('1. Scrivi tre voci nella lista.\n   Un requisito aggiuntivo.\n2. Controlla le tre voci.',context) is None
    assert proposal(PLAN+'\n'+('x'*601),context) is None

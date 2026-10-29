from copy import deepcopy
from pathlib import Path
from unittest.mock import Mock,patch
import json

import pytest

from allma_model.agency_system.plan_review import review,requirements
from allma_model.learning_system.plan_experience import context,assessment,find
from allma_model.learning_system.plan_experience_diagnostics import failed,create,say as task_say
from allma_model.agency_system.plan_review_diagnostics import CASES

BAD_REAL = [
 'Raccogliere tre elementi distinti e verificabili (es. un oggetto fisico, un documento digitale o una fotografia).',
 'Verificare che ogni elemento soddisfi il criterio di distinzione (diversi da quelli precedenti).',
 'Controllare la presenza di almeno uno dei tre elementi nella lista finale.',
 'Confermare o correggere l’inclusione degli elementi mancanti nel risultato finale.']

BAD = [
 ('tre oggetti distinti controllati',BAD_REAL),
 ('tre oggetti controllati',['Prepara gli oggetti.','Controlla solo un oggetto.']),
 ('cinque documenti verificati',['Raccogli i documenti.','Verifica due documenti.']),
 ('6 voci controllate',['Prepara le voci richieste.','Controlla almeno due delle sei voci nella lista finale.']),
 ('four documents checked',['Gather the documents.','Check only one document.']),
 ('3 objects checked',['Collect the objects.','Check at least one of the three objects in the final list.']),
 ('otto file verificati',['Raccogli i file.','Verifica almeno tre file.']),
 ('sette elementi controllati',['Prepara gli elementi.','Controlla due elementi.']),
 ('9 oggetti controllati',['Prepara gli oggetti.','Controlla soltanto un oggetto.']),
 ('dieci documenti controllati',['Prepara i documenti.','Controlla 2 documenti nella lista definitiva.'])]

GOOD = [
 ('tre oggetti controllati',['Prepara gli oggetti.','Controlla tutti gli oggetti.']),
 ('tre oggetti controllati',['Prepara gli oggetti.','Verifica ciascuno dei tre elementi.']),
 ('tre oggetti controllati',['Controlla un oggetto.','Poi controlla tutti gli oggetti.']),
 ('tre oggetti controllati',['Controlla un oggetto.','Controlla gli altri due oggetti.']),
 ('tre oggetti controllati',['Prepara gli oggetti.','Controlla un oggetto e verifica altri due oggetti.']),
 ('tre documenti controllati',['Controlla tutti i documenti.','Verifica un documento a campione per audit finale.']),
 ('tre oggetti controllati',['Prepara gli oggetti.','Controlla un oggetto alla volta fino a verificarli tutti.']),
 ('tre oggetti controllati',['Se manca uno dei tre oggetti, aggiungilo.','Controlla tutti gli oggetti.']),
 ('tre documenti controllati',['Non limitarti a controllare un documento.','Verifica tutti i documenti.']),
 ('four documents checked',['Collect the documents.','Check all four documents.']),
 ('four documents checked',['Check one document.','Check the other three documents.']),
 ('tre oggetti controllati',['Controlla il primo oggetto.','Controlla il secondo e il terzo oggetto.']),
 ('tre documenti e due foto verificati',['Verifica tre documenti.','Verifica due foto.']),
 ('tre documenti controllati',['Verifica due foto.','Prepara una cartella.']),
 ('tre oggetti controllati',['Confronta il testo «controlla solo un oggetto».','Verifica tutti gli oggetti.']),
 ('tre oggetti controllati',['Prepara gli oggetti.','Controlla almeno 3 oggetti.']),
 ('tre oggetti controllati',['Prepara gli oggetti.','Controlla un oggetto alla volta.']),
 ('tre oggetti controllati',['Verifica due oggetti del primo gruppo.','Verifica un oggetto del secondo gruppo.']),
 ('almeno quattro documenti verificati',['Prepara i documenti.','Verifica cinque documenti.']),
 ('tre oggetti controllati',['Verifica la lista “controllare uno”.','Chiedi chiarimenti prima di procedere.'])]

UNKNOWN = [
 ('testo cortese con saluto e ringraziamento',['Scrivi un saluto.','Chiedi il motivo del ringraziamento.']),
 ('non controllare tre oggetti',['Prepara gli oggetti.','Controlla un oggetto.']),
 ('circa tre oggetti controllati',['Prepara gli oggetti.','Controlla un oggetto.']),
 ('tre giorni di controlli',['Pianifica la settimana.','Controlla un giorno.']),
 ('tre oggetti raccolti',['Raccogli un oggetto.','Mettilo sul tavolo.']),
 ('tre oggetti controllati',['Prepara gli oggetti.','Chiedi le informazioni necessarie.']),
 ('1000 oggetti controllati',['Prepara gli oggetti.','Controlla un oggetto.']),
 ('0 oggetti controllati',['Prepara gli oggetti.','Controlla un oggetto.']),
 ('«tre oggetti controllati»',['Prepara gli oggetti.','Controlla un oggetto.']),
 ('at most three objects checked',['Gather the objects.','Check one object.'])]


@pytest.mark.parametrize('group,name,criterion,fn',CASES,ids=[row[1] for row in CASES])
def test_shared_android_review_scenario(tmp_path,group,name,criterion,fn):
    path=tmp_path/name;path.mkdir();fn(path)


@pytest.mark.parametrize('criterion,steps',BAD)
def test_explicit_weaker_check_has_a_counterexample(criterion,steps):
    report=review(steps,criterion)
    assert report['status']=='needs_review'
    for f in report['findings']:
        assert f['guaranteed'] < f['required'] and f['uncovered']==f['required']-f['guaranteed']
    assert report['source']=='host_count_coverage_v1' and report['semantic_correctness_verified'] is False


@pytest.mark.parametrize('criterion,steps',GOOD)
def test_valid_partitions_loops_quotes_and_samples_are_not_blocked(criterion,steps):
    assert review(steps,criterion)['status']!='needs_review'


@pytest.mark.parametrize('criterion,steps',UNKNOWN)
def test_unknown_scope_is_not_claimed_to_be_verified(criterion,steps):
    report=review(steps,criterion)
    assert report['status']=='not_automatically_checkable' and not report['findings']
    assert report['semantic_correctness_verified'] is False


@pytest.mark.parametrize('count,subject',[(2,'cartelle'),(11,'campioni'),(17,'registri'),(27,'pacchi'),(83,'record'),(101,'samples'),(255,'files'),(999,'documenti')])
def test_new_counts_and_subjects_are_not_special_cases(count,subject):
    criterion=f'{count} {subject} checked'
    assert review(['Prepare the collection.',f'Check {count-1} {subject}.'],criterion)['status']=='needs_review'
    assert review(['Prepare the collection.',f'Check all {count} {subject}.'],criterion)['status']=='no_known_gap'


@pytest.mark.parametrize('criterion,step',[('3 files checked','Check one file.'),('4 samples checked','Check one sample.')])
def test_english_singular_and_plural_bind_to_same_subject(criterion,step):
    assert review(['Prepare the collection.',step],criterion)['status']=='needs_review'


@pytest.mark.parametrize('step,status',[
 ('Controlla almeno **uno** dei tre oggetti nella lista finale.','needs_review'),
 ('Controlla almeno _uno_ dei tre oggetti nella lista finale.','needs_review'),
 ('Verifica **tutti** gli oggetti.','no_known_gap'),
 ('Esamina il testo «controlla **uno** dei tre oggetti».','not_automatically_checkable')])
def test_emphasis_does_not_change_the_numeric_guarantee(step,status):
    assert review(['Prepara gli oggetti.',step],'tre oggetti controllati')['status']==status


def test_arithmetic_in_criterion_is_not_misread_as_a_literal_count():
    assert review(['Prepara gli oggetti.','Controlla un oggetto.'],'3*4 oggetti controllati')['status']=='not_automatically_checkable'


@pytest.fixture
def core(tmp_path,monkeypatch):
    monkeypatch.chdir(tmp_path)
    from allma_model.core.allma_core import ALLMACore
    value=ALLMACore(mobile_mode=True,db_path=str(tmp_path/'allma.db'))
    value._ensure_mobile_llm=lambda:None;value._llm=Mock()
    value._llm.get_generation_meta.return_value={'finish_reason':'stop'}
    value.decision_runtime.route=Mock(return_value={'status':'selected','choice':'reason'})
    yield value
    value.close()


def say(core,text):return core.process_message('u',core.start_conversation('u'),text)


def proposal(core):
    say(core,'Nuovo obiettivo: Lista degli oggetti\nCriterio: tre oggetti distinti controllati')
    core._llm.generate.return_value='Proposta di piano\n1. Prepara gli oggetti.\n2. Controlla almeno uno dei tre oggetti nella lista finale.'
    return say(core,'Proponi un piano per questo obiettivo')


def test_bad_plan_is_documented_but_cannot_be_adopted(core):
    response=proposal(core)
    assert response.is_valid and response.metadata['goal_plan_review']['status']=='needs_review'
    assert response.metadata['goal_proposal']
    denied=say(core,'Adotta questo piano')
    assert not denied.is_valid and 'Piano da rivedere' in denied.content
    goal=core.goal_progress.goals('u')[0]
    assert goal['workflow'].get('plan') is None and goal['workflow']['revision']==1
    assert 'learning' not in goal['workflow']
    assert denied.metadata['goal_update']['status']=='review_required'
    assert core.delivery_updates.recover(synchronize=True)['pending']==0
    core._llm.generate.assert_called_once()


def test_counterexample_is_reused_for_new_proposal_without_inventing_an_experience(core):
    proposal(core);say(core,'Adotta questo piano')
    core._llm.generate.return_value='1. Prepara i tre oggetti.\n2. Verifica tutti gli oggetti della lista.'
    response=say(core,'Proponi un piano per questo obiettivo')
    assert 'previous_plan_gap' in core._llm.generate.call_args.kwargs['prompt']
    assert response.metadata['goal_plan_review']['status']=='no_known_gap'
    assert not response.metadata['plan_experience']['case_ids']
    assert say(core,'Adotta questo piano').is_valid
    assert core._llm.generate.call_count==2


def test_replay_after_review_required_checkpoint_keeps_goal_unadopted(core):
    proposal(core)
    with patch.object(core.delivery_updates,'_ack',side_effect=OSError('synthetic lost ack')):
        say(core,'Adotta questo piano')
    before=deepcopy(core.goal_progress.goals('u')[0])
    assert core.delivery_updates.recover(synchronize=True)['pending']==0
    assert core.goal_progress.goals('u')[0]==before


def test_review_is_recomputed_even_if_saved_verdict_is_tampered(core):
    proposal(core)
    record=core.conversational_memory.messages[-1]
    record.metadata['goal_plan_review']['status']='no_known_gap'
    core.conversational_memory.save_memory()
    assert not say(core,'Adotta questo piano').is_valid


def test_criterion_correction_invalidates_old_counterexample_and_proposal(core):
    proposal(core)
    say(core,'Criterio obiettivo: un oggetto controllato')
    assert 'Non trovo una proposta' in say(core,'Adotta questo piano').content
    core._llm.generate.return_value='1. Prepara un oggetto.\n2. Controlla un oggetto.'
    answer=say(core,'Proponi un piano per questo obiettivo')
    assert 'previous_plan_gap' not in core._llm.generate.call_args.kwargs['prompt']
    assert answer.metadata['goal_plan_review']['status']=='no_known_gap'


def bridge(path):
    f,lesson=failed(path)
    title='Passaporto prima della partenza'
    f.apply('Nuovo obiettivo: '+title+'\nCriterio: passaporto e biglietti validi prima della partenza')
    task_say(f,title,'Risultato obiettivo: passaporto e biglietti controllati')
    task_say(f,title,'Confermo il risultato dell’obiettivo')
    target={'id':'unseen','user_id':'u','objective':'Controllare passaporto e biglietti prima della partenza',
            'workflow':{'criterion':'passaporto e biglietti validi prima della partenza'}}
    assert not any(r['id']==lesson for r in context(f.tracker.goals('u'),target))
    task_say(f,title,'Lezione utile: '+lesson)
    return f,lesson,title,target


def test_experience_creates_a_new_retrieval_route_between_different_vocabularies(tmp_path):
    f,lesson,title,target=bridge(tmp_path)
    results=context(f.tracker.goals('u'),target)
    row=next(r for r in results if r['id']==lesson)
    assert row['retrieval']['kind']=='confirmed_task_bridge'
    assert row['retrieval']['task']==title
    assert row['supporting_tasks']==1 and row['status']=='candidate'


@pytest.mark.parametrize('command',['Lezione non utile: {id}','Riapri obiettivo','Criterio obiettivo: biglietti annullati'])
def test_withdrawn_or_corrected_route_is_no_longer_used(tmp_path,command):
    f,lesson,title,target=bridge(tmp_path)
    if command.startswith('Criterio'):task_say(f,title,'Riapri obiettivo')
    task_say(f,title,command.format(id=lesson))
    assert not any(r['id']==lesson for r in context(f.tracker.goals('u'),target))


def test_unreviewed_model_output_and_repeated_feedback_cannot_create_more_routes(tmp_path):
    f,lesson,title,target=bridge(tmp_path)
    for _ in range(4):task_say(f,title,'Lezione utile: '+lesson)
    results=context(f.tracker.goals('u'),target)
    row=next(r for r in results if r['id']==lesson)
    assert row['supporting_tasks']==1
    alien=deepcopy(target);alien['user_id']='other'
    assert context(f.tracker.goals('u'),alien)==[]


def test_comparison_uses_same_goal_and_seed_and_only_four_model_calls(core,tmp_path):
    from allma_model.agency_system.plan_comparison import PlanReviewComparisonRun
    def generated(**kwargs):
        return ('1. Prepara gli elementi richiesti.\n2. Verifica tutti gli elementi.' if '"requirements"' in kwargs['prompt']
                else '1. Prepara gli oggetti richiesti.\n2. Controlla solo un oggetto.')
    core._llm.generate.side_effect=generated
    worker=PlanReviewComparisonRun()
    try:
        worker.setup_brain(core);worker.report_path=str(tmp_path/'comparison.md');worker.run_tests()
        summary=worker.manifest['summary'];rows=summary['results']
        assert summary['completed']==4 and summary['host_review_in_both_arms']
        assert core._llm.generate.call_count==4
        assert all(call.kwargs['max_tokens']<=192 and call.kwargs['thought_budget']<=64 for call in core._llm.generate.call_args_list)
        for pair in ('objects','documents'):
            a,b=[r for r in rows if r['pair']==pair]
            assert a['goal_id']==b['goal_id'] and a['seed']==b['seed'] and a['goal_revision']==b['goal_revision']==1
        assert core.goal_progress.goals('u')==[]
        assert summary['semantic_accuracy'] is None
    finally:worker.close()
    assert not core._user_active.is_set()

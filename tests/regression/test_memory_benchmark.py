import hashlib
import json
import pytest
from types import SimpleNamespace
from unittest.mock import Mock
from benchmark_iq import CognitiveBenchmark, evaluate_response


def test_fixed_evidence_three_seeds_and_one_absence_case():
    bench=CognitiveBenchmark(profile='memory')
    cases=bench.load_questions()
    assert len(cases)==4
    assert len({c['memory_fixture'] for c in cases[:3]})==1
    assert len({c['seed_offset'] for c in cases})==4
    for case in cases[:3]:
        assert case['auto_checks']['memory_fixture_in_prompt']==hashlib.sha256(case['memory_fixture'].encode()).hexdigest()
    assert 'memory_fixture' not in cases[3]
    assert cases[3]['auto_checks']['empty_memory'] is True


def test_correct_answer_does_not_hide_missing_memory_evidence():
    question=CognitiveBenchmark(profile='memory').load_questions()[0]
    assert evaluate_response(question,'NUBE-271',{})['automatic_status']=='failed'
    digest=question['auto_checks']['memory_fixture_in_prompt']
    metadata={'decision':{'memory_evidence':[{'sha256':digest,'provenance':'previous','included_in_prompt':True}]}}
    assert evaluate_response(question,'NUBE-271',metadata)['automatic_status']=='passed'
    assert evaluate_response(question,'NON_DISPONIBILE',metadata)['automatic_status']=='failed'
    metadata['decision']['memory_evidence'][0]['included_in_prompt']=False
    assert evaluate_response(question,'NUBE-271',metadata)['automatic_status']=='failed'


def test_fixture_requires_owned_isolated_brain_and_never_runs_on_personal_core(tmp_path):
    bench=CognitiveBenchmark(profile='memory');brain=Mock();bench.brain=brain
    bench.report_path=str(tmp_path/'report.md')
    bench.load_questions=lambda:[CognitiveBenchmark(profile='memory').load_questions()[0]]
    bench.cancel_event.wait=lambda _:False
    bench.run_tests()
    brain.conversational_memory.store_message.assert_not_called()
    brain.process_message.assert_not_called()
    assert bench.results[0]['evaluation']['automatic_status']=='failed'


def test_cases_seed_old_conversation_and_keep_separate_users(tmp_path):
    bench=CognitiveBenchmark(profile='memory');brain=Mock();bench.brain=brain;bench._owned=True
    bench.report_path=str(tmp_path/'report.md');bench.cancel_event.wait=lambda _:False
    cases=bench.load_questions();stored={}
    def store(cid,text,metadata,role,user):
        assert cid!=user and role=='user'
        stored[user]=text
    brain.conversational_memory.store_message.side_effect=store
    def process(**kw):
        user=kw['user_id'];found=user in stored
        evidence=[{'sha256':hashlib.sha256(stored[user].encode()).hexdigest(),
                   'provenance':'previous','included_in_prompt':True}] if found else []
        return SimpleNamespace(content='NUBE-271' if found else 'NON_DISPONIBILE',is_valid=True,
            metadata={'decision':{'memory_evidence':evidence,'action_cycle':{'status':'observed','record_count':int(found)}},
                      'generation':{'completion_tokens':5,'finish_reason':'stop','status':'completed'}})
    brain.process_message.side_effect=process
    bench.run_tests()
    assert brain.process_message.call_count==4
    assert brain.conversational_memory.store_message.call_count==3
    calls=brain.process_message.call_args_list
    assert len({c.kwargs['user_id'] for c in calls})==4
    assert [c.kwargs['context']['benchmark_seed'] for c in calls]==[bench.seed+c['seed_offset'] for c in cases]
    assert all(c.kwargs['context']['benchmark_thought_budget']==128 for c in calls)
    assert all(r['evaluation']['automatic_status']=='passed' for r in bench.results)


@pytest.mark.parametrize('profile',['memory','memory_contract','memory_recall','memory_lifecycle','memory_personal'])
def test_benchmark_fixtures_reach_real_pipeline_without_contaminating_absence_case(tmp_path,monkeypatch,profile):
    from allma_model.core.allma_core import ALLMACore
    monkeypatch.chdir(tmp_path)
    (tmp_path/'isolated').mkdir()
    brain=ALLMACore(mobile_mode=True,db_path=str(tmp_path/'isolated'/'core.db'))
    brain._ensure_mobile_llm=lambda:None
    brain._llm=Mock()
    brain._llm.generate.side_effect=lambda **kw:'NUBE-271' if 'NUBE-271' in kw['prompt'] else 'NON_DISPONIBILE'
    brain._llm.get_generation_meta.return_value={'finish_reason':'stop','completion_tokens':5}
    bench=CognitiveBenchmark(profile=profile);bench.brain=brain;bench._owned=True
    brain._capture_synthetic_candidates=True
    bench.report_path=str(tmp_path/'report.md');bench.cancel_event.wait=lambda _:False
    try:
        bench.run_tests()
        assert all(row['evaluation']['automatic_status']=='passed' for row in bench.results)
        assert len(bench.results)==({'memory_lifecycle':7,'memory_personal':6}.get(profile,4))
        if profile in ('memory_recall','memory_lifecycle','memory_personal'):
            brain._llm.generate.assert_not_called()
            assert all(row['evaluation']['model_answer_valid'] is None for row in bench.results)
        else:
            assert all('before_pipeline' in row['steps'][0]['candidate_diagnostic'] for row in bench.results)
        if profile == 'memory_contract':
            prompts=[call.kwargs['prompt'] for call in brain._llm.generate.call_args_list]
            assert 'Le dichiarazioni dell’utente non sono fatti verificati.' in prompts[0]
            assert 'puoi riferirlo senza certificarne la verità esterna' in prompts[1]
            assert ['NUBE-271' in prompt for prompt in prompts]==[True,True,False,False]
    finally:
        bench.close()


def test_memory_contract_pairs_keep_seed_input_budget_and_checks():
    bench=CognitiveBenchmark(profile='memory_contract')
    cases=bench.load_questions()
    assert len(cases)==4
    assert [c['memory_variant'] for c in cases]==['baseline','attributed','attributed','baseline']
    for a,b in zip(cases[::2],cases[1::2]):
        for key in ('pair_seed','question','total_budget','thought_budget','auto_checks'):
            assert a[key]==b[key]
    assert 'memory_fixture' in cases[0] and 'memory_fixture' not in cases[2]


def test_absence_format_check_is_not_relaxed():
    question=next(c for c in CognitiveBenchmark(profile='memory').load_questions() if c['id']=='MF4')
    meta={'decision':{'action_cycle':{'status':'observed','record_count':0}}}
    assert evaluate_response(question,'NON DISPONIBILE',meta)['automatic_status']=='failed'
    assert evaluate_response(question,'NON_DISPONIBILE',meta)['automatic_status']=='passed'



def test_native_recall_profile_has_distinct_values_and_strict_literal_checks():
    cases=CognitiveBenchmark(profile='memory_recall').load_questions()
    assert [case['auto_checks']['literal_exact_answer'] for case in cases]==['NUBE-271','vEnTo_004','000015','NON_DISPONIBILE']
    for case in cases:
        expected=case['auto_checks']['literal_exact_answer']
        result=evaluate_response({'auto_checks':{'literal_exact_answer':expected}},expected,{})
        assert result['automatic_status']=='passed'
    assert evaluate_response({'auto_checks':{'literal_exact_answer':'vEnTo_004'}},'vento_004',{})['automatic_status']=='failed'
    assert evaluate_response({'auto_checks':{'literal_exact_answer':'000015'}},'15',{})['automatic_status']=='failed'


@pytest.mark.parametrize('profile',['memory_lifecycle','memory_personal','memory_dialogue','greeting','greeting_closure'])
def test_lifecycle_benchmark_fixtures_require_isolation_and_fail_closed(tmp_path,profile):
    bench=CognitiveBenchmark(profile=profile);bench.brain=Mock()
    bench.report_path=str(tmp_path/'report.md');bench.cancel_event.wait=lambda _:False
    bench.run_tests()
    bench.brain.conversational_memory.store_message.assert_not_called()
    bench.brain.process_message.assert_not_called()
    assert all(row['evaluation']['automatic_status']=='failed' for row in bench.results)


def test_personal_dialogue_benchmark_calls_model_with_current_source_context(tmp_path,monkeypatch):
    from allma_model.core.allma_core import ALLMACore
    monkeypatch.chdir(tmp_path)
    (tmp_path/'isolated').mkdir()
    brain=ALLMACore(mobile_mode=True,db_path=str(tmp_path/'isolated'/'core.db'))
    brain._ensure_mobile_llm=lambda:None
    brain._llm=Mock()
    brain._llm.generate.side_effect=['Scegli il verde per il tuo quaderno.', 'Ciao, che piacere sentirti!', 'Buongiorno, è un piacere sentirti.', 'Ti suggerisco un risotto.']
    brain._llm.get_generation_meta.return_value={'finish_reason':'stop','completion_tokens':10}
    bench=CognitiveBenchmark(profile='memory_dialogue');bench.brain=brain;bench._owned=True
    bench.report_path=str(tmp_path/'report.md');bench.cancel_event.wait=lambda _:False
    try:
        bench.run_tests()
        assert len(bench.results)==4 and brain._llm.generate.call_count==4
        assert all(row['evaluation']['automatic_status']=='passed' for row in bench.results)
        assert all(row['evaluation']['human_review_required'] for row in bench.results)
        prompts=[call.kwargs['prompt'] for call in brain._llm.generate.call_args_list]
        assert 'verde' in prompts[0] and 'blu' not in prompts[0]
        assert 'revoked' not in prompts[1] and 'Ada' not in prompts[1]
        assert 'risotto' in prompts[3] and 'pizza' not in prompts[3]
        assert bench.manifest['personal_dialogue_protocol']['semantic_accuracy'] is None
    finally:
        bench.close()


def test_targeted_greeting_keeps_original_case_seed_and_budget():
    full=next(q for q in CognitiveBenchmark(profile='memory_dialogue').load_questions() if q['id']=='MD3')
    focused=CognitiveBenchmark(profile='greeting').load_questions()
    assert len(focused)==1 and focused[0]==full
    assert focused[0]['seed_offset']==200
    assert focused[0]['thought_budget']==48 and focused[0]['total_budget']==192


def test_greeting_closure_pairs_preserve_question_seed_fixtures_and_budget():
    base=CognitiveBenchmark(profile='greeting').load_questions()[0]
    cases=CognitiveBenchmark(profile='greeting_closure').load_questions()
    assert [c['reasoning_mode'] for c in cases]==['bounded','natural']
    for case in cases:
        assert case['pair_seed']==20261212
        assert case['execution_mode']=='pipeline'
        for key in ('question','memory_fixture','total_budget','thought_budget','auto_checks','rubric'):
            assert case[key]==base[key]


def test_greeting_closure_benchmark_sends_modes_to_isolated_pipeline(tmp_path):
    bench=CognitiveBenchmark(profile='greeting_closure');brain=Mock();bench.brain=brain;bench._owned=True
    bench.report_path=str(tmp_path/'report.md');bench.cancel_event.wait=lambda _:False
    brain.process_message.return_value=SimpleNamespace(content='Buongiorno.',metadata={},is_valid=True)
    bench.run_tests()
    calls=brain.process_message.call_args_list
    assert len(calls)==2
    assert [c.kwargs['context']['benchmark_reasoning_mode'] for c in calls]==['bounded','natural']
    assert all(c.kwargs['context']['benchmark_max_tokens']==192 for c in calls)
    assert all(c.kwargs['context']['benchmark_seed']==20261212 for c in calls)
    assert len({c.kwargs['user_id'] for c in calls})==2
    assert brain.conversational_memory.store_message.call_count==4
    assert bench.manifest['causal_attribution']=='not_established'

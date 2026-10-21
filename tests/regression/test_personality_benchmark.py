from unittest.mock import Mock
from benchmark_iq import CognitiveBenchmark,evaluate_response


def test_personality_benchmark_refuses_personal_core(tmp_path):
    bench=CognitiveBenchmark(profile='personality');brain=Mock();bench.brain=brain
    bench.report_path=str(tmp_path/'report.md');bench.cancel_event.wait=lambda _:False
    bench.run_tests()
    brain.process_message.assert_not_called()
    assert len(bench.results)==6
    assert all(r['evaluation']['automatic_status']=='failed' for r in bench.results)


def test_personality_benchmark_checks_canonical_state_reload_and_actual_prompt(tmp_path,monkeypatch):
    from allma_model.core.allma_core import ALLMACore
    from tests.regression.test_core_response import MemoryProbeEngine
    monkeypatch.chdir(tmp_path);(tmp_path/'isolated').mkdir()
    brain=ALLMACore(mobile_mode=True,db_path=str(tmp_path/'isolated'/'core.db'))
    brain._ensure_mobile_llm=lambda:None
    brain._llm=MemoryProbeEngine('La luce del sole cambia direzione nelle gocce e si separa nei colori.')
    brain._llm.generate=Mock(wraps=brain._llm.generate)
    bench=CognitiveBenchmark(profile='personality');bench.brain=brain;bench._owned=True
    brain._capture_synthetic_candidates=True
    bench.report_path=str(tmp_path/'report.md');bench.cancel_event.wait=lambda _:False
    try:
        bench.run_tests()
        assert len(bench.results)==6
        assert all(r['evaluation']['automatic_status']=='passed' for r in bench.results)
        brain._llm.generate.assert_called_once()
        assert not brain.coalescence_processor.expression_view('user_default')['preferences']
        last=bench.results[-1];meta=last['steps'][-1]['metadata']
        assert meta['personality_expression']['instruction_received'] is True
        assert 'Preferisco risposte brevi.' not in str(brain._llm.messages)
        assert meta['personality_expression']['values']=={'verbosity':'brief','questions':'restrained'}
        assert bench.manifest['personality_protocol']['general_reliability_established'] is False
        # Missing telemetry cannot pass the model-context check.
        case=bench.load_questions()[-1]
        assert evaluate_response(case,last['response'],{})['automatic_status']=='failed'
    finally:
        bench.close()


def test_style_context_alone_cannot_hide_truncated_or_missing_generation():
    case=CognitiveBenchmark(profile='personality').load_questions()[-1]
    meta={'personality_expression':{'values':{'verbosity':'brief','questions':'restrained'},'instruction_received':True},
          'generation':{'status':'truncated_answer','finish_reason':'length'}}
    assert evaluate_response(case,'Risposta interrotta a metà',meta)['automatic_status']=='failed'
    meta['generation']={'status':'completed','finish_reason':'stop'}
    assert evaluate_response(case,'Una risposta completa.',meta)['automatic_status']=='passed'


def test_outcome_protocol_is_isolated_and_compares_fresh_histories_with_equal_seed(tmp_path,monkeypatch):
    from allma_model.core.allma_core import ALLMACore
    from tests.regression.test_core_response import MemoryProbeEngine
    monkeypatch.chdir(tmp_path);(tmp_path/'isolated').mkdir()
    class Probe(MemoryProbeEngine):
        def generate(self,**kw):
            self.options=kw
            question=self.messages[-1]['content']
            for word,answer in [('ghiaccio','Il ghiaccio galleggia perché è meno denso dell’acqua.'),
                                ('foglie','La clorofilla contribuisce al colore verde delle foglie.'),
                                ('limone','L’acido citrico contribuisce al sapore acido del limone.')]:
                if word in question:return answer
            return 'La luce si propaga più velocemente del suono.'
        def get_generation_meta(self,request):
            return {'finish_reason':'stop','seed':self.options['seed'],'max_tokens':self.options['max_tokens'],
                    'reasoning_budget':48,'answer_budget':144,'temperature':self.options['temperature'],
                    'top_p':self.options['top_p']}
    brain=ALLMACore(mobile_mode=True,db_path=str(tmp_path/'isolated'/'core.db'))
    brain._ensure_mobile_llm=lambda:None;brain._llm=Probe('unused');brain._capture_synthetic_candidates=True
    brain._llm.generate=Mock(wraps=brain._llm.generate)
    process=brain.process_message;brain.process_message=Mock(wraps=process)
    bench=CognitiveBenchmark(profile='personality_feedback');bench.brain=brain;bench._owned=True
    bench.report_path=str(tmp_path/'report.md');bench.cancel_event.wait=lambda _:False
    try:
        bench.run_tests()
        assert len(bench.results)==1
        row=bench.results[0]
        assert row['evaluation']['automatic_status']=='passed',row['evaluation']
        assert brain._llm.generate.call_count==5
        calls=brain.process_message.call_args_list
        assert len(calls)==8
        assert calls[0].kwargs['message']==calls[7].kwargs['message']
        assert calls[0].kwargs['context']['benchmark_seed']==calls[7].kwargs['context']['benchmark_seed']
        assert calls[0].kwargs['conversation_id']!=calls[7].kwargs['conversation_id']
        assert calls[0].kwargs['conversation_id']!=calls[1].kwargs['conversation_id']
        assert len({calls[i].kwargs['conversation_id'] for i in (1,3,5)})==3
        assert all(calls[i].kwargs['conversation_id']==calls[i+1].kwargs['conversation_id'] for i in (1,3,5))
        assert len({c.kwargs['user_id'] for c in calls})==1
        assert not brain.coalescence_processor.expression_view('user_default')['outcome_learning']['contexts']
        # High temperature after the third training answer still permits its
        # native assessment, then stops before the fifth model inference.
        brain._llm.generate.reset_mock()
        bench._conditions=lambda:{'battery_temp_celsius':41.6 if brain._llm.generate.call_count>=4 else 38.}
        bench.run_tests()
        assert brain._llm.generate.call_count==4
        assert bench.manifest['stop_reason']=='thermal_pause'
        assert len(bench.results[0]['steps'])==7
        final=bench.results[0]['steps'][-1]['metadata']
        assert final['personality_expression']['outcome_learning']['strong_feedback']==3
        assert final['source']=='personality_response_feedback'
    finally:bench.close()


def test_outcome_protocol_refuses_to_mutate_the_personal_core(tmp_path):
    bench=CognitiveBenchmark(profile='personality_feedback');bench.brain=Mock()
    bench.report_path=str(tmp_path/'report.md');bench.cancel_event.wait=lambda _:False
    bench.run_tests()
    bench.brain.process_message.assert_not_called()
    assert bench.results[0]['evaluation']['automatic_status']=='failed'


def test_synthetic_utility_stops_without_extra_inference_when_delivery_is_not_assessable(tmp_path,monkeypatch):
    from allma_model.core.allma_core import ALLMACore
    from tests.regression.test_core_response import MemoryProbeEngine
    monkeypatch.chdir(tmp_path);(tmp_path/'isolated').mkdir()
    brain=ALLMACore(mobile_mode=True,db_path=str(tmp_path/'isolated'/'core.db'))
    brain._ensure_mobile_llm=lambda:None
    brain._llm=MemoryProbeEngine(' '.join('termine'+str(i) for i in range(110)))
    brain._llm.generate=Mock(wraps=brain._llm.generate)
    bench=CognitiveBenchmark(profile='personality_feedback');bench.brain=brain;bench._owned=True
    bench.report_path=str(tmp_path/'report.md');bench.cancel_event.wait=lambda _:False
    try:
        bench.run_tests()
        assert brain._llm.generate.call_count==2
        assert bench.manifest['stop_reason']=='unassessable_training_response'
        assert len(bench.results[0]['steps'])==3
        assert bench.results[0]['evaluation']['automatic_status']=='failed'
        assert not brain.coalescence_processor.expression_view('user_default')['outcome_learning']['contexts']
    finally:bench.close()

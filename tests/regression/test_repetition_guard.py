from types import SimpleNamespace
from unittest.mock import Mock
import pytest
from allma_model.utils.repetition_guard import repetition_start, completion_with_compat, memory_display
from allma_model.utils.generation_budget import bounded_completion
from allma_model.utils.answer_stream import AnswerStream


@pytest.mark.parametrize('text', ['Una risposta. '+ 'ghiandole '*12, 'La stessa frase. '*5, 'È un ciclo ripetuto '*5])
def test_lexical_loops_are_detected_without_topic_keywords(text):
    assert repetition_start(text) is not None


@pytest.mark.parametrize('text', ['La membrana e le branchie hanno funzioni diverse.',
    'no no no', '0 0 0 0 0 0 0 0', '```\n'+ 'funzione '*12+'\n```',
    'Il mare cambia. Il mare può calmarsi. Il mare può agitarsi.'])
def test_legitimate_short_repetition_and_code_are_not_loops(text):
    assert repetition_start(text) is None


def test_compatibility_keeps_penalty_when_window_kwarg_is_unsupported():
    seen=[]
    def api(prompt, *, repeat_penalty):
        seen.append(repeat_penalty)
        return 'done'
    assert completion_with_compat(api,'prompt',{'repeat_penalty':1.1,'repeat_last_n':128})=='done'
    assert seen==[1.1]


def test_unrelated_type_error_is_not_retried_or_swallowed():
    api=Mock(side_effect=TypeError('bad tensor'))
    with pytest.raises(TypeError,match='bad tensor'):
        completion_with_compat(api,'prompt',{'repeat_penalty':1.1})
    api.assert_called_once()


def test_bounded_iterator_stops_answer_loop_early_closes_and_marks_stop():
    consumed=[];closed=[];calls=[]
    def generate(prompt, **kwargs):
        calls.append(kwargs)
        try:
            if len(calls)==1:
                yield {'choices':[{'text':'Riflessione breve.', 'finish_reason':'stop'}]}
            else:
                yield {'choices':[{'text':'Inizio corretto. ', 'finish_reason':None}]}
                for i in range(100):
                    consumed.append(i)
                    yield {'choices':[{'text':'ghiandole ', 'finish_reason':None}]}
        finally:
            closed.append(True)
    llm=Mock(side_effect=generate);llm.tokenize.side_effect=lambda data:data.split()
    result=bounded_completion(llm,'<think>',{'max_tokens':128},32)
    assert result['choices'][0]['finish_reason']=='repetition'
    assert len(consumed)==6 and len(closed)==2
    assert 'ghiandole' not in result['choices'][0]['text']


def test_explicit_repetition_request_can_complete():
    def generate(prompt,**kwargs):
        yield {'choices':[{'text':'parola '*8, 'finish_reason':'stop'}]}
    llm=Mock(side_effect=generate);llm.tokenize.side_effect=lambda data:data.split()
    result=bounded_completion(llm,'<think>',{'max_tokens':128},32,allow_repetition=True)
    assert result['choices'][0]['finish_reason']=='stop'


def test_stream_buffers_loop_instead_of_emitting_repetitive_tail():
    emitted=[];stream=AnswerStream('Spiega un fenomeno',emitted.append)
    stream.feed('Una frase leggibile. ')
    for _ in range(12):stream.feed('ghiandole ')
    stream.feed('',final=True)
    assert stream.rejected
    assert 'ghiandole' not in ''.join(e['content'] for e in emitted)


def test_memory_display_warns_without_modifying_raw_content():
    raw='ghiandole '*12
    assert 'Esclusa' in memory_display(raw,'assistant')
    assert memory_display(raw,'user')==raw
    assert raw=='ghiandole '*12


def test_bad_answers_cannot_be_confirmed_or_recalled(tmp_path):
    from allma_model.learning_system.answer_recall import AnswerRecall
    recall = AnswerRecall(tmp_path/'recall.json')
    question = 'Spiega la respirazione dei pesci'
    recall.observe('key', 'u', question, 'ghiandole '*12, 'event')
    assert recall.records == {}
    recall.records['key'] = dict(user='u', question=question, answer='ghiandole '*12,
        observations=2, confirmations=['a','b'], rejected=False)
    assert recall.lookup('key','u') is None
    assert 'key' in recall.records


def test_wrapper_applies_native_window_and_preserves_penalty():
    from threading import Lock
    from allma_model.llm.mobile_gemma_wrapper import MobileGemmaWrapper
    class Native:
        last_n_tokens_size = 64
        def tokenize(self, text): return [1]
        def __call__(self, prompt, **options):
            assert 'repeat_last_n' not in options
            assert options['repeat_penalty'] == 1.1
            return {'choices':[{'text':'ghiandole '*12,'finish_reason':'stop'}]}
    wrapper = MobileGemmaWrapper.__new__(MobileGemmaWrapper)
    wrapper.inference_lock=Lock(); wrapper.n_ctx=2048; wrapper.llm=Native()
    assert wrapper.generate('assistant',repeat_penalty=1.1,repeat_last_n=128) == ''
    assert wrapper.llm.last_n_tokens_size == 128
    assert wrapper.last_generation['finish_reason'] == 'repetition'

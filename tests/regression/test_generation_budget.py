from threading import Event
from unittest.mock import Mock
import pytest
from allma_model.utils.generation_budget import bounded_completion
from allma_model.utils.generation_control import GenerationCancelled
from allma_model.utils.thinking_stream import answer_from_completion


def fake_llm():
    calls = []
    def generate(prompt, **kwargs):
        calls.append((prompt, kwargs))
        text = 'Ragionamento incompleto' if len(calls) == 1 else 'Risposta finale.'
        yield {'choices': [{'text': text, 'finish_reason': None}]}
        yield {'choices': [{'text': '', 'finish_reason': 'length' if len(calls) == 1 else 'stop'}]}
    llm = Mock(side_effect=generate)
    llm.tokenize.side_effect = lambda data: list(data.split())
    return llm, calls


def test_exhausted_reasoning_still_reserves_answer_and_reports_stages():
    llm, calls = fake_llm()
    events = []
    result = bounded_completion(llm, '<think>\n', {'max_tokens': 60, 'stop': ['END']}, 20, events.append)
    assert [c[1]['max_tokens'] for c in calls] == [20, 40]
    assert calls[1][0].endswith('Ragionamento incompleto\n</think>\n\n')
    assert answer_from_completion(result['choices'][0]['text'], '<think>') == 'Risposta finale.'
    assert result['budget_meta']['reasoning_finish_reason'] == 'length'
    assert result['choices'][0]['finish_reason'] == 'stop'
    assert ''.join(events) == result['choices'][0]['text']


def test_cancellation_prevents_answer_stage():
    llm, calls = fake_llm()
    event = Event()
    with pytest.raises(GenerationCancelled):
        bounded_completion(llm, '<think>', {'max_tokens': 60}, 20, lambda _: event.set(), event)
    assert len(calls) == 1


def test_reasoning_can_use_more_than_one_third_but_cannot_consume_answer_reserve():
    llm, calls = fake_llm()
    result = bounded_completion(llm, '<think>', {'max_tokens': 60}, 50)
    assert [item[1]['max_tokens'] for item in calls] == [30, 30]
    assert result['budget_meta']['reasoning_truncated'] is True
    assert result['usage']['total_tokens'] == result['usage']['prompt_tokens'] + result['usage']['completion_tokens']

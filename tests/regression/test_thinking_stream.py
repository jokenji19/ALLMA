from threading import Lock
from unittest.mock import Mock

import pytest

from allma_model.utils.thinking_stream import ThinkingStream, answer_from_completion
from allma_model.llm.mobile_gemma_wrapper import MobileGemmaWrapper


@pytest.mark.parametrize('width', [1, 2, 3, 7, 1000])
def test_prefilled_thought_split_at_any_token_width(width):
    raw = 'Okay, the user said Ciao. Since the context is neutral. </think>\nCiao!'
    parser = ThinkingStream(in_thought=True)
    events = []
    for start in range(0, len(raw), width):
        events.extend(parser.feed(raw[start:start + width]))
    events.extend(parser.feed('', final=True))
    assert ''.join(e['content'] for e in events if e['type'] == 'answer').strip() == 'Ciao!'
    assert answer_from_completion(raw, 'assistant\n<think>\n') == 'Ciao!'


def test_explicit_blocks_and_legitimate_english_answer():
    raw = '<think>hidden</think>I should explain this.\n\n\nHere is the example.'
    assert answer_from_completion(raw) == 'I should explain this.\n\n\nHere is the example.'
    assert answer_from_completion('<think>unfinished') == ''
    assert answer_from_completion('unfinished', '<think>\n') == ''
    assert answer_from_completion('2 < 3') == '2 < 3'


@pytest.mark.parametrize('streaming', [False, True])
def test_wrapper_returns_same_clean_answer_as_stream(streaming):
    wrapper = MobileGemmaWrapper.__new__(MobileGemmaWrapper)
    wrapper.inference_lock = Lock()
    wrapper.n_ctx = 2048
    raw = 'Okay, the user said Ciao. Since the context is neutral.</think>Ciao!'
    output = iter({'choices': [{'text': char}]} for char in raw) if streaming else {
        'choices': [{'text': raw, 'finish_reason': 'stop'}]}
    wrapper.llm = Mock(return_value=output)
    wrapper.llm.tokenize.return_value = [1]
    seen = []
    result = wrapper.generate('assistant\n<think>\n', max_tokens=200,
                              callback=seen.append if streaming else None)
    assert result == 'Ciao!'
    if streaming:
        assert ''.join(seen) == raw


def test_structural_pipeline_preserves_subject_and_quoted_general_knowledge():
    from allma_model.core.architecture.structural_core import StructuralCore
    from allma_model.core.architecture.neuroplasticity import NeuroplasticitySystem
    from allma_model.core.cognitive_pipeline import CognitivePipeline
    pipeline = CognitivePipeline(structural_core=StructuralCore(),
                                 neuroplasticity_v5=NeuroplasticitySystem())
    text, _ = pipeline.process("Ciao! Sono un'IA che si riposa e sogna. Come stai oggi?")
    assert text == "Ciao! Sono un'IA che si riposa e sogna. Come stai oggi?"
    quoted = "Nel racconto, il robot dice: Sono un'IA. Il testo cita OpenAI."
    assert pipeline.process(quoted)[0] == quoted

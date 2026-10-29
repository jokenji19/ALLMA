from threading import Lock
from unittest.mock import Mock

import pytest

from allma_model.llm.mobile_gemma_wrapper import MobileGemmaWrapper


def wrapper(chunks, retokenized=1):
    engine = MobileGemmaWrapper.__new__(MobileGemmaWrapper)
    engine.inference_lock = Lock();engine.n_ctx = 2048
    engine.llm = Mock()
    engine.llm.tokenize.side_effect = lambda data, **opts: [1] * (retokenized if data else 0)
    engine.llm.return_value = iter(chunks)
    return engine


@pytest.mark.parametrize('finish', ['length', 'stop'])
def test_native_terminal_reason_wins_over_retokenized_length(finish):
    engine = wrapper([{'choices': [{'text': 'risposta', 'finish_reason': None}]},
                      {'choices': [{'text': '', 'finish_reason': finish}]}])
    assert engine.generate('prompt', max_tokens=272, callback=lambda token: None,
                           request_id='synthetic') == 'risposta'
    meta = engine.get_generation_meta('synthetic')
    assert meta['completion_tokens'] == 1
    assert meta['finish_reason'] == finish and meta['finish_reason_source'] == 'native_stream'
    assert meta['token_count_source'] == 'retokenized'


def test_natural_eof_is_not_reclassified_as_length_when_text_count_hits_cap():
    engine = wrapper([{'choices': [{'text': 'testo', 'finish_reason': 'stop'}]}], retokenized=20)
    engine.generate('prompt', max_tokens=20, callback=lambda token: None)
    assert engine.last_generation['finish_reason'] == 'stop'


def test_empty_stream_has_no_first_token_time():
    engine = wrapper([{'choices': [{'text': '', 'finish_reason': 'stop'}]}])
    assert engine.generate('prompt', max_tokens=20, callback=lambda token: None) == ''
    assert engine.last_generation['ttft_ms'] is None


def test_repetition_stop_is_distinct_from_native_length():
    engine = wrapper([{'choices': [{'text': 'ghiandole ' * 8, 'finish_reason': 'length'}]}])
    engine.generate('prompt', max_tokens=20, callback=lambda token: None)
    assert engine.last_generation['finish_reason'] == 'repetition'
    assert engine.last_generation['finish_reason_source'] == 'local_repetition_guard'


def test_missing_terminal_reason_remains_labeled_as_heuristic():
    engine = wrapper([{'choices': [{'text': 'risposta', 'finish_reason': None}]}])
    engine.generate('prompt', max_tokens=20, callback=lambda token: None)
    assert engine.last_generation['finish_reason_source'] == 'retokenized_heuristic'

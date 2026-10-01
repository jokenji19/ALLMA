from threading import Event, Lock
from unittest.mock import Mock

import pytest
from allma_model.llm.mobile_gemma_wrapper import MobileGemmaWrapper
from allma_model.utils.generation_control import GenerationCancelled


def test_cancel_closes_stream_and_releases_inference_lock():
    wrapper = MobileGemmaWrapper.__new__(MobileGemmaWrapper)
    wrapper.inference_lock = Lock()
    cancelled = Event()
    closed = []
    def output():
        try:
            yield {'choices': [{'text': 'primo'}]}
            yield {'choices': [{'text': 'secondo'}]}
        finally:
            closed.append(True)
    wrapper.llm = Mock(return_value=output())
    wrapper.llm.tokenize.return_value = [1]
    seen = []
    def callback(token):
        seen.append(token)
        cancelled.set()
    with pytest.raises(GenerationCancelled):
        wrapper.generate('prompt', max_tokens=8, callback=callback, cancel_event=cancelled)
    assert seen == ['primo']
    assert closed == [True]
    assert not wrapper.inference_lock.locked()


def test_already_cancelled_request_never_calls_native_model():
    wrapper = MobileGemmaWrapper.__new__(MobileGemmaWrapper)
    wrapper.llm = Mock()
    cancelled = Event()
    cancelled.set()
    with pytest.raises(GenerationCancelled):
        wrapper.generate('prompt', cancel_event=cancelled)
    wrapper.llm.assert_not_called()

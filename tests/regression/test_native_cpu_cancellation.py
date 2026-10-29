import ctypes
from threading import Event
from types import SimpleNamespace as NS
from unittest.mock import Mock
import pytest
from allma_model.llm.cpu_cancellation import CPUCancellation
from allma_model.utils.generation_control import GenerationCancelled


def fixture():
    api=NS(ggml_abort_callback=ctypes.CFUNCTYPE(ctypes.c_bool,ctypes.c_void_p),llama_set_abort_callback=Mock())
    llm=NS(_ctx=NS(ctx=1234,kv_cache_clear=Mock()),set_cache=Mock(),reset=Mock())
    wrapper=NS(llm=llm,backend_info={'kind':'cpu'},_conv_caches={'c':'old'},_conv_cache_prefix={'c':'old'})
    return api,wrapper


def test_cpu_abort_interrupts_before_a_first_token_and_clears_native_state():
    api,wrapper=fixture();signal=Event()
    with pytest.raises(GenerationCancelled):
        with CPUCancellation(wrapper,signal,api) as hook:
            assert hook.supported and hook.callback(None) is False
            signal.set();assert hook.callback(None) is True
            raise RuntimeError('llama_decode returned 2')
    assert api.llama_set_abort_callback.call_count==2
    assert not bool(api.llama_set_abort_callback.call_args.args[1])
    assert wrapper._native_abort_callback is None and wrapper._conv_caches=={}
    wrapper.llm.reset.assert_called_once();wrapper.llm._ctx.kv_cache_clear.assert_called_once()


@pytest.mark.parametrize('kind',['opencl','hexagon'])
def test_cpu_hook_never_registers_on_a_gpu_or_npu_context(kind):
    api,wrapper=fixture();wrapper.backend_info['kind']=kind
    with CPUCancellation(wrapper,Event(),api) as hook:assert not hook.supported
    api.llama_set_abort_callback.assert_not_called()


def test_normal_generation_preserves_state_and_always_removes_callback():
    api,wrapper=fixture()
    with CPUCancellation(wrapper,Event(),api) as hook:assert hook.callback(None) is False
    wrapper.llm.reset.assert_not_called()
    assert api.llama_set_abort_callback.call_count==2 and wrapper._native_abort_callback is None


def test_arbitrary_sensor_bearing_is_set_is_never_called_from_native_code():
    api,wrapper=fixture();signal=NS(is_set=Mock(side_effect=AssertionError('JNI callback forbidden')))
    with CPUCancellation(wrapper,signal,api) as hook:assert not hook.supported
    signal.is_set.assert_not_called()


def test_explicit_native_protocol_has_no_undefined_ctypes_exception():
    api,wrapper=fixture()
    class Signal:
        def native_is_set(self):raise ValueError('synthetic check failure')
    with pytest.raises(RuntimeError,match='check failed'):
        with CPUCancellation(wrapper,Signal(),api) as hook:
            assert hook.callback(None) is True
            raise RuntimeError('llama_decode returned 2')
    assert wrapper._native_abort_callback is None


def test_unrelated_native_error_is_not_misreported_as_cancellation():
    api,wrapper=fixture()
    with pytest.raises(RuntimeError,match='unrelated'):
        with CPUCancellation(wrapper,Event(),api):raise RuntimeError('unrelated')
    wrapper.llm.reset.assert_not_called()


def test_unknown_context_owner_cannot_be_passed_to_a_real_native_api():
    _,wrapper=fixture()
    with CPUCancellation(wrapper,Event()) as hook:assert not hook.supported

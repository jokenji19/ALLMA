"""Cooperative CPU graph abort for the pinned llama.cpp runtime.

The C header explicitly limits this hook to CPU execution. The callback only
reads an Event or an explicit no-I/O native_is_set protocol; it never calls JNI,
reads sensors, raises through ctypes or operates on a GPU context.
The caller must hold the inference lock throughout this context.
"""
import ctypes
from threading import Event
from allma_model.utils.generation_control import GenerationCancelled


class CPUCancellation:
    def __init__(self, wrapper, signal, api=None):
        self.wrapper, self.signal, self.api = wrapper, signal, api
        self.supported = self.fired = False
        self.probe_error = None
        self.callback = self.context = None

    def __enter__(self):
        if getattr(self.wrapper, 'backend_info', {}).get('kind') != 'cpu' or self.signal is None:
            return self
        if isinstance(self.signal, Event):
            probe = self.signal.is_set
        elif callable(getattr(type(self.signal), 'native_is_set', None)):
            probe = self.signal.native_is_set
        else:
            return self  # legacy signals still cancel between iterator chunks
        llm = self.wrapper.llm
        if self.api is None and not type(llm).__module__.startswith('llama_cpp.'):
            return self
        context = getattr(getattr(llm, '_ctx', None), 'ctx', None)
        if not ((type(context) is int and context > 0) or
                (isinstance(context, ctypes.c_void_p) and context.value)):
            return self
        try:
            if self.api is None:
                from llama_cpp import llama_cpp
                self.api = llama_cpp
            factory, register = self.api.ggml_abort_callback, self.api.llama_set_abort_callback
        except (ImportError, AttributeError):
            return self
        def check(_):
            try:
                cancelled = probe()
                if type(cancelled) is not bool:
                    raise ValueError('Native cancellation must return bool')
            except BaseException as error:
                self.probe_error = error
                cancelled = True
            self.fired = self.fired or cancelled
            return cancelled
        self.callback = factory(check)
        self.context = context
        register(context, self.callback, None)
        # Keep a strong reference for the lifetime of any native registration.
        self.wrapper._native_abort_callback = self.callback
        self.supported = True
        return self

    def __exit__(self, kind, error, traceback):
        if not self.supported:
            return False
        self.api.llama_set_abort_callback(self.context, self.api.ggml_abort_callback(), None)
        self.wrapper._native_abort_callback = None
        self.callback = None
        if self.fired or (kind is not None and issubclass(kind, GenerationCancelled)):
            llm = self.wrapper.llm
            for field in ('_conv_caches','_conv_cache_prefix'):
                cache = getattr(self.wrapper, field, None)
                if cache is not None:cache.clear()
            self.wrapper._active_conv = None
            llm.set_cache(None)
            llm.reset()
            llm._ctx.kv_cache_clear()
            if self.probe_error is not None:
                raise RuntimeError('Native cancellation check failed') from self.probe_error
            if self.fired:
                raise GenerationCancelled('CPU generation cancelled') from None
        return False

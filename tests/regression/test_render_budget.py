"""A compute request must not leave Android's window capped afterwards."""
from types import SimpleNamespace
import pytest
from allma_model.ui import render_budget as budget


class Window:
    def __init__(self, rate=0, mode=0):
        self.rate, self.mode = rate, mode
        self.history = []
    def getAttributes(self):
        return SimpleNamespace(preferredRefreshRate=self.rate, preferredDisplayModeId=self.mode)
    def setAttributes(self, attributes):
        self.rate = attributes.preferredRefreshRate
        self.history.append(self.rate)


@pytest.mark.parametrize('fails', [False, True])
def test_window_request_is_restored_in_ui_order_even_after_cancellation(monkeypatch, fails):
    monkeypatch.setenv('ANDROID_PRIVATE', '/data/test')
    window, queued = Window(), []
    monkeypatch.setattr(budget, '_window', lambda: window)
    monkeypatch.setattr(budget, '_dispatch', queued.append)
    try:
        with budget.gpu_render_budget(True):
            assert window.history == []
            if fails: raise ValueError('cancelled generation')
    except ValueError:
        assert fails
    assert len(queued) == 2
    for callback in queued: callback()
    assert window.history == [60, 0]


@pytest.mark.parametrize('rate,mode', [(30,0), (60,0), (0,4)])
def test_existing_low_limit_or_explicit_mode_is_respected(monkeypatch, rate, mode):
    monkeypatch.setenv('ANDROID_PRIVATE', '/data/test')
    window = Window(rate, mode)
    monkeypatch.setattr(budget, '_window', lambda: window)
    monkeypatch.setattr(budget, '_dispatch', lambda callback: callback())
    with budget.gpu_render_budget(True): pass
    assert window.history == []


def test_another_window_controller_change_is_not_overwritten(monkeypatch):
    monkeypatch.setenv('ANDROID_PRIVATE', '/data/test')
    window = Window(120)
    monkeypatch.setattr(budget, '_window', lambda: window)
    monkeypatch.setattr(budget, '_dispatch', lambda callback: callback())
    with budget.gpu_render_budget(True): window.rate = 90
    assert window.history == [60]
    assert window.rate == 90


def test_cpu_and_desktop_never_dispatch_display_changes(monkeypatch):
    calls = []
    monkeypatch.setattr(budget, '_dispatch', calls.append)
    monkeypatch.setenv('ANDROID_PRIVATE', '/data/test')
    with budget.gpu_render_budget(False): pass
    monkeypatch.delenv('ANDROID_PRIVATE')
    with budget.gpu_render_budget(True): pass
    assert calls == []

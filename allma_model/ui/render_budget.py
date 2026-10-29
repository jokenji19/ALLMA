"""Temporary per-window display cadence while the GPU computes a response."""
from contextlib import contextmanager
import logging
import os


def _window():
    from jnius import autoclass
    return autoclass('org.kivy.android.PythonActivity').mActivity.getWindow()


def _dispatch(callback):
    try:
        from android.runnable import run_on_ui_thread
        run_on_ui_thread(callback)()
    except Exception:
        logging.debug('Display cadence dispatch unavailable', exc_info=True)


@contextmanager
def gpu_render_budget(enabled=False):
    """Ask for 60 Hz only during inference; restore the window's prior request.

    Android chooses the actual display rate. No global display settings change.
    Enter/leave are posted in order to the same Android UI thread, including
    the exception path; neither waits for that UI thread while holding the GIL.
    """
    if not enabled or 'ANDROID_PRIVATE' not in os.environ:
        yield
        return
    state = {}

    def enter():
        try:
            window = _window()
            attributes = window.getAttributes()
            original = float(attributes.preferredRefreshRate)
            if 0 < original <= 60 or attributes.preferredDisplayModeId:
                return  # Respect an explicit mode or a lower existing limit.
            state.update(window=window, original=original)
            attributes.preferredRefreshRate = 60.0
            window.setAttributes(attributes)
            state['changed'] = True
            logging.info('[RenderBudget] requested_hz=60 original_hz=%s', original)
        except Exception:
            logging.debug('Display cadence request unavailable', exc_info=True)

    def leave():
        if not state.get('changed'):
            return
        try:
            window = state['window']
            attributes = window.getAttributes()
            # A user or another window controller may have changed the request.
            if attributes.preferredRefreshRate == 60.0:
                attributes.preferredRefreshRate = state['original']
                window.setAttributes(attributes)
                logging.info('[RenderBudget] restored_hz=%s', state['original'])
        except Exception:
            logging.debug('Display cadence restore unavailable', exc_info=True)

    try:
        _dispatch(enter)
        yield
    finally:
        _dispatch(leave)

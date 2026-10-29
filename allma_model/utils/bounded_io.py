"""Bounded admission and caller deadlines around a synchronous network client.

Only one reference transport may exist, including a cancelled request still
waiting for DNS or a socket timeout. Workers cannot touch chat or persistent
state. A late transport result is discarded and never queues another job.
"""
import threading
import time
from .generation_control import check_cancelled

_slot = threading.BoundedSemaphore(1)


class StopEvent:
    def __init__(self, external, internal):
        self.external, self.internal = external, internal

    def is_set(self):
        return self.internal.is_set() or (self.external is not None and self.external.is_set())


def reference_io(operation, cancelled, allowed, seconds=8):
    check_cancelled(cancelled)
    if not allowed():
        return []
    if not _slot.acquire(blocking=False):
        raise RuntimeError('Reference transport still closing')
    stop, done, result = threading.Event(), threading.Event(), {}

    def work():
        try:
            result['value'] = operation(StopEvent(cancelled, stop))
        except BaseException as error:
            result['error'] = error
        finally:
            _slot.release()
            done.set()

    worker = threading.Thread(target=work, name='ALLMA-ReferenceIO', daemon=True)
    try:
        deadline = time.monotonic() + seconds
        worker.start()
    except BaseException:
        _slot.release()
        raise
    try:
        while True:
            check_cancelled(cancelled)
            if not allowed():
                return []
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError('Reference deadline exceeded')
            if done.wait(min(0.05, remaining)):
                check_cancelled(cancelled)
                if not allowed():
                    return []
                if 'error' in result:
                    raise result['error']
                return result['value']
    finally:
        stop.set()

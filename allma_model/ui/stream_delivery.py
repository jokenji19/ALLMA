"""Coalesce native-to-WebView updates without changing content or turn order."""
from threading import RLock


class StreamDelivery:
    def __init__(self, emit, schedule, interval=0.08):
        self.emit = emit
        self.schedule = schedule
        self.interval = interval
        self._lock = RLock()
        self._event = None
        self._request = None
        self._active = False
        self._pending = []

    def start(self, request):
        with self._lock:
            self.clear()
            self._request = request
            self._active = True

    def push(self, text, thought, request):
        with self._lock:
            if not self._active or request != self._request or not text:
                return
            if self._pending and self._pending[-1][1] == bool(thought):
                self._pending[-1][0] += text
            else:
                self._pending.append([text, bool(thought), request])
            if self._event is None:
                self._event = self.schedule(self.flush, self.interval)

    def flush(self, _dt=0):
        with self._lock:
            if self._event is not None:
                self._event.cancel()
                self._event = None
            pending, self._pending = self._pending, []
            if pending:
                # Emit while serialized with finish/start: a delayed frame must
                # never enqueue a chunk after endStream or into another turn.
                self.emit(pending)

    def finish(self, request):
        with self._lock:
            if not self._active or request != self._request:
                return
            self.flush()
            self._active = False

    def clear(self):
        with self._lock:
            if self._event is not None:
                self._event.cancel()
                self._event = None
            self._pending.clear()
            self._active = False


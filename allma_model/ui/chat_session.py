"""Thread-safe ownership of one chat turn, independent of Kivy/WebView."""
from dataclasses import dataclass, field
from threading import Event, RLock


@dataclass
class ChatTurn:
    request_id: int
    conversation_id: str
    cancelled: Event = field(default_factory=Event)


class ChatSession:
    def __init__(self, create_conversation):
        self._create = create_conversation
        self._lock = RLock()
        self.conversation_id = create_conversation()
        self._active = None
        self._next_id = 0
        self._reset_pending = False

    def begin(self):
        with self._lock:
            if self._active is not None:
                return None
            self._next_id += 1
            self._active = ChatTurn(self._next_id, self.conversation_id)
            return self._active

    def cancel(self):
        with self._lock:
            if self._active is not None:
                self._active.cancelled.set()

    def new_conversation(self):
        with self._lock:
            if self._active is not None:
                self._reset_pending = True
                self._active.cancelled.set()
                return None
            self.conversation_id = self._create()
            return self.conversation_id

    def finish(self, turn):
        with self._lock:
            if self._active is not turn:
                return None
            self._active = None
            if self._reset_pending:
                self._reset_pending = False
                self.conversation_id = self._create()
                return self.conversation_id
            return None

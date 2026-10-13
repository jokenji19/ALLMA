"""Release complete answer segments after the existing personal-claim checks."""
import re
from allma_model.utils.repetition_guard import repetition_start, requested_repetition
from allma_model.core.autobiographical_identity import identity_conflict, unsupported_personal_claim
from .output_contract import borrowed_user_experience


class AnswerStream:
    def __init__(self, request, emit, continuity=None):
        self.continuity = continuity
        self.request = request
        self.emit = emit
        self.observed = ''
        self.pending = ''
        self.rejected = False
        self.emitted = False

    def feed(self, text, final=False):
        if self.rejected:
            return
        self.observed += text
        if not requested_repetition(self.request) and repetition_start(self.observed) is not None:
            self.rejected = True
            self.pending = ''
            return
        self.pending += text
        if self.continuity:
            if final and self.continuity.duplicate(self.observed):
                self.rejected = True
                self.pending = ''
                return
            if not final and self.continuity.hold_prefix(self.observed):
                return
        # Avoid splitting code or abbreviations/decimals across a partial line.
        # A code block stays buffered until the final validated response.
        if '```' in self.pending:
            return
        while self.pending:
            boundary = re.search(r'[.!?](?=\s)', self.pending)
            if boundary:
                end = boundary.end()
            elif final:
                end = len(self.pending)
            else:
                break
            chunk, self.pending = self.pending[:end], self.pending[end:]
            checked = re.sub(r'\s+', ' ', chunk).strip()
            if identity_conflict(checked) or unsupported_personal_claim(checked, self.request) or borrowed_user_experience(checked, self.request):
                self.rejected = True
                self.pending = ''
                break
            if chunk:
                self.emit({'type': 'answer', 'content': chunk})
                self.emitted = self.emitted or bool(chunk.strip())

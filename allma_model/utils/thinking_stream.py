"""Separate model reasoning from answers, including tags split across tokens."""


class ThinkingStream:
    def __init__(self, in_thought=False):
        self.in_thought = in_thought
        self.pending = ''

    def feed(self, text, final=False):
        self.pending += text
        events = []
        tags = ('<think>', '</think>')
        while self.pending:
            matches = [(self.pending.find(tag), tag) for tag in tags
                       if tag in self.pending]
            if matches:
                index, tag = min(matches)
                if index:
                    events.append(self._event(self.pending[:index]))
                self.in_thought = tag == '<think>'
                self.pending = self.pending[index + len(tag):]
                continue
            # Retain only a possible tag prefix, not an arbitrary token window.
            keep = 0
            if not final:
                for tag in tags:
                    for length in range(1, len(tag)):
                        if self.pending.endswith(tag[:length]):
                            keep = max(keep, length)
            count = len(self.pending) - keep
            if count:
                events.append(self._event(self.pending[:count]))
                self.pending = self.pending[count:]
            break
        return events

    def _event(self, text):
        return {'type': 'thought' if self.in_thought else 'answer', 'content': text}


def answer_from_completion(text, prompt=''):
    """Account for a reasoning opening tag already supplied by the prompt."""
    parser = ThinkingStream(in_thought=prompt.rstrip().endswith('<think>'))
    return ''.join(event['content'] for event in parser.feed(text, final=True)
                   if event['type'] == 'answer').strip()

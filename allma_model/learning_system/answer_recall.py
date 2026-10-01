"""User-confirmed answer recall, separate from autobiographical knowledge and GGUF weights."""
import hashlib
import json
import logging
import re
import threading
import unicodedata
from pathlib import Path
from allma_model.utils.persistence import atomic_write_json


def normalize(text):
    return ' '.join(unicodedata.normalize('NFKC', text).casefold().split()).rstrip(' .!?')


def feedback_kind(text):
    text = normalize(text)
    if text in {'risposta corretta', 'la risposta è corretta', 'confermo la risposta',
                'corretto', 'esatto', 'correct answer'}:
        return 'positive'
    if text in {'risposta sbagliata', 'la risposta è sbagliata', 'sbagliato',
                'non è corretto', 'wrong answer'} or re.match(r'^(hai sbagliato|ti sbagli)\b', text):
        return 'negative'
    return None


def eligible(question):
    # Recall only stable, self-contained requests. Personal identity uses its own evidence gate.
    return (len(question.strip()) >= 12 and not re.search(
        r'\b(oggi|ora|adesso|ieri|domani|ultim[oaie]|attuale|prezzo|meteo|batteria|'
        r'temperatura|farmac\w*|dos\w*|medic\w*|sintom\w*|invest\w*|legale|'
        r'mio|mia|miei|mie|tuo|tua|tuoi|tue|ricordi|prima|questo|quello|questa|quella)\b',
        question, re.I))


class AnswerRecall:
    def __init__(self, path, confirmations=2):
        self.path = Path(path)
        self.confirmations = confirmations
        self.lock = threading.RLock()
        self.records = {}
        try:
            data = json.loads(self.path.read_text())
            if data.get('version') == 1:
                self.records = data.get('records', {})
        except FileNotFoundError:
            pass
        except (ValueError, OSError, AttributeError):
            logging.warning('AnswerRecall: unreadable state; recall disabled for saved entries')

    def key(self, user, question, history, context=None):
        q = normalize(question)
        turns = []
        skip_answer = False
        for m in history:
            if m.metadata.get('source') == 'learning_feedback':
                continue
            if m.role == 'user':
                skip_answer = normalize(m.content) == q
                if skip_answer:
                    continue
            elif skip_answer:
                continue
            turns.append((m.role, m.content))
        payload = [user, q, turns[-4:], context or {}]
        return hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str).encode()).hexdigest()

    def _save(self):
        atomic_write_json(self.path, {'version': 1, 'records': self.records})

    def observe(self, key, user, question, answer, event):
        if not eligible(question):
            return
        with self.lock:
            previous = self.records.get(key)
            if previous and previous['answer'] == answer:
                previous['observations'] += 1
            else:
                self.records[key] = {'user': user, 'question': question, 'answer': answer,
                                     'observations': 1, 'confirmations': [], 'rejected': False}
            self.records[key]['event'] = event
            while len(self.records) > 500:
                self.records.pop(next(iter(self.records)))
            self._save()

    def feedback(self, key, user, event, positive):
        with self.lock:
            record = self.records.get(key)
            if not record or record['user'] != user:
                return False
            if not positive:
                record['rejected'] = True
                record['confirmations'] = []
            elif not record['rejected'] and event not in record['confirmations']:
                record['confirmations'].append(event)
            self._save()
            return True

    def lookup(self, key, user):
        with self.lock:
            r = self.records.get(key)
            if (r and r['user'] == user and not r['rejected']
                    and len(r['confirmations']) >= self.confirmations):
                return dict(r)
        return None

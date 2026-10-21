"""User-confirmed answer recall, separate from autobiographical knowledge and GGUF weights."""
import hashlib
import json
import logging
import re
import threading
import unicodedata
from copy import deepcopy
from pathlib import Path
from allma_model.utils.persistence import atomic_write_json, preserve_invalid_file, StateRecoveryRequired
from allma_model.utils.repetition_guard import repetition_start, requested_repetition
from allma_model.utils.output_contract import requested_contract, valid_contract, borrowed_user_experience, requested_sentence_count, valid_sentence_count
from allma_model.utils.source_claims import unbacked_source_claim


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
        self.delivery_checkpoint = 0
        self.load_error = None
        self.load_state()

    def load_state(self):
        """Publish only a complete valid snapshot; a failed reload keeps RAM intact."""
        with self.lock:
            try:
                data = json.loads(self.path.read_text(encoding='utf-8'))
                if (not isinstance(data, dict) or type(data.get('version')) is not int
                        or data['version'] != 1 or not isinstance(data.get('records'), dict)):
                    raise ValueError('Invalid recall schema')
                checkpoint = data.get('delivery_checkpoint', 0)
                if type(checkpoint) is not int or not 0 <= checkpoint < 2**53:
                    raise ValueError('Invalid recall checkpoint')
                if any(not self._valid_record(key, record) for key, record in data['records'].items()):
                    raise ValueError('Invalid recall record')
                records = deepcopy(data['records'])
            except FileNotFoundError as error:
                if self.records or self.delivery_checkpoint or self.load_error is not None:
                    self.load_error = error
                    return False
                return True
            except (ValueError, OSError, AttributeError) as error:
                self.load_error = error
                self._preserve_invalid_state()
                logging.warning('AnswerRecall: state requires recovery; automatic recall and writes disabled')
                return False
            self.records = records
            self.delivery_checkpoint = checkpoint
            self.load_error = None
            return True

    @staticmethod
    def _valid_record(key, record):
        return (isinstance(key, str) and isinstance(record, dict)
                and all(isinstance(record.get(field), str) and record[field].strip()
                        for field in ('user', 'question', 'answer'))
                and type(record.get('observations')) is int and record['observations'] >= 1
                and type(record.get('rejected')) is bool
                and isinstance(record.get('confirmations'), list)
                and all(isinstance(event, str) and event for event in record['confirmations'])
                and len(set(record['confirmations'])) == len(record['confirmations']))

    def _preserve_invalid_state(self):
        # Preserve original bytes before any later successful learning overwrites them.
        if not self.path.exists():
            return
        try:
            preserve_invalid_file(self.path)
        except OSError:
            logging.warning('AnswerRecall: cannot preserve invalid state')

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
        if self.load_error is not None:
            raise StateRecoveryRequired('Archivio delle risposte apprese da recuperare prima di salvare') from self.load_error
        atomic_write_json(self.path, {'version': 1, 'records': self.records,
                                     'delivery_checkpoint': self.delivery_checkpoint})

    def observe(self, key, user, question, answer, event, *, delivery_sequence=None):
        if unbacked_source_claim(answer):
            return
        if (not eligible(question) or not valid_contract(answer, requested_contract(question))
                or not valid_sentence_count(answer, requested_sentence_count(question))
                or borrowed_user_experience(answer, question)
                or (not requested_repetition(question) and repetition_start(answer) is not None)):
            return
        with self.lock:
            if self.load_error is not None:
                raise StateRecoveryRequired('Archivio delle risposte apprese da recuperare prima di salvare') from self.load_error
            if delivery_sequence is not None and delivery_sequence <= self.delivery_checkpoint:
                return
            original = self.records
            previous_checkpoint = self.delivery_checkpoint
            self.records = dict(original)
            previous = deepcopy(self.records.get(key))
            if previous and previous['answer'] == answer:
                previous['observations'] += 1
                self.records[key] = previous
            else:
                self.records[key] = {'user': user, 'question': question, 'answer': answer,
                                     'observations': 1, 'confirmations': [], 'rejected': False}
            self.records[key]['event'] = event
            while len(self.records) > 500:
                self.records.pop(next(iter(self.records)))
            try:
                if delivery_sequence is not None:
                    self.delivery_checkpoint = delivery_sequence
                self._save()
            except Exception:
                self.records = original
                self.delivery_checkpoint = previous_checkpoint
                raise

    def feedback(self, key, user, event, positive):
        with self.lock:
            if self.load_error is not None:
                return False
            record = deepcopy(self.records.get(key))
            if not record or record['user'] != user:
                return False
            original = self.records
            self.records = dict(original, **{key: record})
            if not positive:
                record['rejected'] = True
                record['confirmations'] = []
            elif not record['rejected'] and event not in record['confirmations']:
                record['confirmations'].append(event)
            try:
                self._save()
            except Exception:
                self.records = original
                raise
            return True

    def lookup(self, key, user):
        with self.lock:
            if self.load_error is not None:
                return None
            r = self.records.get(key)
            if (r and r['user'] == user and not r['rejected']
                    and eligible(r['question'])
                    and valid_contract(r['answer'], requested_contract(r['question']))
                    and valid_sentence_count(r['answer'], requested_sentence_count(r['question']))
                    and not borrowed_user_experience(r['answer'], r['question'])
                    and not unbacked_source_claim(r['answer'])
                    and (requested_repetition(r['question']) or repetition_start(r['answer']) is None)
                    and len(r['confirmations']) >= self.confirmations):
                return deepcopy(r)
        return None

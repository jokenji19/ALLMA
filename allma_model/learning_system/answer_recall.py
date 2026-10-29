"""User-confirmed answer recall, separate from autobiographical knowledge and GGUF weights."""
import hashlib
import json
import logging
import re
import sqlite3
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
    def __init__(self, path, confirmations=2, *, legacy_path=None):
        self.path = Path(path)
        self.confirmations = confirmations
        self.lock = threading.RLock()
        self.records = {}
        self.delivery_checkpoint = 0
        self.load_error = None
        self._store = None
        self._pending_write = None
        self._initialized = False
        if self.path.suffix == '.db':
            from .recall_store import RecallStore
            self._store = RecallStore(self.path, self._valid_record, self._valid_snapshot, legacy_path)
        self.load_state()

    def load_state(self):
        """Publish only a complete valid snapshot; a failed reload keeps RAM intact."""
        with self.lock:
            if self._store is not None:
                try:
                    checkpoint = self._store.load(initialize=not self._initialized)
                except Exception as error:
                    self.load_error = error
                    target = self.path if self.path.exists() else self._store.legacy_path
                    code = getattr(error,'sqlite_errorcode',0) & 255
                    structural = (isinstance(error,(ValueError,TypeError,KeyError))
                                  or code in (sqlite3.SQLITE_CORRUPT,sqlite3.SQLITE_NOTADB,sqlite3.SQLITE_ERROR))
                    if structural and target is not None and target.exists():
                        try:
                            preserve_invalid_file(target)
                        except OSError:
                            pass
                    logging.warning('AnswerRecall: persistent store unavailable (%s, errno=%s): %s',
                                    type(error).__name__,getattr(error,'errno',None),error)
                    return False
                self.records = self._store.view
                self.delivery_checkpoint = checkpoint
                self.load_error = None
                self._initialized = True
                return True
            try:
                data = json.loads(self.path.read_text(encoding='utf-8'))
                records, checkpoint = self._valid_snapshot(data)
                records = deepcopy(records)
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

    @classmethod
    def _valid_snapshot(cls, data):
        if (not isinstance(data, dict) or type(data.get('version')) is not int
                or data['version'] != 1 or not isinstance(data.get('records'), dict)):
            raise ValueError('Invalid recall schema')
        checkpoint = data.get('delivery_checkpoint', 0)
        if type(checkpoint) is not int or not 0 <= checkpoint < 2**53:
            raise ValueError('Invalid recall checkpoint')
        if any(not cls._valid_record(key, record) for key, record in data['records'].items()):
            raise ValueError('Invalid recall record')
        return data['records'], checkpoint

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
        if self._store is not None:
            if self._pending_write is None:
                return
            return self._store.apply(*self._pending_write)
        atomic_write_json(self.path, {'version': 1, 'records': self.records,
                                     'delivery_checkpoint': self.delivery_checkpoint})

    def _persist_update(self, key, update, delivery_sequence=None):
        self._pending_write = (key, update, delivery_sequence)
        try:
            changed, checkpoint = self._save()
            self.delivery_checkpoint = checkpoint
            return changed
        finally:
            self._pending_write = None

    @staticmethod
    def _observation(previous, user, question, answer, event):
        if previous is not None and previous['user'] != user:
            raise ValueError('Recall key belongs to another user')
        if previous and previous['answer'] == answer:
            record = deepcopy(previous)
            record['observations'] += 1
        else:
            record = {'user': user, 'question': question, 'answer': answer,
                      'observations': 1, 'confirmations': [], 'rejected': False}
        record['event'] = event
        return record

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
            if self._store is not None:
                self._persist_update(key,
                    lambda previous: self._observation(previous,user,question,answer,event), delivery_sequence)
                return
            if delivery_sequence is not None and delivery_sequence <= self.delivery_checkpoint:
                return
            original = self.records
            previous_checkpoint = self.delivery_checkpoint
            self.records = dict(original)
            self.records[key] = self._observation(self.records.get(key),user,question,answer,event)
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
            if self._store is not None:
                def update(previous):
                    if previous is None or previous['user'] != user:
                        return None
                    record = deepcopy(previous)
                    if not positive:
                        record['rejected'] = True
                        record['confirmations'] = []
                    elif not record['rejected'] and event not in record['confirmations']:
                        record['confirmations'].append(event)
                    return record
                return self._persist_update(key, update)
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
            try:
                r = self.records.get(key)
            except (sqlite3.Error, OSError, ValueError, TypeError, KeyError) as error:
                if self._store is None:
                    raise
                # A failed optional recall must not prevent a normal model turn.
                # Only structural damage/missing state latches recovery mode;
                # a transient busy or I/O condition can be retried later.
                code = getattr(error, 'sqlite_errorcode', 0) & 255
                if (not self.path.exists() or not isinstance(error, (sqlite3.Error,OSError))
                        or code in (sqlite3.SQLITE_CORRUPT, sqlite3.SQLITE_NOTADB)):
                    self.load_error = error
                    self._preserve_invalid_state()
                logging.warning('AnswerRecall: lookup unavailable (%s)',type(error).__name__)
                return None
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

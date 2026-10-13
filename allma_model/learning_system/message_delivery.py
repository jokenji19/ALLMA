"""Explicit, persistent communication preferences, independent of model weights."""
import json
import logging
import re
import threading
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

from allma_model.utils.persistence import atomic_write_json

MODES = {'progressive', 'complete', 'auto'}


def preference_request(message):
    """Recognize whole explicit directives, never quotes, silence or unrelated praise."""
    text = ' '.join(unicodedata.normalize('NFKC', message).casefold().split()).strip(' .!?')
    for _ in range(3):
        text = re.sub(r'^(?:allma[, ]+|da ora (?:in poi )?|per favore[, ]+)', '', text)
    patterns = {
        'progressive': [
            r'(?:preferisco|voglio) (?:le |che le )?risposte (?:siano )?(?:progressive|progressivamente|in streaming)',
            r'(?:scrivi|scrivimi|rispondi|mostra le risposte|mandami le risposte) (?:in modo |in maniera )?(?:progressivo|progressiva|progressivamente|in streaming|un po alla volta)',
        ],
        'complete': [
            r'(?:preferisco|voglio) (?:le |che le )?risposte (?:siano )?(?:tutte insieme|tutto insieme|in un unico blocco)',
            r'(?:scrivi|scrivimi|rispondi|mostra le risposte|mandami le risposte) (?:tutto insieme|tutto in una volta|tutto d[’\']un colpo|in un unico blocco)',
            r'non (?:scrivere|rispondere) (?:progressivamente|in streaming)',
        ],
        'auto': [
            r'(?:scegli tu|decidi tu) (?:come (?:inviare|mandare|mostrare) le risposte|la modalit[àa] di invio)',
            r'(?:usa|preferisco|voglio) (?:la )?modalit[àa] (?:automatica|di invio automatica)',
        ],
    }
    for mode, choices in patterns.items():
        if any(re.fullmatch(pattern, text) for pattern in choices):
            return mode
    return None


def needs_personal_validation(message):
    """Keep personal/history requests buffered; generic output still has sentence guards."""
    return bool(re.search(
        r'\b(?:tuo|tua|tuoi|tue|nostro|nostra|nostri|nostre|ricordi|ricordo|ricordare|'
        r'ricordami|abbiamo|preferisci|ti piace|chi sei|ti chiami|mi chiamo|mi conosci|'
        r'sogni|sognato|dormi|dormito|emozioni|sei nat[oa]|hai vissuto)\b', message, re.I))


class MessageDelivery:
    def __init__(self, path):
        self.path = Path(path)
        self.lock = threading.RLock()
        self.users = {}
        try:
            data = json.loads(self.path.read_text(encoding='utf-8'))
            if isinstance(data, dict) and data.get('version') == 1 and isinstance(data.get('users'), dict):
                self.users = {user: item for user, item in data['users'].items()
                              if isinstance(item, dict) and isinstance(item.get('mode'), str) and item['mode'] in MODES}
        except FileNotFoundError:
            pass
        except (OSError, ValueError):
            logging.warning('MessageDelivery: stato illeggibile; uso la modalità predefinita')

    def learn(self, user, mode):
        if not user or mode not in MODES:
            raise ValueError('Preferenza di invio non valida')
        with self.lock:
            record = {'mode': mode, 'source': 'explicit_user_instruction',
                      'updated_at': datetime.now(timezone.utc).isoformat()}
            updated = dict(self.users, **{user: record})
            # Commit memory only after successful persistence.
            atomic_write_json(self.path, {'version': 1, 'users': updated})
            self.users = updated

    def choose(self, user, message, voice=False):
        with self.lock:
            requested = self.users.get(user, {}).get('mode', 'auto')
        if voice:
            return 'complete', 'voice_final_validation'
        if needs_personal_validation(message):
            return 'complete', 'personal_validation'
        if requested == 'complete':
            return 'complete', 'explicit_user_preference'
        return 'progressive', 'explicit_user_preference' if requested == 'progressive' else 'default_general_stream'

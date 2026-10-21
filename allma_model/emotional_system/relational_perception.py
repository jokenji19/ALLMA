"""Transient, attributed interpretation of a conversation, without extra inference.

Prior emotion is context, not a current diagnosis or a personality trait. The
durable support preferences belong to the existing personality subsystem.
"""
from datetime import datetime, timezone
import re
import unicodedata

from .emotion_analysis import analyze, NUANCE_NAMES_IT

VERSION = 'relational-perception-v1'
WINDOW = 4
MAX_AGE_SECONDS = 1800


def plain(text):
    return ' '.join(unicodedata.normalize('NFKC', text or '').casefold().split()).strip(' .!?')


def boundary_reply(message):
    """Only an entire, explicit boundary; mixed requests remain with the model."""
    if not isinstance(message, str) or len(message) > 180:
        return None
    if re.fullmatch(r'(?:per ora |adesso )?(?:preferisco non parlarne|non (?:voglio|mi va di) parlarne|'
                    r'non voglio parlare di questo|cambiamo argomento|lasciamo perdere questo argomento)', plain(message)):
        return ('Va bene, lasciamo questo argomento.', 'conversation_boundary', [])
    return None


def support_request(message):
    """Current need, not a durable preference and not an emotion classification."""
    text = plain(message)
    if (len(text) > 12000 or re.search(r'```|["«»“”]|\b(?:dice|ha detto|traduci|scrivi|spiega|significa|frase|esempio|immagina|supponi|se|quando|forse)\b', text)
            or re.search(r"(?<!\w)'[^'\n]{2,}'(?!\w)", text)):
        return None
    def affirmed(pattern):
        return any(not re.search(r'\b(?:non|evita di)\s*$', text[max(0,m.start()-15):m.start()])
                   for m in re.finditer(pattern,text))
    listening = affirmed(r'\b(?:voglio solo sfogarmi|ho (?:solo )?bisogno di (?:sfogarmi|essere ascoltat[oa])|'
                         r'ascoltami senza (?:darmi )?consigli)\b')
    listening = listening or bool(re.search(r'\b(?:non voglio consigli|non cerco soluzioni)\b', text))
    practical = affirmed(r'\b(?:aiutami a (?:capire|decidere) cosa fare|'
                         r'(?:dammi|vorrei|voglio|cerco) (?:dei |alcuni )?(?:consigli|suggerimenti) pratici|'
                         r'aiutami a trovare una soluzione)\b')
    # A request for both is ambiguous; do not silently choose either.
    return 'listening' if listening and not practical else 'practical' if practical and not listening else None


def _read(record, key, default=None):
    return record.get(key, default) if isinstance(record, dict) else getattr(record, key, default)


def _timestamp(value):
    try:
        if isinstance(value, str):
            value = datetime.fromisoformat(value)
        if not isinstance(value, datetime):
            return None
        return value.timestamp()
    except (ValueError, OverflowError, OSError):
        return None


def plan(message, state, history, user_id, conversation_id, *, now=None, learned_aliases=None):
    """Build small host guidance from current evidence and scoped recent users.

    No raw history text is copied into metadata or host instructions. The
    original conversation is already supplied to the LLM as attributed turns.
    """
    context = _read(state, 'context', {}) or {}
    analysis = _read(state, 'analysis', None) or context.get('emotion_analysis', {})
    nuances = _read(state, 'nuances', {}) or {}
    current = ([label for label in nuances if label in NUANCE_NAMES_IT][:4]
               if analysis.get('source') != 'recent_reference' else [])
    denied = list(dict.fromkeys(r.get('label') for r in analysis.get('negated', [])
                               if r.get('label') in NUANCE_NAMES_IT))[:4]
    need = support_request(message)
    uncertain = bool(analysis.get('uncertain'))
    result = {'version': VERSION, 'current_labels': current, 'denied_labels': denied,
              'prior_labels': [], 'relation': 'none', 'support_request': need,
              'interpretation_uncertain': uncertain, 'persistent_emotion_inferred': False,
              'instruction': ''}
    if analysis.get('truncated'):
        result['interpretation_uncertain'] = True
        return result
    from allma_model.utils.output_contract import requested_contract, requested_sentence_count
    if requested_contract(message) or requested_sentence_count(message):
        return result  # Preserve strict formatting without extra counselling.
    unquoted = re.sub(r'```.*?(?:```|$)|"[^"\n]*"|“[^”\n]*”|«[^»\n]*»', '', message, flags=re.S)
    text = plain(unquoted)
    if not current and re.search(r'\b(?:scrivi|traduci|spiega|analizza|immagina|il personaggio|la frase)\b', text):
        return result
    # The message can be short and ambiguous without naming an emotion.
    tentative = bool(re.fullmatch(r'(?:va be[nh]e|va be|vabbè|lascia perdere|niente|non importa)', text))
    repeated = bool(re.search(r'\b(?:ho fallito ancora|ho fallito di nuovo|è successo di nuovo|e successo di nuovo)\b', text))
    referring = bool(re.fullmatch(r'(?:(?:mi sento|sto) )?(?:ancora cos[iì]|come prima|meglio|peggio)', text))
    correcting = bool(denied and re.search(r'\b(?:non sono|non mi sento|non provo|non ho)\b', text))
    contextual = bool(current or need or tentative or repeated or referring or correcting)
    if not contextual:
        return result
    now_seconds = _timestamp(now) if now is not None else datetime.now(timezone.utc).timestamp()
    previous = []
    # Count turns, not emotions: an unrelated current topic must break carryover.
    for record in reversed(history[-16:]):
        metadata = _read(record, 'metadata', {}) or {}
        if (_read(record, 'role') != 'user' or _read(record, 'user_id', metadata.get('user_id')) != user_id
                or _read(record, 'conversation_id') != conversation_id or metadata.get('is_valid') is False):
            continue
        observed = _timestamp(_read(record, 'timestamp'))
        if observed is None or now_seconds is None or not 0 <= now_seconds - observed <= MAX_AGE_SECONDS:
            continue
        previous.append(record)
        if len(previous) >= WINDOW:
            break
    prior = []
    for record in previous:
        prior_analysis = analyze(_read(record, 'content', ''), learned_aliases=learned_aliases)
        if prior_analysis['analysis']['truncated']:
            break
        labels = [label for label, strength in prior_analysis['nuances'].items() if strength >= .8]
        # Explicit correction or a clear new self-report supersedes older mood.
        if labels:
            prior = labels[:4]
            break
        if prior_analysis['analysis']['negated'] or boundary_reply(_read(record, 'content', '')):
            break
        # Only explicit references can bridge intervening unrelated turns.
        if not referring:
            break
    hints = []
    if correcting:
        result['relation'] = 'self_correction'
        hints.append('Accogli la correzione dell’utente: non riproporre le emozioni che ha negato. La sua descrizione attuale prevale sulle tue ipotesi precedenti.')
        prior = [label for label in prior if label not in denied]
    elif prior and (referring or tentative or repeated or current):
        result['relation'] = 'recent_reference' if referring else 'recent_context'
        hints.append('Nel turno recente l’utente aveva espresso '+', '.join(NUANCE_NAMES_IT[x] for x in prior)+': è contesto passato, non prova che si senta ancora così. Non trasformarlo in un tratto della persona.')
    result['prior_labels'] = prior
    if tentative:
        result['interpretation_uncertain'] = True
        hints.append('Il messaggio breve può essere letterale o esprimere disagio: non scegliere un’emozione senza prove. Rispetta la possibilità di chiudere l’argomento, senza insistere.')
    if repeated:
        result['interpretation_uncertain'] = True
        hints.append('La ripetizione è dichiarata dall’utente; il suo significato emotivo resta incerto. Puoi riconoscerne il possibile peso senza inventare altri fallimenti o ricordi.')
    if current and uncertain:
        hints.append('Le emozioni rilevate restano ipotesi: usa formulazioni prudenti e lascia correggere l’interpretazione, senza domande di conferma automatiche.')
    if analysis.get('mixed'):
        hints.append('Lascia spazio alle emozioni diverse espresse insieme, senza ridurle a un’unica etichetta.')
    # A current need is also expressed through the existing personality plan.
    # The same signal does not become a second persistent memory here.
    result['instruction'] = ' '.join(hints)
    return result

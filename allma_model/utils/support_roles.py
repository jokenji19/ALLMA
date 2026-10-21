"""Experimental speaker grounding, derived from evidence rather than an answer template."""
import json
from allma_model.emotional_system.emotion_analysis import analyze, NUANCE_NAMES_IT


def role_map(message):
    state = analyze(message)
    analysis = state['analysis']
    def labels(items):
        return list(dict.fromkeys(NUANCE_NAMES_IT.get(item['label'], item['label']) for item in items))[:4]
    return {'mittente': 'utente', 'destinatario': 'ALLMA',
            'emozioni_utente': [NUANCE_NAMES_IT.get(label,label) for label in state['nuances']][:4],
            'emozioni_altre_persone': labels(analysis['other_evidence']),
            'emozioni_negate': labels(analysis['negated']),
            'interpretazione_incerta': analysis['uncertain'],
            'proprietario_eventi_narrati': 'chi li racconta, non ALLMA',
            'azione_ALLMA': 'rispondere nella conversazione'}


def role_instruction(message):
    return ('Mappa dei ruoli (indizi, non ricordi): '+json.dumps(role_map(message),ensure_ascii=False,separators=(',',':'))+
            '\nFormula una risposta rivolta al mittente usando tu/ti per la sua esperienza. '
            'Accogli la situazione e offri aiuto pertinente. Io indica solo le tue azioni conversazionali; '
            'mantieni distinti gli eventi del mittente e delle altre persone.')

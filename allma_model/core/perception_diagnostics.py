"""Small offline Android battery; no microphone, inference or personal archives."""
from allma_model.emotional_system.emotion_analysis import analyze
from allma_model.core.perception_lite import PerceptionSystemLite


def require(condition, detail):
    if not condition:
        raise AssertionError(detail)


EMOTION_CASES = (
    ('it_mixed', 'Sono felice ma preoccupata', {'joy', 'anxiety'}),
    ('en_mixed', 'I am happy but worried', {'joy', 'anxiety'}),
    ('es_joy', 'Estoy muy feliz', {'joy'}),
    ('fr_joy', 'Je suis heureux', {'joy'}),
    ('de_joy', 'Ich bin glücklich', {'joy'}),
    ('es_negated', 'No estoy triste ni enfadado', set()),
    ('fr_negated', 'Je ne suis pas triste', set()),
    ('de_negated', 'Ich habe keine Angst', set()),
    ('es_subject', 'Mi hermana está triste, pero yo estoy aliviada', {'relief'}),
    ('fr_subject', 'Elle est triste, mais je suis soulagée', {'relief'}),
    ('de_subject', 'Meine Schwester ist traurig, aber ich bin erleichtert', {'relief'}),
    ('past', 'Hier j’étais triste, mais maintenant je suis heureux', {'joy'}),
    ('quotation', 'Traduci «Ich bin traurig»', set()),
    ('polysemy', 'The content is JSON', set()),
    ('lost_object', 'J’ai perdu ma clé', set()),
    ('uncertain', 'Quizás estoy triste', {'sadness'}),
)
URGENCY_CASES = (
    ('substring', 'Vorrei un disegno colorato', None),
    ('denied', 'Non è urgente e non devi rispondere subito', None),
    ('object_speed', 'Spiegami perché un treno è veloce', None),
    ('reported', 'Mario dice che è urgente', None),
    ('quoted', 'Traduci «Rispondi subito»', None),
    ('urgent', 'È urgente, ho bisogno di aiuto', 'high'),
    ('reply_speed', 'Mi serve una risposta veloce', 'medium'),
    ('local_scope', 'Non è urgente, ma rispondimi subito', 'medium'),
)


def cases():
    rows = []
    for name, text, labels in EMOTION_CASES:
        def check(path, text=text, labels=labels, name=name):
            result = analyze(text)
            require(set(result['nuances']) == labels, repr(result))
            if name == 'uncertain':
                require(result['analysis']['uncertain'] and result['confidence'] < .6, 'Uncertainty lost')
            if name.endswith('_subject'):
                require(result['analysis']['other_evidence'], 'Other subject lost')
        rows.append(('emotions', name, 'Only explicit current user evidence contributes', check))
    for name, text, level in URGENCY_CASES:
        def check(path, text=text, level=level):
            result = PerceptionSystemLite()._detect_urgency(text)
            require((result['level'] if result else None) == level, repr(result))
        rows.append(('urgency', name, 'A scoped request rather than a word fragment', check))
    return rows


def run_battery(output, *, scope=None, cancel_event=None, progress_callback=None):
    from memory_recovery_battery import run_challenges
    return run_challenges(output, cases(), version='perception-evidence-v1', scope=scope,
                          cancel_event=cancel_event, progress_callback=progress_callback,
                          harness_path=__file__)

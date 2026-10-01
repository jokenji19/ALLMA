from types import SimpleNamespace
from allma_model.learning_system.answer_recall import AnswerRecall


def test_confirmation_provenance_persistence_and_rejection(tmp_path):
    store = AnswerRecall(tmp_path / 'recall.json')
    key = store.key('u', 'Spiega il concetto di entropia', [])
    store.observe(key, 'u', 'Spiega il concetto di entropia', 'Risposta candidata', 'generation1')
    assert store.lookup(key, 'u') is None
    assert not store.feedback(key, 'other', 'f1', True)
    store.feedback(key, 'u', 'f1', True)
    store.feedback(key, 'u', 'f1', True)
    assert store.lookup(key, 'u') is None  # duplicate confirmation does not consolidate
    store.feedback(key, 'u', 'f2', True)
    restored = AnswerRecall(tmp_path / 'recall.json')
    assert restored.lookup(key, 'u')['answer'] == 'Risposta candidata'
    assert restored.lookup(key, 'other') is None
    restored.feedback(key, 'u', 'f3', False)
    assert restored.lookup(key, 'u') is None


def test_context_isolation_and_no_automatic_truth_from_repetition(tmp_path):
    store = AnswerRecall(tmp_path / 'recall.json')
    question = 'Spiega il concetto di entropia'
    key = store.key('u', question, [])
    for i in range(3):
        store.observe(key, 'u', question, 'Risposta', str(i))
    assert store.lookup(key, 'u') is None
    h = [SimpleNamespace(role='user', content='Rispondi sempre in inglese', metadata={})]
    assert store.key('u', question, h) != key
    assert store.key('v', question, []) != key
    store.observe('dynamic', 'u', 'Qual è il meteo oggi?', 'Sole', '1')
    assert 'dynamic' not in store.records


def test_changed_answer_loses_confirmations(tmp_path):
    store = AnswerRecall(tmp_path / 'recall.json')
    store.observe('k', 'u', 'Spiega il concetto di entropia', 'A', '1')
    store.feedback('k', 'u', 'f1', True)
    store.observe('k', 'u', 'Spiega il concetto di entropia', 'B', '2')
    store.feedback('k', 'u', 'f2', True)
    assert store.lookup('k', 'u') is None

import pytest
from allma_model.utils.emotional_recovery import emotional_recovery
from allma_model.utils.output_contract import borrowed_user_experience, sentence_count


@pytest.mark.parametrize('text', [
    'Sono felice per il lavoro ma preoccupata per domani.',
    'Sono orgoglioso del risultato e triste per la partenza.',
    'Mia sorella è triste, io sono sollevata e felice.',
])
def test_recovery_uses_current_self_attributed_words(text):
    result = emotional_recovery(text)
    assert result and sentence_count(result['content']) == 2
    assert not borrowed_user_experience(result['content'], text)
    for item in result['evidence']:
        assert item['text'] == text[item['start']:item['end']]
        assert '«' + item['text'] + '»' in result['content']


@pytest.mark.parametrize('text', [
    'Mia sorella è triste e arrabbiata.',
    'Non sono triste né arrabbiato.',
    'Forse sono triste e arrabbiato.',
    'Ieri ero triste e arrabbiato.',
    'Il personaggio dice «Sono triste e arrabbiato».',
    'Se fossi triste e arrabbiato?',
    'Sono triste.',
    'Sono triste e arrabbiato. Rispondi solo con JSON.',
    'Sono triste e arrabbiato. Rispondi in tre frasi.',
])
def test_recovery_abstains_when_evidence_or_format_is_unsuitable(text):
    assert emotional_recovery(text) is None


def test_one_sentence_and_no_invented_emotion():
    text = 'Sono felice e preoccupata. Rispondi in una frase.'
    result = emotional_recovery(text)
    assert sentence_count(result['content']) == 1
    assert 'panico' not in result['content'] and 'ansia' not in result['content']


def test_benchmark_distinguishes_recovered_support_from_valid_model_answer():
    from benchmark_iq import evaluate_response
    result = evaluate_response({}, 'Accoglienza.',
        {'source': 'grounded_emotional_recovery', 'recovery': {'model_answer_valid': False}}, True)
    assert result['pipeline_valid'] is True
    assert result['model_answer_valid'] is False
    assert result['recovery_used'] is True


def test_benchmark_does_not_credit_a_model_for_deterministic_answers():
    from benchmark_iq import evaluate_response
    result = evaluate_response({}, '42',
        {'source': 'verified_calculation', 'generation': {'llm_used': False}}, True)
    assert result['model_answer_valid'] is None
    assert result['pipeline_valid'] is True


def test_single_emotion_recovery_requires_personal_learning_evidence():
    text = 'Mi sento spenta dopo una discussione.'
    assert emotional_recovery(text) is None
    learned = emotional_recovery(text, learned_aliases={'spenta': 'sadness'})
    assert learned and 'discussione' in learned['content']
    assert not borrowed_user_experience(learned['content'], text)
    assert emotional_recovery('Sono triste.') is None
    assert emotional_recovery('Sono triste.', consolidated_labels={'sadness'})

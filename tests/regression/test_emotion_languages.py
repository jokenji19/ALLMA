"""Explicit multilingual evidence with negative, subject and temporal controls."""
import pytest

from allma_model.emotional_system.emotion_analysis import analyze


@pytest.mark.parametrize('text,nuance', [
    ('Estoy feliz', 'joy'), ('Me siento triste', 'sadness'),
    ('Estoy preocupada', 'anxiety'), ('Tengo miedo', 'fear'),
    ('Estoy aliviado', 'relief'), ('Estoy enfadada', 'anger'),
    ('Me siento frustrado', 'frustration'), ('Estoy agradecida', 'gratitude'),
    ('Estoy orgulloso', 'pride'), ('Estoy cansada', 'fatigue'),
    ('Je suis heureux', 'joy'), ('Je suis contente', 'joy'),
    ('Je suis triste', 'sadness'), ('Je suis anxieuse', 'anxiety'),
    ("J’ai peur", 'fear'), ('Je suis soulagée', 'relief'),
    ('Je suis en colère', 'anger'), ('Je suis curieux', 'curiosity'),
    ('Je suis fatiguée', 'fatigue'), ('Je me sens perdu', 'confusion'),
    ('Je ne suis que triste', 'sadness'),
    ('Ich bin glücklich', 'joy'), ('Ich bin traurig', 'sadness'),
    ('Ich bin besorgt', 'anxiety'), ('Ich habe Angst', 'fear'),
    ('Ich bin erleichtert', 'relief'), ('Ich bin wütend', 'anger'),
    ('Ich bin neugierig', 'curiosity'), ('Ich bin dankbar', 'gratitude'),
    ('Ich fühle mich einsam', 'loneliness'), ('Ich bin müde', 'fatigue'),
])
def test_explicit_affect_in_five_language_detector(text, nuance):
    result = analyze(text)
    assert nuance in result['nuances']
    assert result['confidence'] >= .6
    assert result['analysis']['lexicon_languages'] == ['it', 'en', 'es', 'fr', 'de']


@pytest.mark.parametrize('text', [
    'No estoy triste', 'No tengo miedo', 'Nunca estoy enfadado',
    'No estoy feliz ni triste', 'Traduce estoy triste',
    'Mi hermana está triste', 'Ella está enfadada',
    'Ayer estaba triste', 'Si estuviera feliz',
    'Je ne suis pas triste', 'Je n’ai pas peur', 'Je ne suis plus triste',
    'Je ne suis ni heureux ni triste', 'Traduis je suis triste',
    'Elle est triste', 'Mon frère est inquiet', 'Hier j’étais triste',
    'Si je suis triste, que puis-je faire ?',
    'Ich bin nicht traurig', 'Ich habe keine Angst',
    'Ich bin weder froh noch traurig', 'Übersetze ich bin traurig',
    'Meine Schwester ist traurig', 'Er ist wütend',
    'Gestern war ich traurig', 'Wenn ich traurig bin',
    'She says «Je suis heureuse»', 'Elle dit „Ich bin traurig“',
    'The content is JSON', 'J’ai perdu ma clé', 'El duelo entre dos equipos',
    'La confiance du marché augmente', 'Le livre contient le mot heureux',
])
def test_multilingual_no_current_affect_without_personal_evidence(text):
    result = analyze(text)
    assert result['nuances'] == {}
    assert result['analysis']['uncertain']


@pytest.mark.parametrize('text', [
    'Mi hermana está triste, pero yo estoy feliz',
    'Elle est triste, mais je suis heureux',
    'Meine Schwester ist traurig, aber ich bin froh',
])
def test_multilingual_subject_changes_are_attributed(text):
    result = analyze(text)
    assert result['nuances'].keys() == {'joy'}
    assert any(row['label'] == 'sadness' for row in result['analysis']['other_evidence'])


@pytest.mark.parametrize('text', [
    'Ayer estaba triste, pero ahora estoy aliviada',
    'Hier j’étais triste, mais maintenant je suis soulagé',
    'Gestern war ich traurig, aber jetzt bin ich erleichtert',
])
def test_multilingual_current_state_does_not_include_past(text):
    result = analyze(text)
    assert result['nuances'].keys() == {'relief'}
    assert result['analysis']['past_evidence']


@pytest.mark.parametrize('text', [
    'Quizás estoy triste', 'Peut-être je suis triste', 'Vielleicht bin ich traurig',
])
def test_multilingual_uncertainty_is_preserved(text):
    result = analyze(text)
    assert result['nuances'].keys() == {'sadness'}
    assert result['analysis']['uncertain'] and result['confidence'] < .6


@pytest.mark.parametrize('text', [
    'No solo estoy feliz, también orgulloso',
    'Je ne suis pas seulement heureux, mais aussi fier',
    'Ich bin nicht nur glücklich, sondern auch stolz',
])
def test_multilingual_not_only_is_not_a_denial(text):
    assert analyze(text)['nuances'].keys() == {'joy', 'pride'}


def test_learned_alias_uses_the_same_language_scope_checks():
    aliases = {'nuvoloso': 'sadness'}
    assert analyze('Je me sens nuvoloso', aliases)['nuances'].keys() == {'sadness'}
    assert analyze('Je ne me sens pas nuvoloso', aliases)['nuances'] == {}
    assert analyze('Elle se sent nuvoloso', aliases)['nuances'] == {}


def test_repeated_intensifiers_do_not_inflate_confidence():
    assert analyze('Ich bin sehr sehr sehr traurig')['confidence'] == analyze('Ich bin traurig')['confidence']


@pytest.mark.parametrize('text,answer', [
    ('Mi hermana está triste, pero yo estoy aliviada', 'Tú sientes alivio, mientras tu hermana está triste.'),
    ('Elle est triste, mais je suis soulagée', 'Tu ressens du soulagement, tandis qu’elle est triste.'),
    ('Meine Schwester ist traurig, aber ich bin erleichtert', 'Du bist erleichtert, während deine Schwester traurig ist.'),
])
def test_multilingual_evidence_reaches_chat_without_a_second_model_call(tmp_path, text, answer):
    from unittest.mock import Mock
    from allma_model.core.allma_core import ALLMACore
    core = ALLMACore(mobile_mode=True, db_path=str(tmp_path / 'synthetic.db'))
    try:
        core._ensure_mobile_llm = lambda: None
        core._llm = Mock()
        core._llm.generate.return_value = answer
        core._llm.get_generation_meta.return_value = {'finish_reason': 'stop'}
        reply = core.process_message('SYNTHETIC_LANGUAGES', core.start_conversation('SYNTHETIC_LANGUAGES'), text)
        assert reply.is_valid
        state = reply.metadata['emotion_analysis']
        assert state['nuances'].keys() == {'relief'}
        assert state['context']['emotion_analysis']['other_evidence']
        core._llm.generate.assert_called_once()
        assert 'relief (sollievo)' in core._llm.generate.call_args.kwargs['prompt']
    finally:
        core.close()

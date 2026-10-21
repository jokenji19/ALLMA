"""Missing optional desktop models must not disable the mobile emotion path."""
from unittest.mock import Mock, patch

import pytest

from allma_model.core import context_understanding as context_module
from allma_model.core.nlp_processor import NLPProcessor


@pytest.mark.parametrize('text', ['I am happy', 'I feel sad', 'The sky is cloudy'])
def test_context_without_model_reports_unknown_with_zero_confidence(text):
    with patch.object(context_module, 'TRANSFORMERS_AVAILABLE', True), \
            patch.object(context_module, 'pipeline', create=True) as loader:
        context = context_module.ContextUnderstandingSystem(load_models=False)
    loader.assert_not_called()
    assert context.analyze_emotions(text) == {'label': 'unknown', 'score': 0.0}


def test_context_model_load_failure_is_explicitly_unknown():
    with patch.object(context_module, 'TRANSFORMERS_AVAILABLE', True), \
            patch.object(context_module, 'pipeline', side_effect=OSError('Missing model'), create=True):
        context = context_module.ContextUnderstandingSystem()
    assert context.emotion_detector is None
    assert context.analyze_emotions('I am happy') == {'label': 'unknown', 'score': 0.0}


@pytest.mark.parametrize('text', [None, '', 123])
def test_invalid_context_input_does_not_invoke_classifier(text):
    context = context_module.ContextUnderstandingSystem(load_models=False)
    context.emotion_detector = Mock()
    assert context.analyze_emotions(text) == {'label': 'unknown', 'score': 0.0}
    context.emotion_detector.assert_not_called()


def test_context_inference_failure_does_not_invent_an_emotion():
    context = context_module.ContextUnderstandingSystem(load_models=False)
    context.emotion_detector = Mock(side_effect=RuntimeError('Inference failed'))
    assert context.analyze_emotions('I am happy') == {'label': 'unknown', 'score': 0.0}
    context.emotion_detector.assert_called_once_with('I am happy')


@pytest.mark.parametrize('text', ['Sono felice', 'Sono triste', 'Oggi è giovedì'])
def test_legacy_nlp_missing_model_preserves_neutral_placeholder(text):
    # This old API has no confidence/unknown field: neutral is its compatibility
    # placeholder, not evidence of the user's emotional state. Mobile uses EmotionalCore.
    with patch('allma_model.core.nlp_processor.AutoTokenizer.from_pretrained',
               side_effect=OSError('Missing model')), \
            patch('allma_model.core.nlp_processor.AutoModelForSequenceClassification.from_pretrained') as loader:
        nlp = NLPProcessor()
    loader.assert_not_called()
    assert nlp.tokenizer is nlp.model is None
    scores = nlp.analyze_emotion(text)
    assert scores['neutral'] == 1.0
    assert scores['sentiment'] == 0.0
    assert all(value == 0.0 for key, value in scores.items() if key != 'neutral')


@pytest.mark.parametrize('text,expected,answer', [
    ('Sono felice ma preoccupata per domani.', {'joy', 'fear'},
     'Sei felice e preoccupata: entrambe le sensazioni possono coesistere.'),
    ('Non sono triste.', set(), 'Va bene, terrò conto di ciò che mi hai detto.'),
    ('Mia sorella è triste, io sono felice.', {'joy'},
     'Tu sei felice, mentre tua sorella è triste.'),
])
def test_mobile_turn_retains_local_emotion_analysis_without_transformers(tmp_path, text, expected, answer):
    from allma_model.core.allma_core import ALLMACore

    with patch('allma_model.core.nlp_processor.AutoTokenizer.from_pretrained') as tokenizer, \
            patch('allma_model.core.nlp_processor.AutoModelForSequenceClassification.from_pretrained') as model, \
            patch.object(context_module, 'pipeline', create=True) as classifier:
        core = ALLMACore(mobile_mode=True, db_path=str(tmp_path/'core.db'))
        try:
            core._ensure_mobile_llm = lambda: None
            core._llm = Mock()
            core._llm.generate.return_value = answer
            core._llm.get_generation_meta.return_value = {'finish_reason': 'stop'}
            result = core.process_message('u', core.start_conversation('u'), text)
            assert result.is_valid
            state = result.metadata['emotion_analysis']
            found = {state['primary_emotion'], *state['secondary_emotions']} - {'neutral'}
            assert found == expected
            assert state['context']['user_id'] == 'u'
            if not expected:
                assert state['confidence'] < .6
                assert state['context']['emotion_analysis']['uncertain']
                assert state['context']['emotion_analysis']['negated'][0]['label'] == 'sadness'
            assert core.context_system.emotion_detector is None
        finally:
            core.close()
    tokenizer.assert_not_called()
    model.assert_not_called()
    classifier.assert_not_called()

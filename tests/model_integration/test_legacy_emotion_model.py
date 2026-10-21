"""Real legacy desktop inference, separate from offline wiring tests.

Provision emotion_model.json's exact snapshot before running with
--run-model-integration. Missing weights are a failure, never a silent skip.
"""
import json
from pathlib import Path
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.model_integration


@pytest.fixture(scope='module')
def emotion_model():
    from transformers import AutoModelForSequenceClassification, AutoTokenizer
    spec = json.loads((Path(__file__).with_name('emotion_model.json')).read_text())
    options = dict(revision=spec['revision'], local_files_only=True)
    try:
        tokenizer = AutoTokenizer.from_pretrained(spec['repo_id'], **options)
        model = AutoModelForSequenceClassification.from_pretrained(spec['repo_id'], **options)
    except OSError as exc:
        pytest.fail(f"Pinned emotion snapshot is missing; provision {spec['repo_id']}@{spec['revision']} before running: {exc}")
    model.eval()
    assert model.config.id2label == {
        0: 'anger', 1: 'disgust', 2: 'fear', 3: 'joy',
        4: 'neutral', 5: 'sadness', 6: 'surprise',
    }
    return tokenizer, model


@pytest.mark.parametrize('text,label', [
    ('I am extremely happy and excited about this!', 'joy'),
    ('I am feeling very sad and depressed.', 'sadness'),
    pytest.param('The weather is cloudy today.', 'neutral', marks=pytest.mark.xfail(
        strict=True, raises=AssertionError,
        reason='Pinned legacy English model labels this neutral weather sentence as sadness; known model quality limit')),
])
def test_real_classifier_through_context_adapter(emotion_model, text, label):
    from transformers import pipeline
    from allma_model.core.context_understanding import ContextUnderstandingSystem
    tokenizer, model = emotion_model
    context = ContextUnderstandingSystem(load_models=False)
    context.emotion_detector = pipeline('text-classification', model=model, tokenizer=tokenizer, top_k=None, device=-1)
    with patch('allma_model.core.context_understanding.LANGDETECT_AVAILABLE', False):
        result = context.analyze_emotions(text)
    assert result['label'] == label
    assert result['score'] > .5


@pytest.mark.parametrize('text', [
    'Mi piace molto come mi aiuti a capire le cose.',
    'Sei molto brava a spiegare le cose.',
])
def test_real_classifier_through_legacy_nlp_adapter(emotion_model, text):
    # Preserve the two original integration expectations. This English model
    # plus the legacy adapter's Italian boosting is not a mobile quality metric.
    from allma_model.core.nlp_processor import NLPProcessor
    tokenizer, model = emotion_model
    with patch('allma_model.core.nlp_processor.AutoTokenizer.from_pretrained', return_value=tokenizer), \
            patch('allma_model.core.nlp_processor.AutoModelForSequenceClassification.from_pretrained', return_value=model):
        nlp = NLPProcessor()
    result = nlp.analyze_emotion(text)
    emotion = max((key for key in result if key != 'sentiment'), key=result.get)
    assert emotion == 'joy'

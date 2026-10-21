import json
import time
from unittest.mock import Mock

import pytest

from allma_model.emotional_system.emotional_core import EmotionalCore
from allma_model.emotional_system.emotion_analysis import analyze, prompt_context
from allma_model.core.emotional_adaptation_system import EmotionalAdaptationSystem


@pytest.mark.parametrize('text,family,nuance', [
    ('Sono felice', 'joy', 'joy'), ('Sono contenta', 'joy', 'joy'),
    ('Mi sento entusiasta', 'joy', 'excitement'), ('Sono orgogliosa', 'joy', 'pride'),
    ('Ti ringrazio di cuore', 'joy', 'gratitude'), ('Ti voglio bene', 'joy', 'love'),
    ('Mi sento sollevato', 'joy', 'relief'), ('Sono triste', 'sadness', 'sadness'),
    ('Mi sento sola', 'sadness', 'loneliness'), ('Nessuno mi ascolta', 'sadness', 'loneliness'),
    ('Mi manca mio padre', 'sadness', 'nostalgia'), ('Provo nostalgia', 'sadness', 'nostalgia'),
    ('Sono delusa', 'sadness', 'disappointment'), ('Mi sento impotente', 'sadness', 'helplessness'),
    ('Mi sento in colpa', 'sadness', 'guilt'), ('Mi vergogno', 'sadness', 'shame'),
    ('Sono imbarazzata', 'sadness', 'shame'), ('Sono furiosa', 'anger', 'anger'),
    ('Mi sento frustrato', 'anger', 'frustration'), ('Mi dà fastidio', 'anger', 'annoyance'),
    ('Sono gelosa', 'anger', 'jealousy'), ('Provo invidia', 'anger', 'jealousy'),
    ('Ho paura', 'fear', 'fear'), ('Mi sento ansiosa', 'fear', 'anxiety'),
    ('Sono preoccupata', 'fear', 'anxiety'), ('Mi sento insicuro', 'fear', 'insecurity'),
    ('Mi sento sopraffatta', 'fear', 'overwhelm'), ('Sono sorpreso', 'surprise', 'surprise'),
    ('Non ci credo', 'surprise', 'surprise'), ('Mi sento confusa', 'surprise', 'confusion'),
    ('Provo disgusto', 'disgust', 'disgust'), ('Mi fido di te', 'trust', 'trust'),
    ('Mi sento serena', 'trust', 'calm'), ('Mi sento rilassato', 'trust', 'calm'),
    ('Sono speranzosa', 'anticipation', 'hope'), ('Sono curiosa', 'anticipation', 'curiosity'),
    ('Mi sento motivato', 'anticipation', 'motivation'), ('Sono stanca', 'neutral', 'fatigue'),
    ('Mi sento vuota', 'neutral', 'numbness'),
    ('I am happy', 'joy', 'joy'), ('I feel anxious', 'fear', 'anxiety'),
    ('I am ashamed', 'sadness', 'shame'), ('I feel relieved', 'joy', 'relief'),
    ('😢', 'sadness', 'sadness'), ('😊', 'joy', 'joy'), ('🤢', 'disgust', 'disgust'),
])
def test_emotional_families_and_nuances(text, family, nuance):
    result = analyze(text)
    assert result['primary_emotion'] == family
    assert nuance in result['nuances']
    assert 0 <= result['confidence'] <= 1
    assert -1 <= result['valence'] <= 1
    assert 0 <= result['arousal'] <= 1


@pytest.mark.parametrize('text', [
    'Non sono triste', 'Non mi sento felice', 'Non ho paura', 'Sono senza paura',
    'Non sono più arrabbiato', 'Non sono molto triste',
    'Spiega la paura', 'Definisci la felicità', 'Traduci sono triste',
    'La parola triste significa qualcosa?', 'Scrivi una storia triste',
    'Mia sorella è triste', 'Lui è arrabbiato', 'Tu sei felice', 'Mario è triste',
    'Il protagonista si sente solo', 'Lei dice "Sono molto triste"',
    "Il libro dice 'Sono triste'", '«Sono felice» è una citazione',
    '```python\nprint("triste")\n```',
    'Se fossi felice', 'Quando sono triste cosa posso fare?', 'Vorrei essere felice',
    'Ieri ero triste', 'Rispondi solo con un numero', 'Mostra una emoji 😢',
    'Sono un solo utente', 'Questo è un contenitore', 'Un algoritmo contiene dati',
    'Che bello, si è rotto di nuovo', 'Ottimo, un altro crash',
    '', None,
])
def test_no_current_user_emotion_is_invented(text):
    result = analyze(text)
    assert result['primary_emotion'] == 'neutral'
    assert result['nuances'] == {}


def test_negation_has_local_scope_and_no_opposite_is_invented():
    result = analyze('Non sono triste ma preoccupato')
    assert result['primary_emotion'] == 'fear'
    assert 'joy' not in result['nuances']
    assert result['analysis']['negated'][0]['label'] == 'sadness'
    assert analyze('Non solo felice, ma anche orgogliosa')['primary_emotion'] == 'joy'
    assert analyze('Non posso non essere triste')['primary_emotion'] == 'sadness'


def test_mixed_emotions_and_local_intensity():
    result = analyze('Sono molto felice ma un po’ preoccupata')
    assert result['primary_emotion'] == 'joy'
    assert result['secondary_emotions'] == {'fear': .82}
    assert result['analysis']['mixed']
    assert result['nuances'].keys() == {'joy', 'anxiety'}
    assert analyze('Sono molto triste')['intensity'] > analyze('Sono poco triste')['intensity']
    assert analyze('Sono triste triste triste')['confidence'] == analyze('Sono triste')['confidence']


def test_other_people_and_past_are_distinct_from_user_now():
    result = analyze('Mia sorella è triste, io sono felice')
    assert result['primary_emotion'] == 'joy'
    assert 'sadness' not in result['secondary_emotions']
    assert result['analysis']['other_evidence'][0]['label'] == 'sadness'
    result = analyze('Prima ero triste, ora sono serena')
    assert result['primary_emotion'] == 'trust'
    assert result['analysis']['past_evidence'][0]['label'] == 'sadness'


def test_uncertainty_and_no_extra_model_invocation():
    core = EmotionalCore()
    llm = Mock()
    context = {'conversation_id': 'c', 'user_id': 'u'}
    state = core.process_interaction('Forse sono triste', context, llm)
    assert state.confidence < .6
    assert state.context['emotion_analysis']['uncertain']
    llm.assert_not_called(); llm.generate.assert_not_called()
    assert 'emotion_analysis' not in context
    assert core.get_intensity() == state.intensity
    assert core.get_user_emotional_state('u') is state
    assert 'ipotesi' in prompt_context(state)
    assert 'stato interno di ALLMA' in prompt_context(state)
    json.dumps(state.to_dict(), allow_nan=False)


def test_recent_reference_is_scoped_to_user_conversation_and_time():
    core = EmotionalCore()
    ctx = {'user_id':'u', 'conversation_id':'c'}
    first = core.process_interaction('Sono molto preoccupata', ctx)
    better = core.process_interaction('Sto meglio', ctx)
    assert better.intensity < first.intensity and better.primary_emotion == 'fear'
    assert better.confidence == .5
    assert core.process_interaction('Ancora così', {'user_id':'v','conversation_id':'c'}).nuances == {}
    assert core.process_interaction('Ancora così', {'user_id':'u','conversation_id':'different'}).nuances == {}
    old = core.process_interaction('Sono triste', ctx)
    old.context['observed_at'] = time.time()-601
    assert core.process_interaction('Ancora così', ctx).nuances == {}


def test_history_is_bounded_and_does_not_create_a_mood_for_unknown_user():
    core = EmotionalCore()
    assert core.get_user_emotional_state('new').confidence == 0
    for n in range(130):
        core.process_interaction('Sono felice', {'user_id':str(n),'conversation_id':'c'})
    assert len(core.emotion_history) == 128
    for _ in range(105):
        core.process_interaction('Sono felice', {'user_id':'last','conversation_id':'c'})
    assert len(core.emotion_history['last']) == 100


@pytest.mark.parametrize('data', [
    'not JSON fear joy', '[]', '{"e":"diagnosis","c":1,"i":1}',
    '{"e":"joy","c":NaN,"i":1}', '{"e":"joy","c":2,"i":1}',
    '{"e":"joy","c":true,"i":1}', '{"e":"joy","i":1}',
])
def test_explicit_llm_analysis_validates_schema_without_retry(data):
    core = EmotionalCore(); llm = Mock(return_value=data)
    state = core.detect_emotion_via_llm('Sono triste', llm)
    assert state.primary_emotion == 'sadness'
    llm.assert_called_once()


def test_explicit_llm_zero_confidence_is_not_replaced_with_default():
    state = EmotionalCore().detect_emotion_via_llm('Testo ambiguo', Mock(return_value='{"e":"neutral","c":0,"i":0}'))
    assert state.confidence == state.intensity == 0


def test_emotional_adaptation_is_gentle_and_mixed_and_never_shouts():
    core = EmotionalCore()
    state = core.detect_emotion('Sono triste ma anche felice')
    result = EmotionalAdaptationSystem().process('', {'emotional_state':state})
    assert any('miste' in s for s in result['system_instruction'])
    unclear = core.detect_emotion('Forse sono triste')
    hints = EmotionalAdaptationSystem().process('', {'emotional_state':unclear})['system_instruction']
    assert any('incerti' in s for s in hints)
    text = core.generate_emotional_response(core.detect_emotion('Sono molto preoccupata'), 'La tua frase.')
    assert 'La tua frase.' in text and 'Non preoccuparti' not in text
    assert 'Percepisco chiaramente' not in text


def test_user_valence_does_not_change_with_internal_chaos():
    core = EmotionalCore(); state = core.detect_emotion('Sono felice')
    valence = core._calculate_valence(state)
    state.entropy = 1
    assert core._calculate_valence(state) == valence


def test_long_inputs_have_bounded_evidence_and_no_unicode_crash():
    result = analyze(('Sono triste. '*1500)+'\x00')
    assert result['analysis']['truncated']
    assert len(result['analysis']['evidence']) <= 32
    assert analyze('SONO FELICE')['primary_emotion'] == 'joy'


def test_uncertain_emotion_does_not_change_personality_style():
    from allma_model.core.personality_adapter import PersonalityAdapterLite
    adapter = PersonalityAdapterLite()
    before = dict(vars(adapter.style))
    adapter.process('Forse sono triste', {'user_id':'u', 'emotional_state':EmotionalCore().detect_emotion('Forse sono triste')})
    assert vars(adapter.style) == before


def test_voice_replies_to_fear_and_anger_calmly():
    from allma_model.voice_system.voice_core import VoiceSystem
    # Avoid initializing microphone/TTS to verify just the tone mapping.
    voice = VoiceSystem.__new__(VoiceSystem)
    voice.base_pitch = voice.base_rate = 1.
    for family in ('fear', 'anger'):
        params = voice.get_voice_parameters(family, .9)
        assert params['rate'] <= 1.
        assert .9 <= params['pitch'] <= 1.1


def test_emotion_prompt_has_italian_labels_and_concrete_balanced_support():
    from allma_model.emotional_system.emotion_analysis import NUANCE_NAMES_IT, LEXICON, support_instruction
    state=EmotionalCore().detect_emotion('Sono felice ma anche preoccupata')
    text=prompt_context(state)
    assert 'joy (gioia)' in text and 'anxiety (ansia)' in text
    task=support_instruction(state)
    assert 'situazione descritta' in task and 'formato richiesto' in task
    assert 'ipotesi' in text and 'Non attribuirtele' in task
    assert 'tuoi sentimenti o partecipazioni' in task
    assert set(LEXICON) <= set(NUANCE_NAMES_IT)


def test_emotion_context_separates_other_people_and_negation_from_user():
    from allma_model.emotional_system.emotion_analysis import support_instruction
    state=EmotionalCore().detect_emotion('Mia sorella è triste, io non sono triste: sono sollevata.')
    data=prompt_context(state)
    assert 'relief (sollievo)' in data
    assert 'Altre persone: tristezza.' in data
    assert 'Negate dall’utente: tristezza.' in data
    assert 'Supporto:' not in data
    assert support_instruction(EmotionalCore().detect_emotion('Quanto fa 12 + 8?')) == ''


def test_mixed_tone_does_not_prioritize_only_negative_primary_emotion():
    state=EmotionalCore().detect_emotion('Sono molto preoccupata ma felice')
    result=EmotionalAdaptationSystem().process('Sono molto preoccupata ma felice',{'emotional_state':state})
    assert any('riconosci ciascuna emozione espressa' in s for s in result['system_instruction'])
    assert result['metadata']['adapted']


def test_positive_primary_with_negative_secondary_does_not_increase_humor():
    from allma_model.core.personality_adapter import PersonalityAdapterLite
    adapter=PersonalityAdapterLite()
    state=EmotionalCore().detect_emotion('Sono molto felice ma triste')
    before=adapter.style.humor
    result=adapter.process('Sono molto felice ma triste', {'user_id':'u','emotional_state':state})
    assert adapter.style.humor <= before
    assert 'umorismo' not in result['style_hint']


def test_default_style_does_not_add_empty_generic_prompt_directive():
    from allma_model.core.personality_adapter import PersonalityAdapterLite
    assert PersonalityAdapterLite().process('', {'user_id':'u'})['style_hint'] == ''


@pytest.mark.parametrize('text,family', [
    ('Non ho paura: mi sento serena','trust'),
    ('Io non sono felice: sono triste','sadness'),
    ('Mio fratello è arrabbiato: io sono sollevato','joy'),
    ('Non sono: triste','neutral'),
])
def test_new_self_statement_after_colon_has_its_own_negation_scope(text,family):
    assert analyze(text)['primary_emotion'] == family

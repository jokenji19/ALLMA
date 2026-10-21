from unittest.mock import patch
import pytest
from allma_model.core.emotional_growth import empty_state, evolve, aliases, view
from allma_model.core.personality_coalescence import CoalescenceProcessor, EmotionalState
from allma_model.emotional_system.emotion_analysis import analyze


def test_birth_has_no_learned_personal_emotion_history():
    state = empty_state()
    assert not view(state, 'u')['associations']
    assert not view(state, 'u')['personal_meanings']
    assert not view(state, 'u')['response_disposition']


def test_drop_suspends_then_coalesces_without_copying_user_emotion():
    state, report = evolve(empty_state(), 'u', '1', 'Sono triste per la partenza.')
    assert report['status'] == 'suspended'
    assert view(state, 'u')['trait_deltas']['empathy'] == 0
    duplicate, _ = evolve(state, 'u', '1', 'Sono triste per la partenza.')
    assert duplicate is state
    state, report = evolve(state, 'u', '2', 'Sono triste per la partenza.')
    assert report['status'] == 'suspended'
    assert view(state, 'u')['associations']['sadness']['observations'] == 1
    state, report = evolve(state, 'u', '3', 'Sono triste perché mi manca casa.')
    growth = view(state, 'u')
    assert report['status'] == 'integrated'
    assert 0 < growth['trait_deltas']['empathy'] < .01
    assert growth['response_disposition']['mode'] == 'care'
    assert growth['response_disposition']['subject'] == 'ALLMA_response_policy'
    assert not growth['response_disposition']['subjective_experience_verified']
    assert not view(state, 'other')['associations']


@pytest.mark.parametrize('text', ['Non sono triste', 'Mia sorella è triste',
    'Forse sono triste', 'Se fossi triste', 'Ieri ero triste',
    'Il personaggio dice «Sono triste».', 'Spiega la tristezza'])
def test_no_personality_growth_from_unattributed_or_uncertain_input(text):
    initial = empty_state()
    state, _ = evolve(initial, 'u', '1', text)
    assert state is initial


def test_personal_emotion_word_is_learned_and_scoped_not_a_global_override():
    state, report = evolve(empty_state(), 'u', '1', 'Per me "spenta" significa tristezza.')
    assert report['status'] == 'meaning_declared'
    learned = aliases(state, 'u')
    assert learned == {'spenta': 'sadness'}
    assert analyze('Mi sento spenta', learned)['primary_emotion'] == 'sadness'
    assert analyze('Mi sento spenta', aliases(state, 'other'))['primary_emotion'] == 'neutral'
    for text in ['Non mi sento spenta', 'La lampada è spenta', 'La lampada spenta',
                 'Mia sorella è spenta', 'Dice «Mi sento spenta».']:
        assert not analyze(text, learned)['nuances']
    state, _ = evolve(state, 'u', '2', 'Per me tristezza significa gioia.')
    assert 'tristezza' not in aliases(state, 'u')
    assert analyze('Sono triste', aliases(state, 'u'))['primary_emotion'] == 'sadness'
    state, _ = evolve(state, 'u', '3', 'Per me felice significa tristezza.')
    assert 'felice' not in aliases(state, 'u')
    assert analyze('Sono felice', aliases(state, 'u'))['primary_emotion'] == 'joy'


def test_meaning_correction_retracts_old_interpretations_and_tendency():
    state, _ = evolve(empty_state(), 'u', '1', 'Per me spenta significa tristezza.')
    state, _ = evolve(state, 'u', '2', 'Mi sento spenta al lavoro.')
    state, _ = evolve(state, 'u', '3', 'Mi sento spenta quando sono sola.')
    assert view(state, 'u')['trait_deltas']['empathy'] > 0
    state, _ = evolve(state, 'u', '4', 'Per me spenta significa gioia.')
    assert view(state, 'u')['trait_deltas']['empathy'] == 0
    assert not view(state, 'u')['response_disposition']
    assert analyze('Mi sento spenta', aliases(state, 'u'))['primary_emotion'] == 'joy'


def test_growth_restarts_and_survives_existing_feedback_snapshot(tmp_path):
    db = str(tmp_path/'state.db')
    processor = CoalescenceProcessor(db)
    processor.observe_interaction('u', '1', 'Per me spenta significa tristezza.')
    processor.observe_interaction('u', '2', 'Mi sento spenta al lavoro.')
    processor.observe_interaction('u', '3', 'Mi sento spenta quando sono sola.')
    before = processor.emotion_growth_view('u')
    processor.observe_feedback('u', 'answer1', True, ['emotion'])
    restored = CoalescenceProcessor(db)
    assert restored.emotion_growth_view('u') == before
    state = restored.get_current_personality_state(user_id='u')
    assert state['emotional_state']['primary'] == EmotionalState.EMPATHY
    assert state['emotional_state']['primary'] != EmotionalState.SADNESS
    assert restored.growth_instruction('u')
    assert not restored.growth_instruction('other')


def test_failed_growth_write_never_changes_live_state(tmp_path):
    processor = CoalescenceProcessor(str(tmp_path/'state.db'))
    before = processor.emotion_growth_view('u')
    with patch.object(processor._state_store, 'put', side_effect=OSError('disk full')):
        with pytest.raises(OSError):
            processor.observe_interaction('u', '1', 'Sono triste per la partenza.')
    assert processor.emotion_growth_view('u') == before


def test_lifelong_evidence_continues_after_recent_window_and_restart(tmp_path):
    processor = CoalescenceProcessor(str(tmp_path/'state.db'))
    for index in range(80):
        processor.observe_interaction('u', str(index), f'Sono triste per la giornata numero {index}.')
    growth = processor.emotion_growth_view('u')
    assert growth['associations']['sadness']['observations'] == 80
    assert len(growth['associations']['sadness']['contexts']) == 32
    assert len(growth['recent_droplets']) == 48
    assert growth['trait_deltas']['curiosity'] > 0
    restored = CoalescenceProcessor(str(tmp_path/'state.db'))
    restored.observe_interaction('u', 'next', 'Sono triste per una nuova partenza.')
    after = restored.emotion_growth_view('u')
    assert after['associations']['sadness']['observations'] == 81
    assert after['trait_deltas']['curiosity'] > growth['trait_deltas']['curiosity']


def test_correction_retracts_evicted_alias_evidence_but_keeps_direct_experience():
    state, _ = evolve(empty_state(), 'u', 'definition', 'Per me spenta significa tristezza.')
    for index in range(45):
        state, _ = evolve(state, 'u', str(index), f'Mi sento spenta dopo la giornata {index}.')
    for index in range(3):
        state, _ = evolve(state, 'u', f'direct{index}', f'Sono triste dopo il viaggio {index}.')
    state, _ = evolve(state, 'u', 'correction', 'Per me spenta significa gioia.')
    growth = view(state, 'u')
    assert growth['associations']['sadness']['observations'] == 3
    assert growth['trait_deltas']['empathy'] > 0


def test_personal_vocabulary_beyond_64_and_last_alias_recognized():
    state = empty_state()
    for index in range(80):
        state, report = evolve(state, 'u', str(index), f'Per me sensazione{index} significa gioia.')
        assert report['status'] == 'meaning_declared'
    assert len(view(state, 'u')['personal_meanings']) == 80
    assert analyze('Mi sento sensazione79', aliases(state, 'u'))['primary_emotion'] == 'joy'
    assert analyze('Mi sento sensazione79', aliases(state, 'other'))['primary_emotion'] == 'neutral'


def test_legacy_growth_migrates_only_known_evidence():
    state, _ = evolve(empty_state(), 'u', '1', 'Sono triste per la partenza.')
    state['profiles']['u']['associations']['sadness'].pop('evidence_counts')
    state, _ = evolve(state, 'u', '2', 'Sono triste per la separazione.')
    assert view(state, 'u')['associations']['sadness']['observations'] == 2

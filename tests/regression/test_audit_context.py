from datetime import datetime
from types import SimpleNamespace
from unittest.mock import Mock, patch
import json
import pytest
from allma_model.emotional_system.emotion_analysis import analyze
from allma_model.core.autobiographical_identity import history_eligible, history_content, POLICY_VERSION
from allma_model.core.dream_system.dream_manager import DreamManager


@pytest.mark.parametrize('text',[
    'Non sono felice, ma nemmeno triste.', 'Non sono felice e neanche triste.',
    'Non sono triste né arrabbiata.',
])
def test_coordinated_denial_does_not_assign_an_emotion(text):
    assert not analyze(text)['nuances']


@pytest.mark.parametrize('text',[
    "Mi manca l’aria per l’ansia dell’esame.", 'Mi manca il fiato.',
    'Mi manca il tempo per studiare.', 'Mi mancano due euro.',
])
def test_missing_resource_is_not_mourning_or_nostalgia(text):
    state = analyze(text)
    assert not {'grief','nostalgia'} & set(state['nuances'])


@pytest.mark.parametrize('text',[
    'Ho paura che tu creda che io sia felice.', 'Spero che tu pensi che io sia felice.',
    'Lei crede che io sia felice.',
])
def test_belief_complement_does_not_assert_joy(text):
    state = analyze(text)
    assert 'joy' not in state['nuances']


def test_partial_answer_is_context_only_and_explicitly_marked():
    msg = SimpleNamespace(role='assistant',content='Risposta incompleta perché',metadata={
        'is_valid':True,'identity_policy':POLICY_VERSION,'generation':{'status':'truncated_answer'}})
    assert not history_eligible(msg)
    assert history_eligible(msg,allow_incomplete=True)
    assert 'incompleta' in history_content(msg) and msg.content in history_content(msg)


def test_corrupt_dream_log_is_preserved_and_not_published_as_saved(tmp_path):
    path = tmp_path/'dream.json'
    path.write_text('[{"text":"truncated')
    manager = DreamManager(None,None,journal_path=str(path))
    original = path.read_bytes()
    manager.output_callback = Mock()
    assert manager._log_dream('Nuova riflessione','hypothesis') is False
    assert not manager.dream_history
    assert path.read_bytes() == original
    assert path.with_name('dream.json.invalid.bak').read_bytes() == original
    assert manager.output_callback.call_args.args[0]['content']['persisted'] is False
    path.write_text('[]')
    assert manager._load_dream_journal()
    assert manager._log_dream('Dopo il recupero') is True


def test_failed_dream_save_keeps_RAM_and_can_retry(tmp_path):
    manager = DreamManager(None,None,journal_path=str(tmp_path/'dream.json'))
    with patch.object(manager,'_save_dream_journal',side_effect=OSError('full')):
        assert manager._log_dream('Non salvato') is False
    assert not manager.dream_history
    manager._log_dream('Salvato')
    assert len(manager.dream_history) == 1


def test_failed_dream_save_and_unavailable_display_can_recover(tmp_path):
    manager = DreamManager(None, None, journal_path=str(tmp_path/'dream.json'))
    manager.output_callback = Mock(side_effect=RuntimeError('display closed'))
    with patch.object(manager, '_save_dream_journal', side_effect=OSError('full')):
        assert manager._log_dream('Non salvato') is False
    assert not manager.dream_history
    manager.output_callback = None
    assert manager._log_dream('Salvato dopo il ripristino') is True
    restored = DreamManager(None, None, journal_path=manager.journal_path)
    assert [row['text'] for row in restored.dream_history] == ['Salvato dopo il ripristino']


@pytest.mark.parametrize('archive', ['pending', 'processed'])
def test_corrupt_auxiliary_dream_archive_blocks_new_work_without_overwrite(tmp_path, archive):
    from allma_model.utils.persistence import StateRecoveryRequired
    journal = tmp_path/'dream.json'
    damaged = tmp_path/f'dream.json.{archive}.json'
    damaged.write_text('[truncated')
    llm = Mock()
    manager = DreamManager(None, None, llm_wrapper=llm, journal_path=str(journal))
    manager.current_user_id = 'u'
    assert archive in manager.archive_errors
    with pytest.raises(StateRecoveryRequired):
        manager._consolidate_insights(['Nuova ipotesi'])
    with pytest.raises(StateRecoveryRequired):
        manager.get_and_clear_pending_verification()
    manager._dream_cycle()
    llm.generate.assert_not_called()
    assert damaged.read_text() == '[truncated'
    assert damaged.with_name(damaged.name+'.invalid.bak').read_text() == '[truncated'

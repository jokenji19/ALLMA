from copy import deepcopy
from unittest.mock import Mock, patch
import pytest
from allma_model.core.cognitive_pipeline import CognitivePipeline, CognitiveValidationError
from allma_model.core.architecture.identity_state import IdentityStateEngine


@pytest.fixture
def core(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from allma_model.core.allma_core import ALLMACore
    instance = ALLMACore(mobile_mode=True, db_path=str(tmp_path/'core.db'))
    instance._ensure_mobile_llm = lambda: None
    instance._llm = Mock()
    instance._llm.get_generation_meta.return_value = {'finish_reason':'stop'}
    yield instance
    instance.close()


def test_candidate_preparation_does_not_commit_state():
    identity = Mock()
    validator = Mock()
    validator.validate.return_value = ('Testo valido',True,[])
    pipeline = CognitivePipeline(structural_core=validator, identity_engine_v5=identity)
    assert pipeline.process('Testo valido')[0] == 'Testo valido'
    identity.update_state.assert_not_called()


def test_validator_exception_is_not_a_pass():
    validator = Mock()
    validator.validate.side_effect = RuntimeError('unavailable')
    with pytest.raises(CognitiveValidationError):
        CognitivePipeline(structural_core=validator).process('unchecked')


def test_rejected_candidate_cannot_change_identity(core):
    core._llm.generate.return_value = 'Sono soddisfatto che tu abbia concluso il trasloco. Sono orgoglioso di aver condiviso questa fase con te.'
    before = (core.identity_engine_v5._maturity,core.identity_engine_v5._base_stability,
              core.identity_engine_v5.accepted_turns)
    reply = core.process_message('u',core.start_conversation('u'),
                                'Mia sorella è triste, io sono sollevata dopo il trasloco.')
    assert not reply.is_valid
    assert reply.metadata['generation']['status'] == 'subject_mismatch'
    assert (core.identity_engine_v5._maturity,core.identity_engine_v5._base_stability,
            core.identity_engine_v5.accepted_turns) == before


def test_real_turn_reports_validator_failure_without_learning(core):
    core._llm.generate.return_value = 'La luce bianca contiene diversi colori.'
    core.structural_core.validate = Mock(side_effect=RuntimeError('unavailable'))
    core.incremental_learner.learn_from_interaction = Mock()
    result = core.process_message('u',core.start_conversation('u'),'Spiega la luce bianca.')
    assert not result.is_valid
    assert result.metadata['generation']['status'] == 'validation_unavailable'
    assert result.metadata['validation']['status'] == 'unavailable'
    core.incremental_learner.learn_from_interaction.assert_not_called()
    assert not core.answer_recall.records


def test_failed_answer_storage_does_not_commit_identity(core):
    core._llm.generate.return_value = 'La luce bianca contiene diversi colori.'
    original = core.conversational_memory.store_message
    def store(*args,**kwargs):
        if kwargs.get('role') == 'assistant': raise OSError('full')
        return original(*args,**kwargs)
    core.conversational_memory.store_message = store
    before = core.identity_engine_v5.accepted_turns
    with pytest.raises(OSError): core.process_message('u',core.start_conversation('u'),'Spiega la luce bianca.')
    assert core.identity_engine_v5.accepted_turns == before


def test_failed_optional_recall_does_not_erase_a_valid_reply(core):
    core._llm.generate.return_value = 'La luce bianca contiene diversi colori.'
    with patch.object(core.answer_recall,'_save',side_effect=OSError('full')):
        result = core.process_message('u',core.start_conversation('u'),'Spiega la luce bianca.')
    assert result.is_valid and result.metadata['persistence']['answer_recall'] == 'failed'
    assert core.conversational_memory.messages[-1].content == result.content


def test_identity_save_failure_does_not_change_entropy_or_counters(tmp_path):
    identity = IdentityStateEngine(str(tmp_path/'core.db'))
    before = deepcopy(vars(identity.entropy_tracker)), identity._base_stability, identity.accepted_turns
    with patch.object(identity._store,'put',side_effect=OSError('full')):
        with pytest.raises(OSError): identity.update_state('Una risposta completa', [])
    assert (vars(identity.entropy_tracker), identity._base_stability, identity.accepted_turns) == before

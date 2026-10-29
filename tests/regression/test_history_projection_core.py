"""The full turn must not treat an unbacked or obsolete index row as memory."""
from unittest.mock import Mock
import pytest
from tests.regression.test_core_response import MemoryProbeEngine


@pytest.fixture
def core(tmp_path,monkeypatch):
    monkeypatch.chdir(tmp_path)
    from allma_model.core.allma_core import ALLMACore
    instance=ALLMACore(mobile_mode=True,db_path=str(tmp_path/'core.db'))
    instance._ensure_mobile_llm=lambda:None
    yield instance
    instance.close()


def test_unbacked_index_report_never_enters_the_native_prompt(core):
    conversation=core.start_conversation('u')
    core.decision_runtime.route=Mock(return_value={'status':'selected','choice':'memory'})
    core.conversational_memory.vector_engine.search=Mock(return_value=[{
        'content':'La passeggiata a Miraggio908 mi ha rilassato.',
        'metadata':{'role':'user','user_id':'u'},'score':.9,'timestamp':'2025-01-01T00:00:00'}])
    core._llm=MemoryProbeEngine('Non trovo un ricordo corrispondente.')
    result=core.process_message('u',conversation,'Quale passeggiata mi aveva rilassato?')
    assert result.metadata['decision']['action_cycle']['record_count']==0
    assert 'Miraggio908' not in str(core._llm.messages)


def test_corrected_authoritative_text_replaces_old_text_in_native_prompt(core):
    conversation=core.start_conversation('u')
    memory=core.conversational_memory
    memory.store_message('previous','La passeggiata a Portovenere mi ha rilassato.',{},'user','u')
    memory.messages[-1].content='La passeggiata a Monterosso mi ha rilassato.';memory.save_memory()
    core.decision_runtime.route=Mock(return_value={'status':'selected','choice':'memory'})
    core._llm=MemoryProbeEngine('Mi avevi parlato della passeggiata a Monterosso.')
    result=core.process_message('u',conversation,'Quale passeggiata mi aveva rilassato?')
    assert result.metadata['decision']['action_cycle']['record_count']==1
    assert 'Monterosso' in str(core._llm.messages) and 'Portovenere' not in str(core._llm.messages)

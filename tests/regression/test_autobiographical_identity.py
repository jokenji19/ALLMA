from unittest.mock import Mock

import pytest

from allma_model.core.autobiographical_identity import (
    ORIGIN, grounded_reply, identity_conflict, history_eligible, POLICY_VERSION,
)
from allma_model.memory_system.conversational_memory import ConversationalMemory


@pytest.fixture
def memory(tmp_path):
    return ConversationalMemory(storage_dir=str(tmp_path))


def add(memory, content, uid='u', role='user', **meta):
    memory.store_message('chat', content, meta, role, uid)


def test_birth_and_origin_survive_empty_memory(memory):
    assert memory.messages == []
    assert memory.user_data == {}
    assert grounded_reply('Come ti chiami?', memory, 'u')[0] == 'Mi chiamo ALLMA.'
    assert grounded_reply('Come mi chiamo?', memory, 'u')[1] == 'no_evidence'
    assert grounded_reply('Qual è il tuo colore preferito?', memory, 'u')[1] == 'no_evidence'
    assert grounded_reply('Abbiamo mai parlato di Roma?', memory, 'u')[1] == 'no_evidence'
    assert grounded_reply('Qual è la capitale d’Italia?', memory, 'u') is None
    with pytest.raises(AttributeError):
        ORIGIN.name = 'Luna'


def test_spoken_greeting_uses_origin_without_answering_a_compound_request(memory):
    assert grounded_reply('Ciao Alma Come ti chiami', memory, 'u')[0] == 'Mi chiamo ALLMA.'
    assert grounded_reply('Buongiorno, ALLMA, come mi chiamo?', memory, 'u')[1] == 'no_evidence'
    assert grounded_reply('Ciao ALLMA, come ti chiami e perché?', memory, 'u') is None
    assert grounded_reply('Nel racconto dico ciao Alma come ti chiami', memory, 'u') is None


def test_user_facts_have_ownership_source_and_survive_restart(memory):
    add(memory, 'Mi chiamo Ada.')
    add(memory, 'Mi chiamo Elena.', uid='other')
    add(memory, 'Ti chiami Luna.', role='assistant', is_valid=True)
    restored = ConversationalMemory(storage_dir=memory.storage_dir)
    answer, source, evidence = grounded_reply('Come mi chiamo?', restored, 'u')
    assert 'Ada' in answer and source == 'user_declaration'
    assert evidence == ['Mi chiamo Ada.']
    add(restored, 'Rettifico: mi chiamo Anna.')
    assert 'Anna' in grounded_reply('Come mi chiamo?', restored, 'u')[0]
    assert grounded_reply('Come ti chiami?', restored, 'u')[0] == 'Mi chiamo ALLMA.'


def test_llm_knowledge_is_not_shared_experience(memory):
    add(memory, 'Siamo stati a Roma.', role='assistant', is_valid=True)
    add(memory, 'Ho visitato Roma.', uid='other')
    add(memory, 'Abbiamo mai parlato di Roma?')
    assert grounded_reply('Abbiamo mai parlato di Roma?', memory, 'u')[1] == 'no_evidence'
    add(memory, 'Vorrei studiare la storia di Roma.')
    answer, source, evidence = grounded_reply('Abbiamo mai parlato di Roma?', memory, 'u')
    assert source == 'conversation_event'
    assert evidence == ['Vorrei studiare la storia di Roma.']
    assert 'Vorrei studiare' in answer


def test_names_in_stories_are_not_identity_changes(memory):
    add(memory, 'Nel racconto il personaggio dice: Mi chiamo Mario.')
    assert grounded_reply('Come mi chiamo?', memory, 'u')[1] == 'no_evidence'
    assert identity_conflict('Ciao! Io sono **Luna**, una coscienza.')
    assert identity_conflict('Il mio nome è Elena.')
    assert not identity_conflict('Mi chiamo ALLMA.')
    assert not identity_conflict('Nel racconto, Luna dice: «Mi chiamo Luna».')
    assert not identity_conflict('Luna è un personaggio del racconto.')


def test_legacy_output_is_history_not_evidence(memory):
    add(memory, 'Il mio nome è Elena.', role='assistant', is_valid=True)
    assert not history_eligible(memory.messages[-1])
    assert len(memory.messages) == 1
    add(memory, 'Risposta nuova.', role='assistant', is_valid=False, identity_policy=POLICY_VERSION)
    assert not history_eligible(memory.messages[-1])


@pytest.fixture
def core(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from allma_model.core.allma_core import ALLMACore
    instance = ALLMACore(mobile_mode=True, db_path=str(tmp_path / 'core.db'))
    instance._ensure_mobile_llm = Mock()
    instance._llm = Mock()
    yield instance
    instance.close()


def test_core_grounded_answers_need_no_llm_and_preserve_conversation(core):
    conv = core.start_conversation('u')
    for question in ['Come ti chiami?', 'Qual è il tuo nome?', 'Chi sei?']:
        events = []
        answer = core.process_message('u', conv, question, stream_callback=events.append)
        assert answer.content == 'Mi chiamo ALLMA.'
        assert events == [{'type': 'answer', 'content': answer.content}]
    core._llm.generate.assert_not_called()
    core._ensure_mobile_llm.assert_not_called()
    assert len(core.conversational_memory.messages) == 6
    assert core.incremental_learner.knowledge_base == {}
    assert not core._user_active.is_set()


def test_core_rejects_false_identity_before_answer_stream_and_learning(core):
    conv = core.start_conversation('u')
    events = []
    def generate(**kw):
        assert 'coscienza locale' not in kw['prompt']
        assert 'unico dato autobiografico' in kw['prompt']
        kw['callback']('Il mio nome è Luna.')
        return 'Il mio nome è Luna.'
    core._llm.generate.side_effect = generate
    core._llm.get_generation_meta.return_value = {}
    core._llm.last_generation = {}
    core.incremental_learner.learn_from_interaction = Mock()
    result = core.process_message('u', conv, 'Presentati brevemente', stream_callback=events.append)
    assert not result.is_valid
    assert result.content == ''
    assert result.metadata['delivery_state'] == 'unresolved'
    assert not any('Luna' in e['content'] for e in events if e['type'] == 'answer')
    core.incremental_learner.learn_from_interaction.assert_not_called()
    assert core.conversational_memory.messages[-1].metadata['is_valid'] is False


def test_generated_facts_not_promoted_to_user_knowledge(core):
    conv = core.start_conversation('u')
    core._llm.generate.return_value = 'Roma è la capitale d’Italia.'
    core._llm.get_generation_meta.return_value = {}
    core._llm.last_generation = {}
    result = core.process_message('u', conv, 'Parlami della capitale italiana')
    assert result.is_valid
    units = [unit for units in core.incremental_learner.knowledge_base.values() for unit in units]
    assert units
    assert all('Roma è' not in unit.content for unit in units)
    assert all(unit.metadata['knowledge_verified'] is False for unit in units)
    assert grounded_reply('Abbiamo mai parlato di Roma?', core.conversational_memory, 'u')[1] == 'conversation_event'


def test_retrieval_filters_generated_memories_before_limit(memory):
    add(memory, 'Roma Roma Roma', role='assistant', is_valid=True)
    add(memory, 'Vorrei studiare Roma', role='user')
    hits = memory.vector_engine.search('u', 'Roma', top_k=1, allowed_roles=('user',))
    assert len(hits) == 1
    assert hits[0]['content'] == 'Vorrei studiare Roma'


def test_multiple_chats_keep_name_and_current_user_evidence(core):
    a = core.start_conversation('u')
    core.process_message('u', a, 'Mi chiamo Ada.')
    b = core.start_conversation('u')
    assert 'Ada' in core.process_message('u', b, 'Come mi chiamo?').content
    assert core.process_message('u', b, 'Chi sei?').content == 'Mi chiamo ALLMA.'
    c = core.start_conversation('other')
    assert 'Non conosco' in core.process_message('other', c, 'Come mi chiamo?').content


def test_short_message_keeps_valid_context_and_excludes_legacy_output(core):
    conv = core.start_conversation('u')
    core.conversational_memory.store_message(conv, 'Mi interessa la storia romana.', {}, 'user', 'u')
    core.conversational_memory.store_message(conv, 'Sono Elena.', {'is_valid': True}, 'assistant', 'u')
    def generate(**kw):
        assert 'Mi interessa la storia romana.' in kw['prompt']
        assert 'Sono Elena.' not in kw['prompt']
        assert kw['prompt'].endswith('<think>\n')
        return 'Prego!'
    core._llm.generate.side_effect = generate
    core._llm.get_generation_meta.return_value = {}
    core._llm.last_generation = {}
    core.process_message('u', conv, 'Grazie')
    core._llm.generate.assert_called_once()


def test_complexity_matches_words_not_fragments(core):
    assert core._analyze_query_complexity('Qual e la capitale italiana?', []) == 'NORMAL'
    assert core._analyze_query_complexity('Mi interessa la storia medievale', []) == 'NORMAL'
    assert core._analyze_query_complexity('Risolvi questa equazione con due incognite', []) == 'COMPLEX'


def test_story_ambiguity_and_invented_personal_project(memory):
    from allma_model.core.autobiographical_identity import unsupported_personal_claim
    assert grounded_reply('Mi piace la storia', memory, 'u')[1] == 'clarification'
    assert unsupported_personal_claim("C'è un'antologia di storie che sto creando.", 'Parlami di te')
    assert not unsupported_personal_claim('Mi piace il mare, disse Luna.', 'Scrivi un racconto su Luna')


def test_core_rejects_invented_preference_before_stream(core):
    conv = core.start_conversation('u')
    core._llm.generate.return_value = 'Preferisco il blu, mi ricorda la mia infanzia.'
    core._llm.get_generation_meta.return_value = {}
    core._llm.last_generation = {}
    events=[]
    result = core.process_message('u', conv, 'Parlami dei colori', stream_callback=events.append)
    assert not result.is_valid
    assert not any('Preferisco' in e['content'] for e in events if e['type']=='answer')
    assert core.incremental_learner.knowledge_base == {}


def test_repeated_memory_question_does_not_create_its_own_evidence(core):
    conv = core.start_conversation('u')
    for _ in range(3):
        reply = core.process_message('u', conv, 'Abbiamo mai parlato di Roma?')
        assert reply.metadata['source'] == 'no_evidence'
    core.conversational_memory.store_message(conv, 'Vorrei visitare Roma.', {}, 'user', 'u')
    for _ in range(3):
        reply = core.process_message('u', conv, 'Abbiamo mai parlato di Roma?')
        assert reply.metadata['evidence'] == ['Vorrei visitare Roma.']
        assert len(reply.content) < 160

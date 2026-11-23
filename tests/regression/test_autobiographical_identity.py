from pathlib import Path
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


@pytest.mark.parametrize('text', [
    'Mi chiamo ALLMA, un modello linguistico. Tu hai detto il tuo nome.',
    'No, non sono timida. Sono un modello linguistico progettato per rispondere.',
    'I’m a large language model.',
    'Me llamo ALLMA, un modelo de lenguaje.',
])
def test_backend_cannot_take_the_identity_of_allma(text):
    assert identity_conflict(text)


@pytest.mark.parametrize('text', [
    'Mi chiamo ALLMA. Uso un modello linguistico per conversare.',
    'Il personaggio risponde: «Ciao! Sono un modello linguistico».',
    'La parola modello indica, qui, un modello linguistico.',
])
def test_backend_mentions_are_not_self_identification(text):
    assert not identity_conflict(text)


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
        assert answer.content.startswith('Mi chiamo ALLMA.')
        assert ('assistente' in answer.content) == (question == 'Chi sei?')
        assert events == [{'type': 'answer', 'content': answer.content}]
    core._llm.generate.assert_not_called()
    core._ensure_mobile_llm.assert_not_called()
    assert len(core.conversational_memory.messages) == 6
    assert core.incremental_learner.knowledge_base == {}
    assert not core._user_active.is_set()


def test_introduction_name_followup_and_style_stay_grounded(core):
    cid = core.start_conversation('u')
    turns = [
        ('Piacere io mi chiamo Ada', 'user_declaration'),
        ('Come mi chiamo?', 'user_declaration'),
        ('E tu come ti chiami?', 'origin_identity'),
        ('Mi piace il tuo nome', 'identity_name_reaction'),
        ('Sei timida?', 'personality_self_description'),
    ]
    answers = [core.process_message('u', cid, question) for question, _ in turns]
    assert [answer.metadata['source'] for answer in answers] == [source for _, source in turns]
    assert all(answer.is_valid and answer.content for answer in answers)
    assert 'Ada' in answers[0].content and 'Ada' in answers[1].content
    assert answers[2].content == 'Mi chiamo ALLMA.'
    assert answers[3].metadata['evidence'] == []
    assert 'modo personale di rispondere' in answers[4].content
    assert grounded_reply('A lei piace il tuo nome', core.conversational_memory, 'u') is None
    core._llm.generate.assert_not_called()


@pytest.mark.parametrize('question, reply', [
    ("And you, what's your name?", 'My name is ALLMA.'),
    ('¿Y tú, cómo te llamas?', 'Me llamo ALLMA.'),
    ('Et toi, comment t’appelles-tu ?', 'Je m’appelle ALLMA.'),
])
def test_name_followup_does_not_need_personal_history(memory, question, reply):
    assert grounded_reply(question, memory, 'u') == (reply, 'origin_identity', [])


@pytest.mark.parametrize('question, followup', [
    ('Chi ti ha progettato cosi?', 'Cosa vuol dire?'),
    ('Who designed you?', 'What do you mean?'),
    ('¿Quién te diseñó así?', '¿Qué significa eso?'),
])
def test_project_origin_followup_explains_learning_without_picking_up_the_name(core, question, followup):
    root = Path(__file__).resolve().parents[2]
    assert ORIGIN.name_expansion in (root / 'README.md').read_text()
    assert ORIGIN.rights_holder in (root / 'LICENSE').read_text()
    cid = core.start_conversation('u')
    reply = core.process_message('u', cid, 'Cosa significa il tuo nome?')
    assert ORIGIN.name_expansion in reply.content
    origin = core.process_message('u', cid, question)
    assert origin.metadata['source'] == 'project_origin'
    assert ORIGIN.rights_holder in origin.content
    explanation = core.process_message('u', cid, followup)
    assert explanation.metadata['source'] == 'project_origin_explanation'
    assert explanation.is_valid and explanation.content
    assert ORIGIN.name_expansion not in explanation.content and explanation.content != origin.content
    core._llm.generate.assert_not_called()


@pytest.mark.parametrize('questions,name_prefix', [
    (('Sai chi sei?', 'E cosa significa il tuo nome?', 'Ti piace il tuo nome?'), 'Mi chiamo'),
    (('Who are you?', 'And what does your name mean?', 'Do you like your name?'), 'My name is'),
    (('¿Sabes quién eres?', '¿Y qué significa tu nombre?', '¿Te gusta tu nombre?'), 'Me llamo'),
    (('Sais-tu qui tu es ?', 'Et que veut dire ton nom ?', 'Aimes-tu ton nom ?'), 'Je m’appelle'),
    (('Wer bist du?', 'Was bedeutet dein Name?', 'Magst du deinen Namen?'), 'Ich heiße'),
    (('Quem é você?', 'E o que significa o seu nome?', 'Você gosta do seu nome?'), 'O meu nome é'),
    (('Ты знаешь, кто ты?', 'И что означает твоё имя?', 'Тебе нравится твоё имя?'), 'Меня зовут'),
    (('هل تعرف من أنت؟', 'وما معنى اسمك؟', 'هل يعجبك اسمك؟'), 'اسمي'),
    (('你知道你是谁吗？', '你的名字是什么意思？', '你喜欢自己的名字吗？'), '我叫'),
    (('自分が誰か知っていますか？', 'あなたの名前の意味は何ですか？', '自分の名前が好きですか？'), '私の名前は'),
])
def test_questions_about_origin_and_name_preference_ignore_public_biography(core, questions, name_prefix):
    cid = core.start_conversation('u')
    memory = core.conversational_memory
    memory.store_message(cid, '¿Quién es Zlatan Ibrahimović?', {}, 'user', 'u')
    memory.store_message(cid, 'Zlatan es un futbolista sueco.',
        {'identity_policy': POLICY_VERSION, 'source': 'reference_excerpt'}, 'assistant', 'u')
    answers = [core.process_message('u', cid, question) for question in questions]
    assert answers[0].content.startswith(name_prefix)
    assert [reply.metadata['source'] for reply in answers] == ['origin_identity', 'origin_identity', 'no_evidence']
    assert all('ALLMA' in reply.content and 'Zlatan' not in reply.content for reply in answers)
    assert memory.messages[1].content.startswith('Zlatan')
    core._llm.generate.assert_not_called()


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
    role = core.process_message('u', b, 'Chi sei?').content
    assert role.startswith('Mi chiamo ALLMA.') and 'assistente' in role
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

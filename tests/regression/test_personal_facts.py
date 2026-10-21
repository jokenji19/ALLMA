from types import SimpleNamespace

import pytest

from allma_model.utils.personal_facts import personal_reply
from allma_model.core.autobiographical_identity import grounded_reply
from allma_model.memory_system.conversational_memory import ConversationalMemory


def recall(question, *history, profile=None):
    return personal_reply(question, [SimpleNamespace(content=t) for t in history], 'u', profile)


@pytest.mark.parametrize('slot,old,new,question', [
    ('name', 'Mi chiamo Ada.', 'Rettifico: mi chiamo Anna.', 'Come mi chiamo?'),
    *[(slot, f'Il mio {slot} preferito è A.', f'Ora il mio {slot} preferito è B.',
       f'Qual è il mio {slot} preferito?') for slot in ('colore','cibo','film','libro','animale','sport')],
])
def test_explicit_update_and_plain_conflict(slot,old,new,question):
    current = 'Anna' if slot == 'name' else 'B'
    result = recall(question,old,new)
    assert current in result[0] and result[1] == 'user_declaration'
    plain = new.removeprefix('Rettifico: ').removeprefix('Ora ')
    conflict = recall(question,old,plain)
    assert conflict[1] == 'personal_fact_clarification'


@pytest.mark.parametrize('question,old,withdraw,new', [
    ('Come mi chiamo?', 'Mi chiamo Ada.', 'Non usare più il mio nome.', 'Ora mi chiamo Anna.'),
    ('Qual è il mio colore preferito?', 'Il mio colore preferito è blu.',
     'Non ho più un colore preferito.', 'Ora il mio colore preferito è verde.'),
    ('Qual è il mio film preferito?', 'Il mio film preferito è Arrival.',
     'Revoco il mio film preferito.', 'Rettifico: il mio film preferito è Dune.'),
])
def test_revocation_blocks_old_repetition_until_explicit_update(question,old,withdraw,new):
    assert recall(question,old,withdraw,old)[1] == 'personal_fact_revoked'
    assert recall(question,old,withdraw,new)[1] == 'user_declaration'


def test_likes_are_not_favorites_and_negative_color_removes_only_that_like():
    history = ('Mi piace il blu.', 'Mi piace il verde.', 'Non mi piace più il blu.')
    result = recall('Quali colori mi piacciono?', *history)
    assert 'verde' in result[0] and 'blu' not in result[0]
    assert recall('Qual è il mio colore preferito?', *history)[1] == 'no_evidence'
    assert recall('Qual è il mio colore preferito?', 'Il mio colore preferito è blu.', *history)[0].endswith('blu.')


@pytest.mark.parametrize('unrelated', [
    'Mia sorella si chiama Anna.', 'Il colore preferito di mia sorella è verde.',
    '"Mi chiamo Anna."', 'Se mi chiamo Anna, cosa rispondi?',
    'Immagina che il mio colore preferito sia verde.',
    'Nel sogno mi chiamo Anna.', 'Per esempio: il mio colore preferito è verde.',
])
def test_third_person_quotes_hypotheses_are_not_personal_declarations(unrelated):
    assert recall('Come mi chiamo?', unrelated)[1] == 'no_evidence'
    assert recall('Qual è il mio colore preferito?', unrelated)[1] == 'no_evidence'
    assert personal_reply(unrelated, [], 'u') is None


@pytest.mark.parametrize('old,unclear,question', [
    ('Mi chiamo Ada.', 'Rettifico: il mio nome forse è Anna.', 'Come mi chiamo?'),
    ('Mi chiamo Ada.', 'Non mi chiamo Ada.', 'Come mi chiamo?'),
    ('Il mio colore preferito è blu.', 'Il mio colore preferito non è blu.', 'Qual è il mio colore preferito?'),
])
def test_unsupported_correction_does_not_resurrect_stale_data(old,unclear,question):
    assert recall(question, old, unclear)[1] == 'personal_fact_clarification'


def test_profile_cannot_restore_a_revoked_name_or_cross_user_boundary():
    profile = SimpleNamespace(user_id='u', name='Ada')
    assert recall('Come mi chiamo?', profile=profile)[1] == 'user_profile'
    assert recall('Come mi chiamo?', 'Non usare più il mio nome.', profile=profile)[1] == 'personal_fact_revoked'
    assert recall('Come mi chiamo?', profile=SimpleNamespace(user_id='other',name='Anna'))[1] == 'no_evidence'


def test_real_archive_reload_ownership_role_validity_and_independent_fields(tmp_path):
    folder = str(tmp_path/'personal')
    memory = ConversationalMemory(storage_dir=folder)
    for text in ('Mi chiamo Ada.', 'Il mio colore preferito è blu.',
                 'Rettifico: mi chiamo Anna.', 'Ora il mio colore preferito è verde.'):
        memory.store_message('old',text,{},'user','u')
    memory.store_message('other','Mi chiamo Elena.',{},'user','other')
    memory.store_message('other','Il mio colore preferito è rosso.',{},'user','other')
    memory.store_message('old','Mi chiamo Modello.',{},'assistant','u')
    memory.store_message('old','Ora il mio colore preferito è nero.',{'is_valid':False},'user','u')
    memory.save_memory()
    restored = ConversationalMemory(storage_dir=folder)
    assert 'Anna' in grounded_reply('Come mi chiamo?',restored,'u')[0]
    assert 'verde' in grounded_reply('Qual è il mio colore preferito?',restored,'u')[0]
    assert 'Elena' in grounded_reply('Come mi chiamo?',restored,'other')[0]
    assert grounded_reply('Come mi chiamo?',restored,'unknown')[1] == 'no_evidence'
    restored.store_message('new','Non usare più il mio nome.',{},'user','u')
    restored.save_memory()
    again = ConversationalMemory(storage_dir=folder)
    assert grounded_reply('Come mi chiamo?',again,'u')[1] == 'personal_fact_revoked'
    assert 'verde' in grounded_reply('Qual è il mio colore preferito?',again,'u')[0]
    assert grounded_reply('Come ti chiami?',again,'u')[0] == 'Mi chiamo ALLMA.'


@pytest.mark.parametrize('question', ['Ti ricordi il mio nome?', 'Ricordi come mi chiamo?',
    'Mi puoi ricordare come mi chiamo?', 'Per favore, dimmi il mio nome.'])
def test_name_paraphrases_share_revocation_policy(question):
    assert recall(question,'Mi chiamo Ada.','Non usare più il mio nome.')[1]=='personal_fact_revoked'


@pytest.mark.parametrize('question', ['Ti ricordi il mio colore preferito?',
    'Mi puoi ricordare il mio colore preferito?', 'Puoi ricordarmi il mio colore preferito?'])
def test_favorite_paraphrases_use_same_source(question):
    assert 'verde' in recall(question,'Il mio colore preferito è blu.',
                            'Il mio colore preferito ora è verde.')[0]


@pytest.mark.parametrize('statement', ['Il mio nome ora è Anna.', 'Il mio nome è adesso Anna.'])
def test_inline_name_updates(statement):
    assert 'Anna' in recall('Come mi chiamo?','Mi chiamo Ada.',statement)[0]


def test_projection_contains_current_values_only_and_omits_unrelated_active_facts():
    from allma_model.utils.personal_facts import PersonalFacts
    facts=PersonalFacts([SimpleNamespace(content=t) for t in (
        'Mi chiamo Ada.', 'Rettifico: mi chiamo Anna.',
        'Il mio colore preferito è blu.', 'Non ho più un colore preferito.')])
    prompt=facts.prompt()
    assert 'Anna' in prompt and 'Ada' not in prompt and 'blu' not in prompt
    assert facts.data()['colore']=={'status':'revoked'}
    assert 'Anna' not in facts.prompt(include_values=False)
    assert facts.prompt(include_values=False)==''
    assert 'revoked' not in prompt and 'stato' not in prompt.lower()


def test_projection_cache_version_tracks_controls_not_repeated_queries():
    from allma_model.utils.personal_facts import PersonalFacts
    def view(*texts): return PersonalFacts([SimpleNamespace(content=t) for t in texts])
    initial=view('Mi chiamo Ada.')
    assert initial.version()==view('Mi chiamo Ada.','Come mi chiamo?').version()
    assert initial.version()!=view('Mi chiamo Ada.','Non usare più il mio nome.').version()
    assert 'Ada' not in view('Mi chiamo Ada.','Mi chiamo Anna.').prompt()


def test_projection_filters_only_recognized_personal_reports_and_acks():
    from allma_model.utils.personal_facts import PersonalFacts
    facts=PersonalFacts([SimpleNamespace(content=t) for t in ('Mi chiamo Ada.','Non usare più il mio nome.')])
    history=[SimpleNamespace(role='user',content='Mi chiamo Ada.',metadata={}),
             SimpleNamespace(role='assistant',content='Piacere, Ada.',
                             metadata={'source':'user_declaration','evidence':['Mi chiamo Ada.']}),
             SimpleNamespace(role='user',content='Mia sorella si chiama Ada.',metadata={}),
             SimpleNamespace(role='user',content='La passeggiata al mare mi ha rilassato.',metadata={})]
    assert facts.filter_history(history)==history[2:]
    records=[{'content':turn.content} for turn in history if turn.role=='user']
    assert facts.filter_records(records)==records[1:]
    assert len(history)==4 and len(records)==3  # Projection never mutates stored events.


def test_revoked_name_cannot_return_via_legacy_assistant_direct_address():
    from allma_model.utils.personal_facts import PersonalFacts
    facts=PersonalFacts([SimpleNamespace(content=t) for t in ('Mi chiamo Ada.','Non usare più il mio nome.')])
    def turn(text): return SimpleNamespace(role='assistant',content=text,metadata={})
    history=[turn('Ciao Ada, come posso aiutarti?'), turn('Mi hai detto che ti chiami Ada.'),
             turn('Il personaggio incontra Ada nel racconto.'), turn('Nel testo si legge «Ciao Ada».')]
    assert facts.filter_history(history)==history[2:]
    assert 'Ada' not in facts.prompt()


def test_changed_name_filters_legacy_old_address_but_preserves_current_address():
    from allma_model.utils.personal_facts import PersonalFacts
    facts=PersonalFacts([SimpleNamespace(content=t) for t in ('Mi chiamo Ada.','Ora mi chiamo Lia.')])
    history=[SimpleNamespace(role='assistant',content=t,metadata={}) for t in ('Buongiorno Ada.', 'Buongiorno Lia.')]
    assert facts.filter_history(history)==history[1:]

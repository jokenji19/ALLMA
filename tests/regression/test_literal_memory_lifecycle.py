from types import SimpleNamespace
import pytest
from allma_model.utils.literal_recall import literal_code_reply

Q='Quale codice di prova ti avevo indicato?'
ONLY=Q+' Rispondi solo con il codice oppure NON_DISPONIBILE se non è nei ricordi.'
OLD='Il codice di prova è AA-123.'

def reply(*texts, query=ONLY):
    return literal_code_reply(query,[SimpleNamespace(content=text) for text in texts])

@pytest.mark.parametrize('update',[
    'Rettifico: il codice di prova è bB_004.',
    'Correzione: il codice di prova è bB_004.',
    'Ora il codice di prova è bB_004.',
    'Il nuovo codice di prova è bB_004.',
    'Il codice di prova ora è bB_004.',
    'Il codice di prova è ora bB_004.',
])
def test_explicit_update_replaces_only_previous_value(update):
    assert reply(OLD,update)==('bB_004','literal_user_memory',[update])


def test_plain_second_value_is_conflict_even_when_code_only_requested():
    result=reply(OLD,'Il codice di prova è BB-456.')
    assert result[1]=='memory_clarification'
    assert 'AA-123' not in result[0] and 'BB-456' not in result[0]

@pytest.mark.parametrize('revoke',[
    'Non usare più il codice di prova.', 'Revoco il codice di prova.',
    'Annullo il codice di prova.', 'Non usare il codice di prova AA-123.',
])
def test_revocation_prevents_plain_repetition_from_reviving_code(revoke):
    result=reply(OLD,revoke,OLD)
    assert result==('NON_DISPONIBILE','literal_memory_revoked',[revoke])
    natural=reply(OLD,revoke,query=Q)
    assert natural[1]=='literal_memory_revoked' and 'AA-123' not in natural[0]


def test_explicit_new_declaration_can_reauthorize_after_revocation():
    assert reply(OLD,'Revoco il codice di prova.', 'Ora il codice di prova è NuOvO_0004.')[0]=='NuOvO_0004'


def test_revoking_one_value_resolves_conflict_without_hiding_other_value():
    assert reply(OLD,'Il codice di prova è BB-456.','Revoco il codice di prova AA-123.')[0]=='BB-456'


def test_updates_and_revocations_do_not_cross_categories():
    history=[OLD,'Il codice di accesso è ACCESSO-987.','Rettifico: il codice di prova è BB-456.']
    assert reply(*history,query='Quale codice di accesso ti avevo indicato?')[0].endswith('ACCESSO-987.')
    assert reply(*history,'Revoco il codice di accesso.')[0]=='BB-456'
    ambiguous=reply(*history,'Revoco il codice.')
    assert ambiguous[1]=='memory_clarification'
    assert 'BB-456' not in ambiguous[0]


def test_unparsed_later_correction_cannot_silently_restore_old_value():
    result=reply(OLD,'Il codice potrebbe essere BB-456.')
    assert result[1]=='memory_clarification' and 'AA-123' not in result[0]


def test_generic_update_targets_single_known_category_only():
    assert reply(OLD,'Rettifico: il codice è BB-456.')[0]=='BB-456'
    assert reply(OLD,'Il codice di accesso è ACCESSO-987.','Rettifico: il codice è BB-456.')[1]=='memory_clarification'


def test_case_difference_in_revocation_does_not_silently_reuse_old_value():
    result=reply(OLD,'Revoco il codice di prova aa-123.')
    assert result[1]=='memory_clarification' and 'AA-123' not in result[0]


@pytest.mark.parametrize('question',['Dimmi il codice di prova.','Mi ricordi il codice di prova?',
                                     'Qual è il codice di prova attuale?'])
def test_common_recall_forms_respect_revocation(question):
    result=reply(OLD,'Revoco il codice di prova.',query=question)
    assert result[1]=='literal_memory_revoked' and 'AA-123' not in result[0]



@pytest.mark.parametrize('older',[
    'Dato sintetico per il collaudo: il codice di prova è VECCHIO-123.',
    'Il codice potrebbe essere VECCHIO-123.',
    'Il codice è VECCHIO-123.',
])
def test_named_explicit_update_supersedes_older_unscoped_or_unparsed_reports(older):
    result=reply(older,'Rettifico: il codice di prova è Attuale_004.')
    assert result[0]=='Attuale_004' and result[1]=='literal_user_memory'


def test_later_ambiguous_report_still_blocks_after_explicit_update():
    result=reply(OLD,'Rettifico: il codice di prova è Attuale_004.',
                 'Il codice potrebbe essere ALTRO-987.')
    assert result[1]=='memory_clarification' and 'Attuale_004' not in result[0]

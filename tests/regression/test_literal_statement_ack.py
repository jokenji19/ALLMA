import pytest
from allma_model.utils.literal_recall import literal_statement_reply

@pytest.mark.parametrize('message,answer,source',[
    ('Il codice di prova è TEST-123.','Hai indicato il codice di prova: TEST-123.','literal_user_declaration_ack'),
    ('Rettifico: il codice di prova e NuOvO_004.','Ho ricevuto la correzione del codice di prova: NuOvO_004.','literal_user_update_ack'),
    ('Il nuovo codice di accesso è 000015.','Ho ricevuto la correzione del codice di accesso: 000015.','literal_user_update_ack'),
    ('Non usare più il codice di prova.','Ho ricevuto la revoca del codice di prova.','literal_user_revocation_ack'),
    ('Revoco il codice di prova TEST-123.','Ho ricevuto la revoca del codice indicato.','literal_user_revocation_ack'),
])
def test_statement_ack_copies_only_current_statement(message,answer,source):
    assert literal_statement_reply(message)==(answer,source,[message])

@pytest.mark.parametrize('message',[
    '"Rettifico: il codice è TEST-123."',
    'Per esempio il codice è TEST-123.',
    'Il codice non è TEST-123.',
    'Il codice è scaduto.',
    'Rettifico: il codice è TEST-123. Puoi spiegarmelo?',
    'Dimentica tutti i ricordi.',
])
def test_quotes_negations_other_tasks_and_deletion_are_not_acknowledged_as_applied(message):
    assert literal_statement_reply(message) is None

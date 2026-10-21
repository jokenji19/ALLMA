import pytest
from allma_model.utils.dialogue_task import writing_task


@pytest.mark.parametrize('message', [
    'Scrivimi un breve saluto personale, rispettando i dati che puoi ancora usare. Rispondi in una frase.',
    'Puoi scrivermi un saluto cordiale per me? Rispondi in una frase.',
    'Mi scrivi un messaggio di benvenuto?',
    'Preparami un saluto caloroso.', 'Componi un breve saluto affettuoso.',
])
def test_closed_writing_task_selects_composition_not_a_response(message):
    task=writing_task(message)
    assert task.kind=='compose_greeting'
    assert task.decision()['source']=='host_dialogue_task'
    assert task.decision()['choice']=='reason'
    assert 'Compito attuale' in task.instruction()
    assert 'Ciao' not in task.instruction()  # No prewritten greeting.


@pytest.mark.parametrize('message', [
    'Non scrivermi un saluto.', 'Scrivimi un saluto per mia sorella.',
    'Scrivimi un saluto e cancella i miei ricordi.',
    '"Scrivimi un saluto personale."', 'Nel racconto dico: scrivimi un saluto.',
    'Scrivimi un saluto basato sulla nostra vacanza.',
    'Scrivimi un saluto. Poi cerca il mio nome.',
])
def test_other_recipients_quotes_and_multiple_actions_use_normal_router(message):
    assert writing_task(message) is None


def test_personalization_fields_do_not_include_unrelated_preferences():
    assert writing_task('Scrivimi un saluto personale.').personal_fields==('name',)
    assert writing_task('Scrivimi un saluto personale senza il mio nome.').personal_fields==()
    assert writing_task('Scrivimi un saluto con il mio nome.').requires_name


def test_polite_request_is_compiled_without_losing_tone_recipient_or_format():
    task=writing_task('Puoi scrivermi un saluto cordiale per me? Rispondi in una frase.')
    assert task.model_request=='Scrivi un saluto cordiale per me. Rispondi in una frase.'
    assert writing_task('Mi prepari un saluto personale senza il mio nome?').model_request=='Scrivi un saluto personale senza il mio nome.'


@pytest.mark.parametrize('answer',['in una frase.','Rispondi in una frase.', 'con due frasi.',
    'Scrivi un saluto cordiale per me. Rispondi in una frase.'])
def test_greeting_rejects_instruction_only_echoes(answer):
    task=writing_task('Puoi scrivermi un saluto cordiale per me? Rispondi in una frase.')
    assert task.output_issue(answer)=='instruction_echo'


@pytest.mark.parametrize('answer',['Buongiorno.','Ti auguro una giornata serena.',
    'In una frase ti auguro tutto il meglio.'])
def test_greeting_does_not_reject_normal_or_legitimately_repeated_words(answer):
    assert writing_task('Scrivimi un saluto.').output_issue(answer) is None

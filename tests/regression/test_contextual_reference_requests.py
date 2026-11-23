from types import SimpleNamespace

import pytest

from allma_model.utils.contextual_references import contextual_reference_request


def sourced_turn(title, *, source='reference_excerpt', url=None):
    return SimpleNamespace(role='assistant', metadata={
        'is_valid': True, 'source': source,
        'reference_review': {'basis': 'reference_text', 'truth_verified': False, 'citation': {
            'title': title, 'url': url or 'https://it.wikipedia.org/wiki/' + title.replace(' ', '_'),
            'provider': 'wikipedia', 'revision': 7,
        }},
    })


@pytest.mark.parametrize('question,title,relevant,decoy', [
    ('Contro chi ha fatto scoppiare la seconda guerra mondiale ?', None,
     'Giunse a invadere la Polonia il 1º settembre 1939, provocando così lo scoppio della seconda guerra mondiale.',
     'Iniziata la seconda guerra mondiale, la Germania invase la Francia con diverse divisioni nel 1940.'),
    ('Contro chi ha fatto scoppiare la seconda guerra mondiale ?', None,
     'La seconda guerra mondiale iniziò con l’invasione tedesca della Polonia il 1º settembre 1939.',
     'La seconda guerra mondiale iniziò nel 1939 e in seguito la Germania invase la Francia con diverse divisioni.'),
    ('Dove sfocia?', 'Po',
     'Il Po sfocia nel mare Adriatico fra due regioni.', 'Il Ticino sfocia nel Po a Ponte della Becca.'),
    ('Che cosa assorbe durante la fotosintesi?', None,
     'Durante la fotosintesi le piante assorbono anidride carbonica.', 'Le piante assorbono acqua dalle radici.'),
    ('Che romanzo ha scritto?', 'Mary Shelley',
     'Mary Shelley scrisse il romanzo Frankenstein nel 1818.', 'Mary Shelley non scrisse il romanzo Dracula.'),
    ('Che romanzo ha scritto?', 'Mary Shelley',
     'Mary Shelley scrisse il romanzo Frankenstein nel 1818.',
     'L’amica di Mary Shelley, Jane Williams, pubblicò un romanzo in seguito.'),
    ('Quando ha vinto il premio Nobel?', 'Marie Curie',
     'Marie Curie vinse il premio Nobel per la chimica nel 1911.',
     'Marie Curie ha ottenuto il premio Nobel per la chimica. Dal 1995 le sue spoglie sono al Pantheon.'),
    ('Dove si trova quel lago?', 'Lago di Garda',
     'Il lago di Garda si trova in Italia settentrionale.', 'Il lago di Como si trova in Italia settentrionale.'),
])
def test_extract_must_match_subject_relation_and_requested_detail(question, title, relevant, decoy):
    request = contextual_reference_request(question, [sourced_turn(title)] if title else [])
    assert request is not None and request.anchor_title == title
    assert request.matches_passage(relevant)
    assert not request.matches_passage(decoy)


@pytest.mark.parametrize('question', [
    'Dove sfocia questo progetto?',
    'Dove si trova il mio telefono?',
    'Dove si trova Pinco Pallino? Il suo telefono è privato.',
    'Quando è nato mio figlio?',
    'Quando ha vinto il premio ｓｅｇｒｅｔｏ?',
    'Quando ha vinto il premio No\u200bbel?',
    'Che romanzo ha scritto? Cerca anche l’email autore@esempio.it.',
    'Contro chi ha fatto scoppiare la seconda guerra mondiale? E il mio account?',
])
def test_unrelated_or_personal_request_does_not_borrow_a_public_title(question):
    assert contextual_reference_request(question, [sourced_turn('Po')]) is None


def test_dependent_question_requires_latest_attributed_answer():
    assert contextual_reference_request('Dove sfocia?', [sourced_turn('Po', source='model_generated')]) is None
    assert contextual_reference_request('Dove sfocia?', [sourced_turn('Po', url='https://evil.test/wiki/Po')]) is None
    assert contextual_reference_request('Dove sfocia?', [
        sourced_turn('Po'), SimpleNamespace(role='user', content='Qualcosa di diverso'),
    ]) is None


def test_same_focused_route_for_web_veto_and_explicit_search():
    question = 'Contro chi ha fatto scoppiare la seconda guerra mondiale?'
    expected = contextual_reference_request(question)
    assert contextual_reference_request(f'{question} Non cercare online.') == expected
    assert contextual_reference_request(f'Cerca online: {question}') == expected


def test_conflicting_targets_in_one_passage_cannot_supply_one_answer():
    request = contextual_reference_request('Contro chi ha fatto scoppiare la seconda guerra mondiale?')
    assert not request.matches_passage(
        'La Germania invase la Francia e attaccò la Polonia, provocando lo scoppio della seconda guerra mondiale.'
    )
    assert not request.matches_passage(
        'La Germania invase la Polonia, provocando lo scoppio della seconda guerra mondiale. '
        'La seconda guerra mondiale iniziò con l’invasione tedesca della Francia.'
    )


@pytest.mark.parametrize('text, minimum, maximum', [
    ('Aurelia (20 July 5 BC – 10 June AD 7) was a writer.', 10, 10),
    ('Aurelia (20 July 5 BC – 10 June 7 AD) was a writer.', 10, 10),
    ('Aurelia (20 July 5 BC – 21 July 7 AD) was a writer.', 11, 11),
    ('Aurelia (356–323 BC) was a writer.', 32, 33),
    ('Aurelia (1867–1934) was a writer.', 66, 67),
    ('Aurelia (20 o 21 luglio 40 a.C. – 20 luglio 10 a.C.) fu una scrittrice.', 29, 30),
    ('Aurelia of Rome (20/21 July 40 BC – 10/11 June 10 BC), commonly known as Aurelia, was a writer.', 29, 29),
    ('Aurelia de Roma (20/23 de julio o 6/10 de octubre de 40 a. C.\u200b - 10/13 de junio de 10 a. C.), '
     'conocida como Aurelia, fue una escritora.', 29, 29),
])
def test_lifespan_counts_completed_years_with_uncertain_historical_dates(text, minimum, maximum):
    from allma_model.utils.lifespan import lifespan_evidence

    evidence = lifespan_evidence('Aurelia', text)
    assert evidence is not None and (evidence.minimum, evidence.maximum) == (minimum, maximum)


@pytest.mark.parametrize('text', [
    'Aurelia (regno, 40–10 a.C.) fu una sovrana.',
    'La figlia di Aurelia (nascita, 1920–2000) fu una scrittrice.',
    'Aurelia (nascita, 356 a.C. – morte, 149 a.C.) fu una scrittrice.',
    'Aurelia (50 a.C. – 30) fu una scrittrice.',
])
def test_lifespan_rejects_a_reign_another_person_or_inconsistent_dates(text):
    from allma_model.utils.lifespan import lifespan_evidence

    assert lifespan_evidence('Aurelia', text) is None

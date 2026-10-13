import pytest
from allma_model.utils.exact_calculation import calculation_reply


@pytest.mark.parametrize('message,answer',[
    ('Quanto fa 18 + 24? Rispondi solo con un numero','42'),
    ('Calcola (7-2)*9','45'),('Quanto fa 0,1 + 0,2?','0.3'),
    ('Calcola 7/8','0.875'),('Calcola -3^2','-9'),('Calcola (−3)^2','9'),
    ('Calcola 0','0'),('Calcola 1/10000','0.0001'),
])
def test_general_exact_arithmetic(message,answer):
    result=calculation_reply(message)
    assert result[0]==answer and result[1]=='verified_calculation'


@pytest.mark.parametrize('message',[
    'Quanto fa 1/3?','Calcola 2^99999999','Calcola __import__("os")',
    'Quanto fa 2+2? Spiegalo in due frasi.',
    'Nel racconto qualcuno dice: Quanto fa 18+24?',
    'Calcola il mio budget per il viaggio',
])
def test_no_unsafe_evaluation_or_guessing_the_request(message):
    assert calculation_reply(message) is None


def test_zero_division_is_not_a_number():
    assert calculation_reply('Calcola 1/0')[1]=='calculation_error'

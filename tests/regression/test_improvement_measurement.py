import pytest
from tools.measure_improvements import score


def test_multilabel_score_does_not_count_partial_match_as_correct():
    rows = [
        {'expected_families':['joy','fear'], 'before':['joy'], 'after':['joy','fear']},
        {'expected_families':[], 'before':['sadness'], 'after':[]},
        {'expected_families':['sadness'], 'before':['sadness'], 'after':['joy']},
    ]
    before, after = score(rows, 'before'), score(rows, 'after')
    assert before['exact'] == 1 and after['exact'] == 2
    assert before['mixed_exact'] == 0 and after['mixed_exact'] == 1
    assert before['false_positive_neutral'] == 1 and after['false_positive_neutral'] == 0
    # These outputs have equal token-label F1 despite different exact-match rates.
    assert before['micro_f1'] == pytest.approx(2/3)
    assert after['micro_f1'] == pytest.approx(2/3)

from decimal import Decimal
import pytest
from app.errors import DataError
from app.modules.domain.rule import evaluate, format_spans


def test_overlap(cases):
    actual, evidence, available = evaluate(cases['overlap'])
    assert actual == Decimal('76')
    assert evidence and all(len(row) == 3 for row in evidence)
    assert format_spans(available) == '1:51;66:90'
    assert sum(b - a for a, b in available) == 76


def test_one_frame(cases):
    actual, _, available = evaluate(cases['one_frame'])
    assert actual == Decimal('1') and format_spans(available) == '5:5'


def test_clip(cases):
    actual, _, _ = evaluate(cases['clip'])
    assert actual == Decimal('5')


def test_reject_gap(cases):
    actual, evidence, available = evaluate(cases['reject_gap'])
    assert actual == Decimal('11')
    assert format_spans(available) == '1:5;15:20'


def test_empty(cases):
    actual, _, available = evaluate(cases['empty'])
    assert actual == Decimal('0') and available == []


def test_bad_target(cases):
    with pytest.raises(DataError) as error:
        evaluate(cases['bad_target'])
    assert error.value.code in {'BUSINESS', 'NUMBER', 'RANGE', 'TIMESTAMP'}


def test_bad_frame(cases):
    with pytest.raises(DataError) as error:
        evaluate(cases['bad_frame'])
    assert error.value.code in {'BUSINESS', 'NUMBER', 'RANGE', 'TIMESTAMP'}

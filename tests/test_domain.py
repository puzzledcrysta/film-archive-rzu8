from decimal import Decimal
import pytest
from app.errors import DataError
from app.modules.domain.rule import evaluate


def test_overlap(cases):
    actual, evidence = evaluate(cases['overlap'])
    assert actual == Decimal('76')
    assert evidence and all(len(row)==3 for row in evidence)


def test_one_frame(cases):
    actual, evidence = evaluate(cases['one_frame'])
    assert actual == Decimal('1')


def test_clip(cases):
    actual, evidence = evaluate(cases['clip'])
    assert actual == Decimal('5')


def test_reject_gap(cases):
    actual, evidence = evaluate(cases['reject_gap'])
    assert actual == Decimal('11')


def test_empty(cases):
    actual, evidence = evaluate(cases['empty'])
    assert actual == Decimal('0')


def test_bad_target(cases):
    with pytest.raises(DataError) as error:
        evaluate(cases['bad_target'])
    assert error.value.code in {'BUSINESS','NUMBER','RANGE','TIMESTAMP'}


def test_bad_frame(cases):
    with pytest.raises(DataError) as error:
        evaluate(cases['bad_frame'])
    assert error.value.code in {'BUSINESS','NUMBER','RANGE','TIMESTAMP'}


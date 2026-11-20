from app.errors import DataError
from app.evidence import finding
from app.settings import UNIT
from .rule import evaluate, format_spans, crop, subtract
from .values import whole


def _available(fields):
    """按已折叠字段复算某一补正时点的可用帧段，供复核轨迹展示。"""
    low = whole(fields['起片帧'], 0, 1000000000)
    high = whole(fields['止片帧'], 0, 1000000000)
    return subtract(crop(fields['扫描帧段'], low, high + 1),
                    crop(fields['判废帧段'], low, high + 1))


def calculate(records):
    accepted, rejected = [], []
    for record in records:
        try:
            amount, proof, available = evaluate(record['fields'])
            trail = []
            for step in record.get('revisions', []):
                try:
                    step_available = _available(step['fields'])
                    step_view = format_spans(step_available)
                except DataError:
                    step_view = ''
                trail.append({**step, 'available_text': step_view})
        except DataError as error:
            rejected.append(finding(record, error.code, str(error)))
            continue
        accepted.append({'key': record['key'], 'line': record['line'], 'revision': record['revision'],
                         'amount': format(amount, 'f'), 'unit': UNIT, 'raw': record['raw'],
                         'fields': record['fields'],
                         'available': [{'start': a, 'end': b - 1} for a, b in available],
                         'available_text': format_spans(available),
                         'revisions': trail,
                         'proof': [{'metric': label, 'value': str(value), 'unit': unit} for label, value, unit in proof]})
    return accepted, rejected

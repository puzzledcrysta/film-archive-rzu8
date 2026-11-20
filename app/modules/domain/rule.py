from decimal import Decimal
from app.errors import DataError
from .values import whole, spans, union


def crop(raw, low, high):
    return union((max(low, a), min(high, b + 1)) for a, b in spans(raw, closed=True)
                 if max(low, a) < min(high, b + 1))


def subtract(ranges, removed):
    """半开区间差集：ranges 与 removed 均已归并，返回归并后的剩余区间。"""
    result = []
    for start, end in ranges:
        cursor = start
        for cut_start, cut_end in removed:
            if cut_end <= cursor or cut_start >= end:
                continue
            if cut_start > cursor:
                result.append((cursor, cut_start))
            cursor = max(cursor, cut_end)
        if cursor < end:
            result.append((cursor, end))
    return union(result)


def format_spans(ranges):
    """半开区间转回业务上的含尾帧段文本。"""
    return ';'.join(f'{a}:{b - 1}' for a, b in ranges)


def evaluate(row):
    low, high = (whole(row[key], 0, 1000000000) for key in ('起片帧', '止片帧'))
    if high < low:
        raise DataError('BUSINESS', '目标帧范围倒置')
    scanned = crop(row['扫描帧段'], low, high + 1)
    bad = crop(row['判废帧段'], low, high + 1)
    available = subtract(scanned, bad)
    unique = sum(b - a for a, b in scanned)
    rejected = sum(max(0, min(b, d) - max(a, c)) for a, b in scanned for c, d in bad)
    amount = sum(b - a for a, b in available)
    proof = [('唯一已扫', unique, '帧'), ('已扫且判废', rejected, '帧'),
             ('未扫描', high - low + 1 - unique, '帧'),
             ('最终已扫帧段', format_spans(scanned), ''),
             ('判废帧段(并集)', format_spans(bad), ''),
             ('最终可用帧段', format_spans(available), '')]
    return Decimal(amount), proof, available

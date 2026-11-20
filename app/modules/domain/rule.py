from decimal import Decimal
from app.errors import DataError
from .values import whole, spans, union


def crop(raw, low, high):
    return union((max(low,a), min(high,b+1)) for a,b in spans(raw, closed=True)
                 if max(low,a) < min(high,b+1))


def evaluate(row):
    low, high = (whole(row[key],0,1000000000) for key in ('起片帧','止片帧'))
    if high < low:
        raise DataError('BUSINESS', '目标帧范围倒置')
    scanned = crop(row['扫描帧段'],low,high+1)
    bad = crop(row['判废帧段'],low,high+1)
    unique = sum(b-a for a,b in scanned)
    rejected = sum(max(0,min(b,d)-max(a,c)) for a,b in scanned for c,d in bad)
    return Decimal(unique-rejected), [('唯一已扫',unique,'帧'), ('已扫且判废',rejected,'帧'), ('未扫描', high-low+1-unique,'帧')]

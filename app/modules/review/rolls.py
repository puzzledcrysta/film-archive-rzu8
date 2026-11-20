import csv
from io import StringIO

# 对账代码到中文结论的映射，与前端原因表保持一致
DIFF_LABELS = {
    'MATCH': '一致',
    'MISSING_BOOK': '外部账漏记',
    'MISSING_RESULT': '复算单边',
    'AMOUNT_DELTA': '数值不符',
}

CSV_HEADER = ('扫描段', '修订号', '来源行号', '最终可用帧段', '正式结果(帧)',
              '外部记录值(帧)', '差值(帧)', '差异结论', '外部账行号')


def build_rolls(run):
    """同一卷的正式复算结果与外部账差异做全外连接，逐条并账。"""
    results = {row['key']: row for row in run['accepted']}
    book = {row['key']: row for row in run['book']['rows']}
    rolls = []
    for key in sorted(results.keys() | book.keys()):
        result = results.get(key)
        diff = book.get(key)
        rolls.append({
            'key': key,
            'revision': result['revision'] if result else None,
            'line': result['line'] if result else None,
            'available_text': result['available_text'] if result else None,
            'amount': result['amount'] if result else None,
            'reference': diff['reference'] if diff else None,
            'delta': diff['delta'] if diff else None,
            'code': diff['code'] if diff else 'MISSING_RESULT',
            'book_line': diff['book_line'] if diff else None,
        })
    return rolls


def rolls_csv(run):
    buffer = StringIO(newline='')
    writer = csv.writer(buffer)
    writer.writerow(CSV_HEADER)
    for roll in build_rolls(run):
        writer.writerow([
            roll['key'],
            roll['revision'] if roll['revision'] is not None else '',
            roll['line'] if roll['line'] is not None else '',
            roll['available_text'] or '无',
            roll['amount'] if roll['amount'] is not None else '',
            roll['reference'] if roll['reference'] is not None else '',
            roll['delta'] if roll['delta'] is not None else '',
            DIFF_LABELS.get(roll['code'], roll['code']),
            roll['book_line'] if roll['book_line'] is not None else '',
        ])
    # UTF-8 BOM，方便 Excel 直接识别中文表头
    return '﻿' + buffer.getvalue()

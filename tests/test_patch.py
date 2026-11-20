import csv
from io import StringIO
from app.pipeline import execute
from app.settings import KEY, UNIT

HEADER = '扫描段,修订号,提交时间,起片帧,止片帧,扫描帧段,判废帧段,原始备注\n'
BOOK_HEADER = f'{KEY},外部记录值({UNIT})\n'


def source_of(*rows):
    return (HEADER + ''.join(rows)).encode()


def row(key, revision, scanned, rejected, start='1', end='100', note='备注'):
    return f'{key},{revision},2026-11-18T01:{revision:02d}:00+00:00,{start},{end},{scanned},{rejected},{note}\n'


def book_of(*pairs):
    out = StringIO(newline='')
    writer = csv.writer(out)
    writer.writerow([KEY, f'外部记录值({UNIT})'])
    for pair in pairs:
        writer.writerow(pair)
    return out.getvalue().encode()


def test_blank_patch_does_not_shrink_scanned_range():
    # 第二版只改判废、扫描留空：可用范围必须保留第一版的全部扫描（1:100）
    payload = source_of(row('00301', 1, '1:100', '90:95'),
                        row('00301', 2, '', '无', start='', end=''))
    result = execute(payload, book_of(('00301', '100')))
    accepted, = result['accepted']
    assert accepted['available_text'] == '1:100'
    assert accepted['amount'] == '100'
    # 若误把空白当清空，只会得到 0 帧并产生缺帧
    assert accepted['revisions'][-1]['available_text'] == '1:100'


def test_explicit_none_clears_rejection_and_recovers_frames():
    # “无”清空判废后，原先扣除的帧恢复可用
    payload = source_of(row('00302', 1, '1:10', '6:10'),
                        row('00302', 2, '', '无', start='', end=''))
    accepted, = execute(payload, book_of())['accepted']
    assert accepted['available_text'] == '1:10' and accepted['amount'] == '10'
    first, second = accepted['revisions']
    assert first['available_text'] == '1:5' and second['available_text'] == '1:10'


def test_trail_records_each_correction_state():
    payload = source_of(row('00303', 1, '1:100', '50:60'),
                        row('00303', 2, '1:80', '', start='', end=''),
                        row('00303', 3, '', '无', start='', end=''))
    accepted, = execute(payload, book_of())['accepted']
    assert [step['revision'] for step in accepted['revisions']] == [1, 2, 3]
    assert [step['changed'] for step in accepted['revisions']] == \
           [['起片帧', '止片帧', '扫描帧段', '判废帧段'], ['扫描帧段'], ['判废帧段']]
    assert accepted['available_text'] == '1:80'
    assert accepted['available'] == [{'start': 1, 'end': 80}]


def test_patch_result_joins_external_ledger_diff(client):
    payload = source_of(row('00304', 1, '1:10', '无'),
                        row('00304', 2, '', '6:10', start='', end=''))
    run = client.post('/api/runs', json={'data': payload.decode(),
                                         'book': BOOK_HEADER + '00304,9\n09998,3\n'}).json()
    # 正式结果 5 帧，外部账记 9 帧，差异 -4；外部单边 09998 一并并账
    roll, external_only = run['book']['rows']
    assert (roll['key'], roll['amount'], roll['reference'], roll['delta'], roll['code']) == \
           ('00304', '5', '9', '-4', 'AMOUNT_DELTA')
    assert (external_only['key'], external_only['code']) == ('09998', 'MISSING_RESULT')
    accepted, = run['accepted']
    assert accepted['available_text'] == '1:5'


def test_export_bundle_and_rolls_csv_share_one_roll_view(client):
    payload = source_of(row('00305', 1, '1:10', '无'))
    run_id = client.post('/api/runs', json={'data': payload.decode(),
                                            'book': BOOK_HEADER + '00305,10\n'}).json()['manifest']['run_id']
    bundle = client.get(f'/api/export/{run_id}').json()
    assert bundle['rolls'][0]['key'] == '00305'
    assert bundle['rolls'][0]['available_text'] == '1:10'
    assert bundle['rolls'][0]['diff_label'] == '一致'
    response = client.get(f'/api/export/{run_id}/rolls.csv')
    assert response.status_code == 200 and 'text/csv' in response.headers['content-type']
    text = response.content.decode('utf-8-sig')
    rows = list(csv.reader(StringIO(text)))
    assert rows[0][:4] == ['扫描段', '修订号', '来源行号', '最终可用帧段']
    assert rows[1][0] == '00305' and rows[1][3] == '1:10' and rows[1][7] == '一致'


def test_replay_of_same_patch_is_stable(client):
    payload = source_of(row('00306', 1, '1:10', '无'),
                        row('00306', 2, '1:8', '', start='', end=''))
    first = client.post('/api/runs', json={'data': payload.decode(), 'book': BOOK_HEADER}).json()
    run_id = first['manifest']['run_id']
    second = client.post(f'/api/runs/{run_id}/replay', json={}).json()
    assert first == second
    assert client.get(f'/api/runs/{run_id}').json() == first


def test_single_revision_still_carries_trail_and_spans(client):
    payload = source_of(row('00307', 1, '1:5;8:10', '无'))
    run = client.post('/api/runs', json={'data': payload.decode(), 'book': BOOK_HEADER}).json()
    accepted, = run['accepted']
    assert accepted['available_text'] == '1:5;8:10'
    assert accepted['available'] == [{'start': 1, 'end': 5}, {'start': 8, 'end': 10}]
    step, = accepted['revisions']
    assert step['revision'] == 1 and step['available_text'] == '1:5;8:10'


def test_rolls_export_covers_external_side_only(client):
    # 外部账单边键也要出现在并账导出里，正式结果侧字段留空
    run_id = client.post('/api/runs', json={'book': f'{BOOK_HEADER}09997,4\n'}).json()['manifest']['run_id']
    bundle = client.get(f'/api/export/{run_id}').json()
    external = next(item for item in bundle['rolls'] if item['key'] == '09997')
    assert external['code'] == 'MISSING_RESULT' and external['amount'] is None
    assert external['reference'] == '4' and external['diff_label'] == '复算单边'
    csv_text = client.get(f'/api/export/{run_id}/rolls.csv').content.decode('utf-8-sig')
    assert '09997,,,无,,4,-4,复算单边,2' in csv_text

from app.modules.contract.service import normalize
from app.modules.intake.service import intake
from app.modules.quality.service import inspect


def report(source):
    return inspect(*normalize(intake(source)))


HEADER = '扫描段,修订号,提交时间,起片帧,止片帧,扫描帧段,判废帧段,原始备注\n'


def csv_of(*rows):
    return (HEADER + ''.join(rows)).encode()


def row(key, revision, scanned, rejected, start='1', end='100'):
    fields = f'{start},{end},{scanned},{rejected}'
    return f'{key},{revision},2026-11-18T01:{revision:02d}:00+00:00,{fields},备注\n'


def test_conflicting(source):
    # TRAP-14
    result = report(source)
    assert '00899' not in {row['key'] for row in result['ready']}
    assert [row['code'] for row in result['rejected'] if row['key'] == '00899'] == ['REV_CONFLICT', 'REV_CONFLICT']


def test_redundant_transmission(source):
    taken = report(source)['suppressed']
    assert [(row['key'], row['code']) for row in taken if row['code'] == 'EXACT_DUP'] == [('00101', 'EXACT_DUP')]


def test_prefers_high_revision(source):
    row, = [row for row in report(source)['ready'] if row['key'] == '00102']
    assert row['revision'] == 2


def test_older_is_explained(source):
    assert [row['key'] for row in report(source)['suppressed'] if row['code'] == 'SUPERSEDED'] == ['00102']


def test_reason_counts(source):
    codes = report(source)['reasons']
    assert codes == {'REQUIRED': 1, 'REV_CONFLICT': 2, 'WIDTH': 1}


def test_earliest_evidence_retained_for_duplicates(source):
    chosen = next(row for row in report(source)['ready'] if row['key'] == '00101')
    assert chosen['line'] == 2


def test_blank_patch_carries_forward_other_fields():
    # 修订 2 只改判废，扫描帧段与目标范围留空：必须沿用修订 1，而不是当成清空
    payload = csv_of(row('00201', 1, '1:55;50:90', '52:60'),
                     row('00201', 2, '', '52:55', start='', end=''))
    ready, = report(payload)['ready']
    assert ready['fields']['扫描帧段'] == '1:55;50:90'
    assert ready['fields']['判废帧段'] == '52:55'
    assert [step['changed'] for step in ready['revisions']] == \
           [['起片帧', '止片帧', '扫描帧段', '判废帧段'], ['判废帧段']]


def test_explicit_none_clears_rejected_spans():
    # “无”是明确清空，与留空语义不同
    payload = csv_of(row('00202', 1, '1:50', '10:20'),
                     row('00202', 2, '', '无'))
    ready, = report(payload)['ready']
    assert ready['fields']['判废帧段'] == '无'
    assert ready['fields']['扫描帧段'] == '1:50'


def test_blank_and_none_differ_for_scan_field():
    cleared = csv_of(row('00203', 1, '1:50', '无'), row('00203', 2, '无', '无'))
    carried = csv_of(row('00204', 1, '1:50', '无'), row('00204', 2, '', '无'))
    assert report(cleared)['ready'][0]['fields']['扫描帧段'] == '无'
    assert report(carried)['ready'][0]['fields']['扫描帧段'] == '1:50'


def test_incomplete_base_revision_is_quarantined():
    # 扫描帧段始终未补齐，不能静默沿用空值
    payload = csv_of(row('00205', 1, '', '无'), row('00205', 2, '', '1:5'))
    result = report(payload)
    assert not result['ready']
    assert [item['code'] for item in result['rejected']] == ['PATCH_INCOMPLETE']


def test_later_revision_completes_blank_base():
    # 首版缺扫描、次版补齐：折叠后字段闭合，正常采信
    payload = csv_of(row('00206', 1, '', '无'), row('00206', 2, '1:50', '无'))
    ready, = report(payload)['ready']
    assert ready['fields']['扫描帧段'] == '1:50'


def test_duplicate_patch_is_idempotent():
    # 同一补发重跑（重复传输）折叠结果不变
    payload = csv_of(row('00207', 1, '1:50', '无'),
                     row('00207', 2, '1:60', '无'),
                     row('00207', 2, '1:60', '无'))
    result = report(payload)
    ready, = result['ready']
    assert ready['fields']['扫描帧段'] == '1:60'
    suppressed = [(item['key'], item['code']) for item in result['suppressed']]
    assert ('00207', 'EXACT_DUP') in suppressed and ('00207', 'SUPERSEDED') in suppressed
    assert [step['revision'] for step in ready['revisions']] == [1, 2]

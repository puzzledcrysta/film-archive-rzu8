from collections import defaultdict
from app.settings import FIELDS
from app.evidence import finding


def _finding(row, code, detail):
    return finding(row, code, detail)


def _fold(chain):
    """按修订号升序折叠同一卷的补发。

    业务字段留空表示本次补发未改该字段，沿用上一版；“无”表示明确清空为空集合。
    返回每次补正后的累积状态与实际变更字段；最终状态不完整则返回 None。
    中间修订允许暂时缺项，由更高修订补齐。
    """
    merged = {field: '' for field in FIELDS}
    trail = []
    for revision, row in chain:
        changed = []
        for field in FIELDS:
            value = row['fields'][field]
            if value == '':
                continue
            merged[field] = value
            changed.append(field)
        trail.append({'revision': revision, 'line': row['line'], 'time': row['time'],
                      'changed': changed, 'fields': dict(merged), 'note': row['note']})
    if any(merged[field] == '' for field in FIELDS):
        return None
    return trail


def split_versions(records):
    groups = defaultdict(list)
    for record in records:
        groups[record['key']].append(record)
    ready, duplicates, conflicts = [], [], []
    for key, group in sorted(groups.items()):
        latest = max(row['revision'] for row in group)
        candidates = sorted((row for row in group if row['revision'] == latest), key=lambda row: row['line'])
        older = [row for row in group if row['revision'] != latest]
        duplicates.extend(_finding(row, 'SUPERSEDED', f'修订 {latest} 取代旧版本') for row in older)
        signatures = {tuple(row['fields'].items()) for row in candidates}
        if len(signatures) > 1:
            conflicts.extend(_finding(row, 'REV_CONFLICT', f'最高修订 {latest} 的来源字段互相冲突') for row in candidates)
            continue
        duplicates.extend(_finding(row, 'EXACT_DUP', f'同为修订 {latest}，保留第 {candidates[0]["line"]} 行')
                          for row in candidates[1:])
        # 每个修订只取首行参与折叠：同修订精确重复已按 EXACT_DUP 留证，重跑不重复改变结果
        chain = []
        seen = set()
        for row in sorted(group, key=lambda item: (item['revision'], item['line'])):
            if row['revision'] in seen:
                continue
            seen.add(row['revision'])
            chain.append((row['revision'], row))
        trail = _fold(chain)
        if trail is None:
            conflicts.append(_finding(candidates[0], 'PATCH_INCOMPLETE',
                                      '补发字段无法闭合：最高修订后仍有业务字段空白，空白只能沿用已有值，无法凭空补齐'))
            continue
        chosen = dict(candidates[0])
        chosen['fields'] = trail[-1]['fields']
        chosen['revisions'] = trail
        ready.append(chosen)
    return ready, duplicates, conflicts

import json
from app.modules.runs.service import get
from .decisions import timeline
from .rolls import build_rolls, DIFF_LABELS


def bundle(run_id):
    history = timeline(run_id)
    run = get(run_id)
    # 导出包同时带来源证据、适用复核版本，以及同卷正式结果与外部账的并账差异。
    rolls = build_rolls(run)
    return json.dumps({'manifest': run['manifest'], 'counts': run['counts'], 'results': run['accepted'],
                       'rolls': [{**roll, 'diff_label': DIFF_LABELS.get(roll['code'], roll['code'])} for roll in rolls],
                       'quarantine': run['quarantine'], 'suppressed': run['suppressed'],
                       'reconciliation': run['book'], 'review': history},
                      ensure_ascii=False, indent=2)

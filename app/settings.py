import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_ROOT = ROOT / 'sample_data'
DB = Path(os.getenv('WORKBENCH_DB', str(ROOT/'state/ledger.sqlite3')))
TITLE = '胶片修复拼接'
SLUG = 'film-archive'
KEY = '扫描段'
FIELDS = ('起片帧', '止片帧', '扫描帧段', '判废帧段')
ROLE = '电影资料馆修复员'
UNIT = '帧'
SIGNATURE = '帧格'
RULE_VERSION = 'film-archive-1.0'
TABS = {'intake': '来源采信', 'contract': '字段解释', 'quality': '隔离裁决', 'domain': '帧段拼接', 'reconcile': '独立对账', 'runs': '批次复算', 'review': '交付复核'}

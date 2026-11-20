# 胶片修复拼接深度登记

- 规模：中型
- 核心规则：先合并目标帧号区间，再减并集内已判废的帧段，帧号采用含尾区间。
- 使用者与工作流：电影资料馆修复员按扫描段复算来源批次，对照外部记录后提交复核。

## 功能模块

| 模块 | 使用者动作 | 入口 | 核心文件 | 测试 |
|---|---|---|---|---|
| M1 来源采信 | 接收分段记录、定位坏行 | `POST /api/intake` | `app/modules/intake/service.py` | `tests/test_intake.py` |
| M2 字段解释 | 归一主键、版本、时间和原字段 | `POST /api/contract` | `app/modules/contract/service.py` | `tests/test_contract.py` |
| M3 隔离裁决 | 归并重复、隔离争议版本 | `POST /api/quality` | `app/modules/quality/versions.py` | `tests/test_quality.py` |
| M4 帧段拼接 | 复算业务明细与边界证据 | `POST /api/domain` | `app/modules/domain/rule.py` | `tests/test_domain.py` |
| M5 独立对账 | 核对外部记录并分别计量 | `POST /api/reconcile` | `app/modules/reconcile/service.py` | `tests/test_reconcile.py` |
| M6 批次复算 | 保存运行、查询历史、复算原输入 | `POST /api/runs` | `app/modules/runs/service.py` | `tests/test_runs.py` |
| M7 交付复核 | 复核差异、阻止陈旧提交、导出证据与并账 | `GET /api/export`、`GET /api/export/{id}/rolls.csv` | `app/modules/review/decisions.py`、`app/modules/review/rolls.py` | `tests/test_review.py`、`tests/test_patch.py` |

## 陷阱登记

| TRAP | 现象 | 样例 | 处理位置 | 测试 |
|---|---|---|---|---|
| TRAP-02 | BOM | shift.csv | `app/modules/intake/service.py` | `tests/test_intake.py::test_bom` |
| TRAP-03 | 引号内换行 | shift.csv | `app/modules/intake/service.py` | `tests/test_intake.py::test_multiline` |
| TRAP-04 | 重复表头 | shift.csv | `app/modules/intake/service.py` | `tests/test_intake.py::test_repeated` |
| TRAP-05 | 列数不齐 | shift.csv | `app/modules/intake/service.py` | `tests/test_intake.py::test_width` |
| TRAP-07 | 空值哨兵 | shift.csv | `app/modules/contract/service.py` | `tests/test_contract.py::test_missing` |
| TRAP-08 | 主键前导零 | shift.csv | `app/modules/contract/service.py` | `tests/test_contract.py::test_leading_zero` |
| TRAP-11 | 偏移时间归一 | shift.csv | `app/modules/contract/service.py` | `tests/test_contract.py::test_offsets` |
| TRAP-14 | 等版本冲突 | shift.csv | `app/modules/quality/versions.py` | `tests/test_quality.py::test_conflicting` |
| TRAP-18 | 三种空态 | 测试构造输入 | `app/modules/intake/service.py` | `tests/test_intake.py::test_empty_states` |
| TRAP-26 | 陈旧复核 | 测试构造输入 | `app/modules/review/decisions.py` | `tests/test_review.py::test_stale` |
| TRAP-27 | 补发留空沿用与“无”清空 | 测试构造输入 | `app/modules/quality/versions.py` | `tests/test_quality.py::test_blank_patch_carries_forward_other_fields` |
| TRAP-28 | 补发字段不闭合 | 测试构造输入 | `app/modules/quality/versions.py` | `tests/test_quality.py::test_incomplete_base_revision_is_quarantined` |
| TRAP-29 | 最终可用帧段差集 | 测试构造输入 | `app/modules/domain/rule.py` | `tests/test_patch.py::test_blank_patch_does_not_shrink_scanned_range` |

## 对账规则

输入记录数 = 计入 + 隔离 + 去重和替换 + 空白记录 + 重复表头。
业务账按扫描段全外连接。差异分别标记漏记、外部单边和数值不符，以帧对差。
`GET /api/export/{id}/rolls.csv` 把同一卷的正式结果（最终可用帧段、复算值）与外部账差异逐卷并到一行；JSON 证据包的 `rolls` 字段是同一份数据。

## 可靠性

- 运行 ID 由规则版本和两份输入的 SHA-256 决定，`INSERT OR IGNORE` 落库：同一补发重跑返回同一结果，不重复改变。
- 运行先算后写，异常时不触碰已存批次；工作台切换或重算失败保留上一版结果，历史批次仍可打开。

## 范围

本地文件与单机复核。单次来源文本限 128 KiB。复合字段单项最多 240 段。

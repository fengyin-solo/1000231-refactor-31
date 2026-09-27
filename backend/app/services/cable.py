"""电缆线路业务规则：状态流转、字段校验与筛选口径都收在这里。

测值缺失、连续下降、待测三类判定只在 ``assess_entry`` 一处完成，
列表、明细、异常入口、逐条检查与整段查看都消费同一份结果对象。
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from app.store import store

MODULE = "cable"
REQUIRED_FIELDS = ["电缆编号", "电缆型号", "起止位置"]
STATUS_ORDER = ["正常运行", "绝缘降低", "待修复", "已修复"]
ACTION_RULES = {"测试绝缘": "正常运行", "标记隐患": "待修复", "安排修复": "已修复"}
NEGATIVE_ACTIONS = []

# 连续下降至少需要几期测值（含本期），少了无法判定趋势。
DECLINE_MIN_POINTS = 3
# 距上次测试超过该天数即视为待测。
PENDING_TEST_DAYS = 30
# 结果对象中固定带上的展示/查询字段，前端各入口只读这一份。
DISPLAY_FIELDS = ["电缆编号", "电缆型号", "起止位置", "敷设方式", "绝缘电阻", "测试日期"]


def _to_number(value: Any) -> float | None:
    """把绝缘电阻测值解析成数字；空串、None、非数字一律视为缺失。"""
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _parse_date(value: Any) -> date | None:
    """解析测试日期；空值或非法日期返回 None。"""
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def assess_entry(entry: dict[str, Any], *, today: date | None = None) -> dict[str, Any]:
    """对一条电缆段生成共用结果对象。

    这是测值缺失、连续下降、待测三类状态的唯一判定处：
    - missing：绝缘电阻（本期测值）缺失；
    - declining：最近连续 ``DECLINE_MIN_POINTS`` 期测值逐期下降；
    - pending_test：没有测试日期，或距上次测试超过 ``PENDING_TEST_DAYS`` 天。
    结论按 缺测 → 连续下降 → 待测 的优先级取一条，其余为正常。
    """
    history = entry.get("测值历史") or []
    readings: list[dict[str, Any]] = sorted(
        history,
        key=lambda item: str(item.get("date") or ""),
    )

    current = _to_number(entry.get("绝缘电阻"))
    missing = current is None

    declining = False
    if len(readings) >= DECLINE_MIN_POINTS:
        recent = [_to_number(item.get("value")) for item in readings[-DECLINE_MIN_POINTS:]]
        declining = all(
            value is not None and (index == 0 or value < recent[index - 1])  # type: ignore[index]
            for index, value in enumerate(recent)
        )

    last_test = _parse_date(entry.get("测试日期"))
    reference = today or date.today()
    pending_test = last_test is None or reference - last_test > timedelta(days=PENDING_TEST_DAYS)

    if missing:
        conclusion = "测值缺失"
    elif declining:
        conclusion = "连续下降"
    elif pending_test:
        conclusion = "待测"
    else:
        conclusion = "正常"

    result: dict[str, Any] = {
        "id": entry.get("id"),
        "status": entry.get("status"),
        "missing": missing,
        "declining": declining,
        "pendingTest": pending_test,
        "abnormal": missing or declining,
        "conclusion": conclusion,
        "history": readings,
        "latestValue": current,
    }
    for field in DISPLAY_FIELDS:
        result[field] = entry.get(field)
    return result


class CableService:
    def list_entries(
        self,
        *,
        keyword: str | None = None,
        status: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[dict[str, Any]], int]:
        rows = store.rows(MODULE)
        if keyword:
            rows = [row for row in rows if keyword in str(row.get("电缆编号", ""))]
        if status:
            rows = [row for row in rows if row.get("status") == status]
        total = len(rows)
        start = max(page - 1, 0) * size
        page_rows = rows[start:start + size]
        return [assess_entry(row) for row in page_rows], total

    def get_entry(self, entry_id: int) -> dict[str, Any] | None:
        entry = store.find(MODULE, entry_id)
        return assess_entry(entry) if entry is not None else None

    def list_abnormal(self) -> list[dict[str, Any]]:
        """异常入口：只取评估结论为异常（缺测或连续下降）的电缆段。"""
        return [
            result
            for row in store.rows(MODULE)
            if (result := assess_entry(row))["abnormal"]
        ]

    def segment_summary(self) -> dict[str, Any]:
        """整段查看：对全部电缆段跑同一套评估，汇总结论与计数。"""
        results = [assess_entry(row) for row in store.rows(MODULE)]
        counts = {
            "正常": 0,
            "测值缺失": 0,
            "连续下降": 0,
            "待测": 0,
        }
        for result in results:
            counts[result["conclusion"]] += 1
        return {
            "module": MODULE,
            "total": len(results),
            "abnormal": sum(1 for result in results if result["abnormal"]),
            "counts": counts,
            "items": results,
        }

    def create_entry(self, values: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
        missing = [field for field in REQUIRED_FIELDS if not str(values.get(field) or "").strip()]
        if missing:
            return None, missing
        rows = store.rows(MODULE)
        entry = {"id": max((int(row.get("id", 0)) for row in rows), default=0) + 1}
        entry.update({field: values.get(field) for field in REQUIRED_FIELDS})
        entry["status"] = STATUS_ORDER[0]
        entry["pending"] = True
        entry["abnormal"] = False
        rows.append(entry)
        return assess_entry(entry), []

    def run_action(self, entry_id: int, action: str) -> tuple[dict[str, Any] | None, str]:
        entry = store.find(MODULE, entry_id)
        if entry is None:
            return None, f"电缆段 {entry_id} 不存在或已归档"
        if action not in ACTION_RULES:
            return None, f"动作「{action}」不属于电缆线路可执行范围"
        target = ACTION_RULES[action]
        if target not in STATUS_ORDER:
            return None, f"目标状态「{target}」不在允许的状态序列里"
        entry["status"] = target
        entry["pending"] = target != STATUS_ORDER[-1]
        entry["abnormal"] = action in NEGATIVE_ACTIONS
        return assess_entry(entry), f"电缆段已{action}"

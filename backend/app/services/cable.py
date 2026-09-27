"""电缆线路业务规则：状态流转、字段校验与筛选口径都收在这里。"""
from __future__ import annotations

from typing import Any

from app.store import store

MODULE = "cable"
REQUIRED_FIELDS = ["电缆编号", "电缆型号", "起止位置"]
FILTER_FIELDS = ["电缆编号", "电缆型号", "起止位置", "绝缘电阻"]
STATUS_ORDER = ["正常运行", "绝缘降低", "待修复", "已修复"]
ACTION_RULES = {"测试绝缘": "正常运行", "标记隐患": "待修复", "安排修复": "已修复"}
NEGATIVE_ACTIONS = []


def _to_float(value: Any) -> float | None:
    """把测值转成可比较的数；空值与占位文本都视为无有效测值。"""
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return None


def evaluate_segment(row: dict[str, Any]) -> dict[str, Any]:
    """电缆段测值结论：测值缺失、连续下降、待测状态只在这里判定一次。

    列表、详情与异常入口都读取这一份结果对象，保证逐条检查与整段查看结论一致。
    """
    current = _to_float(row.get("绝缘电阻"))
    previous = _to_float(row.get("上次测值"))
    pending = current is None
    missing = not pending and previous is None
    declining = current is not None and previous is not None and current < previous
    abnormal = missing or declining
    if pending:
        conclusion = "待测"
    elif declining:
        conclusion = "连续下降"
    elif missing:
        conclusion = "测值缺失"
    else:
        conclusion = "正常"
    return {
        "待测": pending,
        "测值缺失": missing,
        "连续下降": declining,
        "异常": abnormal,
        "结论": conclusion,
    }


class CableService:
    def list_entries(
        self,
        *,
        keyword: str | None = None,
        status: str | None = None,
        filters: dict[str, str] | None = None,
        abnormal_only: bool = False,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[dict[str, Any]], int]:
        rows = store.rows(MODULE)
        if keyword:
            rows = [row for row in rows if keyword in str(row.get("电缆编号", ""))]
        if status:
            rows = [row for row in rows if row.get("status") == status]
        for field, value in (filters or {}).items():
            if field in FILTER_FIELDS and str(value).strip():
                rows = [row for row in rows if str(value).strip() in str(row.get(field, ""))]
        entries = [self._with_result(row) for row in rows]
        if abnormal_only:
            entries = [entry for entry in entries if entry["测值结论"]["异常"]]
        total = len(entries)
        start = max(page - 1, 0) * size
        return entries[start:start + size], total

    def get_entry(self, entry_id: int) -> dict[str, Any] | None:
        row = store.find(MODULE, entry_id)
        if row is None:
            return None
        return self._with_result(row)

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
        return self._with_result(entry), []

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
        return self._with_result(entry), f"电缆段已{action}"

    @staticmethod
    def _with_result(row: dict[str, Any]) -> dict[str, Any]:
        """在记录副本上挂共用测值结论，不污染仓库里的原始行。"""
        entry = dict(row)
        entry["测值结论"] = evaluate_segment(row)
        return entry

"""电缆线路接口：维护电缆段，覆盖测试绝缘、标记隐患、安排修复等动作。"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request

from app.schemas import ActionResult, EntryPayload, PageResult
from app.services.cable import FILTER_FIELDS, CableService

router = APIRouter(prefix="/api/cable", tags=["电缆线路"])

service = CableService()

LIST_FIELDS = ["电缆编号", "电缆型号", "起止位置", "敷设方式", "绝缘电阻", "上次测值", "测试日期", "电缆状态"]
STATUSES = ["正常运行", "绝缘降低", "待修复", "已修复"]


def _field_filters(request: Request) -> dict[str, str]:
    """从查询串里挑出支持的字段条件（起止位置、绝缘电阻等），其余忽略。"""
    return {
        field: request.query_params[field]
        for field in FILTER_FIELDS
        if request.query_params.get(field)
    }


@router.get("", response_model=PageResult[dict])
def list_entries(
    request: Request,
    keyword: str | None = Query(default=None, description="按电缆编号检索"),
    status: str | None = Query(default=None, description="正常运行、绝缘降低、待修复、已修复"),
    page: int = 1,
    size: int = 20,
) -> PageResult[dict]:
    """按电缆编号、状态与字段条件过滤电缆线路列表；每行都带共用测值结论。"""
    if size > 200:
        raise HTTPException(status_code=400, detail="每页最多 200 条，请缩小分页范围")
    items, total = service.list_entries(
        keyword=keyword, status=status, filters=_field_filters(request), page=page, size=size,
    )
    return PageResult(items=items, total=total, page=page, size=size)


@router.get("/abnormal", response_model=PageResult[dict])
def list_abnormal(request: Request, page: int = 1, size: int = 200) -> PageResult[dict]:
    """异常入口：只列出共用结论判定为异常（测值缺失或连续下降）的电缆段。"""
    items, total = service.list_entries(
        filters=_field_filters(request), abnormal_only=True, page=page, size=size,
    )
    return PageResult(items=items, total=total, page=page, size=size)


@router.get("/export")
def export_entries() -> dict[str, Any]:
    """导出电缆线路清单：返回当前过滤条件下的全量数据。"""
    items, total = service.list_entries(page=1, size=10000)
    return {"module": "cable", "total": total, "items": items}


@router.get("/{entry_id}", response_model=dict)
def get_entry(entry_id: int) -> dict:
    """读取单条电缆段明细；与列表、异常入口共用同一份测值结论。"""
    entry = service.get_entry(entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"电缆段 {entry_id} 不存在或已归档")
    return entry


@router.post("", response_model=ActionResult)
def create_entry(payload: EntryPayload) -> ActionResult:
    """登记一条电缆段，缺字段时说明原因而不是静默丢弃。"""
    entry, missing = service.create_entry(payload.values)
    if missing:
        return ActionResult(ok=False, message=f"缺少必填字段：{'、'.join(missing)}")
    return ActionResult(ok=True, message="电缆段已登记", entry=entry)


@router.post("/{entry_id}/actions", response_model=ActionResult)
def run_action(entry_id: int, payload: EntryPayload) -> ActionResult:
    """对单条电缆段执行测试绝缘、标记隐患、安排修复；不允许的动作会被拦下并说明原因。"""
    action = str(payload.values.get("action") or "").strip()
    entry, message = service.run_action(entry_id, action)
    if entry is None:
        return ActionResult(ok=False, message=message)
    return ActionResult(ok=True, message=message, entry=entry)

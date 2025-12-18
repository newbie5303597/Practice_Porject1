"""工单存储模块：封装对 Issue 相关的数据库操作。"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence

from fastapi import logger
from sqlalchemy import select, Row, RowMapping
from sqlalchemy.orm import Session

from .entities import IssueORM
from .models import IssueHistoryEntry, IssueState, Role


def _ensure_history_list(history: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """避免 history 为 None，统一转换为列表。"""
    return list(history or [])


def issue_to_dict(issue: IssueORM) -> Dict[str, Any]:
    """把 IssueORM 转换为 Python 字典，方便交给 Pydantic。"""
    return {
        "id": issue.id,
        "problem_description": issue.problem_description,
        "occurred_at": issue.occurred_at,
        "location": issue.location,
        "creator_id": issue.creator_id,
        "state": issue.state,
        "developer_analysis": issue.developer_analysis,
        "developer_solution": issue.developer_solution,
        "developer_decision": issue.developer_decision,
        "created_at": issue.created_at,
        "updated_at": issue.updated_at,
        "history": [IssueHistoryEntry(**entry) for entry in _ensure_history_list(issue.history)],
    }

def create_issue(
    db: Session,
    *,
    creator_id: int,
    description: str,
    occurred_at: datetime,
    location: str,
) -> IssueORM:
    """创建一个新的工单并保存到数据库。"""
    history = [
        IssueHistoryEntry(actor_id=creator_id, action="created", notes="提交工单").model_dump(),
        IssueHistoryEntry(actor_id=creator_id, action="submitted_to_developer").model_dump(),
    ]
    issue = IssueORM(
        problem_description=description,
        occurred_at=occurred_at,
        location=location,
        creator_id=creator_id,
        history=history,
    )
    try:
        db.add(issue)
        db.commit()
        db.refresh(issue)
    except Exception as e:
        db.rollback()  # 事务回滚，避免脏数据
        logger.error(f"创建工单失败：{e}")  # 记录错误日志
        raise  # 抛出异常，让调用方处理
    return issue

def list_issues_for_user(db: Session, *, user_id: int, role: Role) -> Sequence[IssueORM]:
    """根据用户角色筛选他可以看到的工单列表。"""
    stmt = select(IssueORM)
    if role == Role.customer:
        stmt = stmt.where(IssueORM.creator_id == user_id)
    elif role == Role.developer:
        stmt = stmt.where(IssueORM.state.in_([IssueState.PENDING_DEVELOPER, IssueState.RETURNED]))
    return db.execute(stmt.order_by(IssueORM.updated_at.desc())).scalars().all()

def get_issue(db: Session, issue_id: int) -> Optional[IssueORM]:
    """按主键获取工单。"""
    return db.get(IssueORM, issue_id)



def save_issue(db: Session, issue: IssueORM) -> IssueORM:
    """更新工单的统一入口，自动更新时间。"""
    issue.updated_at = datetime.utcnow()
    db.add(issue)
    db.commit()
    db.refresh(issue)
    return issue

def append_history(issue: IssueORM, *, actor_id: int, action: str, notes: Optional[str] = None) -> None:
    """向工单追加一条历史记录。"""
    history = _ensure_history_list(issue.history)
    history.append(IssueHistoryEntry(actor_id=actor_id, action=action, notes=notes).model_dump())
    issue.history = history
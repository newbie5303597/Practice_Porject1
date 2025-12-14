"""领域模型与 Pydantic Schema。"""
from datetime import datetime
from enum import Enum
from typing import Optional, List

from pydantic import BaseModel, Field


class Role(str, Enum):
    """系统中三个角色：客户、开发、项目经理"""
    customer = "customer"
    developer = "developer"
    PRODUCT_MANAGER = "product_manager"

class IssueState(str, Enum):
    """工单的状态机枚举。"""

    # 实际上工单状态为：工单创建（草稿状态）、工单申请中（工单审批状态）、工单完成、工单退回
    DRAFT = "draft"  # 草稿（当前示例未使用，可扩展）
    PENDING_DEVELOPER = "pending_developer"  # 待开发审批
    DEVELOPER_APPROVED = "developer_approved"  # 开发已通过
    RETURNED = "returned"  # 已退回

class IssueHistoryEntry(BaseModel):
    """工单流转历史中的一条记录。"""

    timestamp: datetime = Field(default_factory=datetime.utcnow)
    actor_id: int
    action: str
    notes: Optional[str] = None

# === 请求/响应 Schema ===

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class IssueCreateRequest(BaseModel):
    """创建工单时的请求体。"""

    problem_description: str = Field(..., min_length=5, description="问题描述")
    occurred_at: datetime = Field(..., description="问题发生时间")
    location: str = Field(..., min_length=2, description="问题发生地点")


class IssueUpdateRequest(BaseModel):
    """修改工单时的请求体（可选字段）。"""

    problem_description: Optional[str] = Field(None, min_length=5)
    occurred_at: Optional[datetime] = None
    location: Optional[str] = Field(None, min_length=2)
    resubmit: bool = Field(False, description="是否重新提交给开发")


class DeveloperDecisionRequest(BaseModel):
    """开发审批时的请求体。"""

    analysis: str = Field(..., min_length=5, description="问题分析")
    solution: str = Field(..., min_length=5, description="解决方案")
    decision: str = Field(..., pattern="^(approve|disapprove)$", description="审批结论")




class IssueResponse(BaseModel):
    """返回给前端的工单结构。"""

    id: int
    problem_description: str
    occurred_at: datetime
    location: str
    creator_id: int
    state: IssueState
    developer_analysis: Optional[str]
    developer_solution: Optional[str]
    developer_decision: Optional[str]
    created_at: datetime
    updated_at: datetime
    history: List[IssueHistoryEntry]

    class Config:
        from_attributes = True  # 允许从 ORM 对象转换而来
"""领域模型与 Pydantic Schema。"""
from enum import Enum


class Role(str, Enum):
    """系统中三个角色：客户、开发、项目经理"""
    customer = "customer"
    developer = "developer"
    PRODUCT_MANAGER = "product_manager"

class IssueState(str, Enum):
    """工单的状态机枚举。"""

    DRAFT = "draft"  # 草稿（当前示例未使用，可扩展）
    PENDING_DEVELOPER = "pending_developer"  # 待开发审批
    DEVELOPER_APPROVED = "developer_approved"  # 开发已通过
    RETURNED = "returned"  # 已退回

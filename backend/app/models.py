"""领域模型与 Pydantic Schema。"""
from enum import Enum


class Role(str, Enum):
    """系统中三个角色：客户、开发、项目经理"""
    customer = "customer"
    developer = "developer"
    PRODUCT_MANAGER = "product_manager"
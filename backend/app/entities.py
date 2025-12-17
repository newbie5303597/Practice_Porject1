"""SQLAlchemy ORM 实体类，对应数据库中的表结构。"""
from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import Column, Integer, String, Enum, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship

from backend.app.database import Base
from backend.app.models import Role, IssueState


class UserORM(Base):
    """用户表：保存账号、角色和密码哈希。"""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    full_name = Column(String(100), nullable=False)
    role = Column(Enum(Role), nullable=False)
    password_hash = Column(String(255), nullable=False)

    # 反向关联：一个用户可以创建多个 issue
    issues = relationship("IssueORM", back_populates="creator")

class IssueORM(Base):
    """工单表：保存工单基本信息和审批状态。"""

    __tablename__ = "issues"

    id = Column(Integer, primary_key=True, index=True)
    problem_description = Column(Text, nullable=False)
    occurred_at = Column(DateTime, nullable=False)
    location = Column(String(255), nullable=False)

    creator_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    creator = relationship("UserORM", back_populates="issues")

    state = Column(Enum(IssueState), default=IssueState.PENDING_DEVELOPER, nullable=False)
    developer_analysis = Column(Text, nullable=True)
    developer_solution = Column(Text, nullable=True)
    developer_decision = Column(String(50), nullable=True)

    # 使用 JSON 字段保存流转历史，简单直观
    history = Column(JSON, default=list, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
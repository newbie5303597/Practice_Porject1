"""FastAPI 应用入口：路由定义、依赖注入、启动配置。"""

from __future__ import annotations

import logging

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from .auth import seed_initial_users, authenticate_user, create_access_token, get_current_user, require_roles
from .config import get_settings
from .database import engine, Base, get_db
from .entities import IssueORM
from .models import TokenResponse, LoginRequest, IssueResponse, IssueCreateRequest, Role, IssueUpdateRequest, \
    IssueState, DeveloperDecisionRequest
from .storage import create_issue, issue_to_dict, list_issues_for_user, get_issue, append_history, save_issue

settings = get_settings()

# 配置日志输出格式
logging.basicConfig(level=settings.log_level, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("approve-system")

# 创建数据库表（生产建议使用 Alembic 迁移）
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Approve System API", version="0.1.0")

# 允许前端跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # 生产中改成具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 应用启动时，确保默认账号已经存在
seed_initial_users()
logger.info("Default demo accounts ready.")


@app.post("/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest) -> TokenResponse:
    """登录接口：验证用户名密码，返回 JWT。"""
    user = authenticate_user(payload.username, payload.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")
    token = create_access_token(subject=user["id"], role=user["role"])
    return TokenResponse(access_token=token, user=user)


@app.get("/me")
def read_profile(current_user: dict = Depends(get_current_user)) -> dict:
    """获取当前登录用户信息。"""
    return current_user


@app.post("/issues", response_model=IssueResponse)
def create_issue_endpoint(
    payload: IssueCreateRequest,
    current_user: dict = Depends(require_roles(Role.customer, Role.PRODUCT_MANAGER)),
    db: Session = Depends(get_db),
) -> IssueResponse:
    """创建工单：客户/产品经理可以调用。"""
    issue = create_issue(
        db,
        creator_id=current_user["id"],
        description=payload.problem_description,
        occurred_at=payload.occurred_at,
        location=payload.location,
    )
    logger.info("Issue %s created by user %s", issue.id, current_user["id"])
    return IssueResponse.model_validate(issue_to_dict(issue))


@app.get("/issues", response_model=list[IssueResponse])
def list_issues(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[IssueResponse]:
    """根据角色返回当前用户可见的工单列表。"""
    issues = list_issues_for_user(db, user_id=current_user["id"], role=current_user["role"])
    return [IssueResponse.model_validate(issue_to_dict(i)) for i in issues]


def _ensure_issue_access(db: Session, issue_id: int, current_user: dict) -> IssueORM:
    """内部工具：检查当前用户是否有权限访问某个工单。"""
    issue = get_issue(db, issue_id)
    if not issue:
        raise HTTPException(status_code=404, detail="工单不存在")
    role = current_user["role"]
    if role == Role.customer and issue.creator_id != current_user["id"]:
        raise HTTPException(status_code=403, detail="无法查看其他用户工单")
    return issue


@app.get("/issues/{issue_id}", response_model=IssueResponse)
def retrieve_issue(
    issue_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> IssueResponse:
    """工单详情接口。"""
    issue = _ensure_issue_access(db, issue_id, current_user)
    return IssueResponse.model_validate(issue_to_dict(issue))


@app.put("/issues/{issue_id}", response_model=IssueResponse)
def update_issue(
    issue_id: int,
    payload: IssueUpdateRequest,
    current_user: dict = Depends(require_roles(Role.customer, Role.PRODUCT_MANAGER)),
    db: Session = Depends(get_db),
) -> IssueResponse:
    """修改/重新提交工单（仅创建者且状态为草稿/退回时）。"""
    issue = _ensure_issue_access(db, issue_id, current_user)
    if issue.state not in {IssueState.DRAFT, IssueState.RETURNED}:
        raise HTTPException(status_code=400, detail="当前状态不可编辑")
    if issue.creator_id != current_user["id"]:
        raise HTTPException(status_code=403, detail="仅创建者可修改工单")

    if payload.problem_description:
        issue.problem_description = payload.problem_description
    if payload.occurred_at:
        issue.occurred_at = payload.occurred_at
    if payload.location:
        issue.location = payload.location
    if payload.resubmit:
        issue.state = IssueState.PENDING_DEVELOPER
        append_history(issue, actor_id=current_user["id"], action="resubmitted")

    append_history(issue, actor_id=current_user["id"], action="updated")
    save_issue(db, issue)
    return IssueResponse.model_validate(issue_to_dict(issue))


@app.post("/issues/{issue_id}/decision", response_model=IssueResponse)
def developer_decision(
    issue_id: int,
    payload: DeveloperDecisionRequest,
    current_user: dict = Depends(require_roles(Role.developer)),
    db: Session = Depends(get_db),
) -> IssueResponse:
    """开发审批接口：通过/驳回工单。"""
    issue = get_issue(db, issue_id)
    if not issue:
        raise HTTPException(status_code=404, detail="工单不存在")
    if issue.state not in {IssueState.PENDING_DEVELOPER, IssueState.RETURNED}:
        raise HTTPException(status_code=400, detail="当前状态无需开发审批")

    issue.developer_analysis = payload.analysis
    issue.developer_solution = payload.solution
    issue.developer_decision = payload.decision

    if payload.decision == "approve":
        issue.state = IssueState.DEVELOPER_APPROVED
        append_history(issue, actor_id=current_user["id"], action="approved")
    else:
        issue.state = IssueState.RETURNED
        append_history(issue, actor_id=current_user["id"], action="disapproved", notes="退回修改")

    save_issue(db, issue)
    logger.info("Issue %s decision set to %s by user %s", issue.id, payload.decision, current_user["id"])
    return IssueResponse.model_validate(issue_to_dict(issue))


if __name__ == "__main__":
    # 方便本地开发：直接 python -m app.main 即可启动
    import uvicorn

    uvicorn.run(
        "backend.app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.reload,
    )
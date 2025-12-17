"""认证与授权模块：登录、生成 JWT、角色校验等。"""
from datetime import timedelta, datetime
from typing import Optional, Callable

from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.testing.pickleable import User
from starlette import status

from backend.app.config import get_settings
from backend.app.database import session_scope, SessionLocal
from backend.app.entities import UserORM
from backend.app.models import Role

settings = get_settings()

# 使用 PBKDF2 对密码进行加密（避免明文存储）
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

# OAuth2 标准的 token 获取方式（前端通过 /auth/login 获得 token）
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def _user_to_dict(user: User) -> dict:
    """把 ORM 用户对象转换成 dict，过滤掉密码哈希字段。"""
    return {
        "id": user.id,
        "username": user.username,
        "full_name": user.full_name,
        "role": user.role,
    }

def seed_initial_users() -> None:
    """
       在应用启动时初始化三种默认账号。
       这个函数是“幂等”的：如果表中已经有用户，就不会重复插入。
    """
    default_users = [
        ("pm_lead", "Product Manager", Role.PRODUCT_MANAGER, "pm123456"),
        ("dev_master", "Lead Developer", Role.DEVELOPER, "dev123456"),
        ("customer_zero", "Customer One", Role.CUSTOMER, "cust123456"),
    ]
    with session_scope() as session:
        existing = session.execute(select(UserORM)).scalars().all()
        if existing:
            return

        for username, full_name, role, raw_password in default_users:
            session.add(
                UserORM(
                    username=username,
                    full_name=full_name,
                    role=role,
                    password_hash=hash_password(raw_password),
                )
            )

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def authenticate_user(username: str, password: str) -> Optional[dict]:
    """
    用于登录：根据用户名查用户，验证密码是否正确。
    成功返回用户 dict，失败返回 None。
    """
    with SessionLocal() as session:
        user = session.execute(
            select(UserORM).where(UserORM.username == username)
        ).scalar_one_or_none()
        if not user or not verify_password(password, user.password_hash):
            return None
        return _user_to_dict(user)


def create_access_token(*, subject: int, role: Role, expires_delta: Optional[timedelta] = None) -> str:
    """创建 JWT 访问令牌。"""
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    to_encode = {"sub": str(subject), "role": role.value, "exp": expire}
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)


async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """
    FastAPI 依赖项：从请求头中解析 JWT，得到当前登录用户。
    如果 token 无效或过期，将抛出 401。
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证用户身份",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        user_id = int(payload.get("sub", 0))
    except (JWTError, ValueError):
        raise credentials_exception

    with SessionLocal() as session:
        user = session.get(UserORM, user_id)
        if not user:
            raise credentials_exception
        return _user_to_dict(user)


def require_roles(*roles: Role) -> Callable:
    """
    用于装饰路由的角色检查依赖。
    使用方法：
        current_user: dict = Depends(require_roles(Role.DEVELOPER))
    """
    async def dependency(current_user: dict = Depends(get_current_user)) -> dict:
        if current_user["role"] not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="权限不足")
        return current_user

    return dependency
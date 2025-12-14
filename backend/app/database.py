"""数据库连接与 Session 管理模块。"""
import os
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session

from backend.app.config import get_settings

settings = get_settings()

# 创建数据库连接 URL
database_url = settings.database_url

# 针对 SQLite 需要设置 check_same_thread=False，并确保目录存在
connect_args = {}
if database_url.startswith("sqlite"):

    # 1. 关闭SQLite的同线程检查（解决多线程报错）
    connect_args["check_same_thread"] = False
    #  # 2. 提取数据库文件的本地路径（如：sqlite:///./data/app.db → ./data/app.db） 例如 sqlite:///./data/app.db，确保 data 目录存在
    db_path = database_url.replace("sqlite:///", "", 1)
    # 3. 创建数据库文件所在的目录（如：./data），exist_ok=True表示目录已存在时不报错
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

# 创建 SQLAlchemy Engine（底层连接池）
engine = create_engine(database_url, connect_args=connect_args, future=True)

# 创建 Session 工厂，用于生成每个请求独立的 Session 对象
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
    future=True,
)

# 声明式 Base，所有 ORM 模型都要继承它
Base = declarative_base()

def get_db() -> Generator[Session, None, None]:
    """
    FastAPI 依赖项：
    每次请求时创建一个数据库 Session，请求结束后自动关闭。
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """
    脚本/初始化阶段使用的上下文管理器。
    自动处理提交/回滚，防止事务不一致。
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


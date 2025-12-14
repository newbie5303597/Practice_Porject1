"""应用配置模块：集中管理所有可配置项（端口、数据库、密钥等）"""
import os
from dataclasses import Field
from functools import lru_cache

from dotenv import load_dotenv
from pydantic import  BaseModel, Field

# 读取同目录或上级目录中的 .env 文件
load_dotenv(verbose=True)

class Settings(BaseModel):
    """使用 Pydantic 定义配置结构，并提供默认值。"""

    app_name: str = Field(default="Approve System")

    # JWT 密钥（生产环境务必使用强随机串，并通过环境变量注入）
    secret_key: str = Field(default=os.getenv("SECRET_KEY", "dev-secret-key-change-me"))

    # JWT 过期时间
    access_token_expire_min : int = Field(
        default=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "120"))
    )
    # JWT 算法
    algorithm: str = Field(default="HS256")

    # 服务监听地址与端口
    host: str = Field(default=os.getenv("APP_HOST", "127.0.0.1"))
    port: int = Field(default=int(os.getenv("APP_PORT", "8000")))
    reload: bool = Field(default=os.getenv("APP_RELOAD", "true"))

    # 数据库连接 URL，默认使用 SQLite 文件
    # 生产中推荐：postgresql://user:pass@host:port/dbname
    database_url: str = Field(
        default=os.getenv("APP_DATABASE_URL", "sqlite:///./data/app.db")
    )

    # 日志级别：DEBUG / INFO / WARNING / ERROR
    log_level: str = Field(default=os.getenv("APP_LOG_LEVEL", "INFO"))

@lru_cache
def get_settings() -> Settings:
    """使用缓存，避免每次都重新读取环境变量。"""
    return Settings()
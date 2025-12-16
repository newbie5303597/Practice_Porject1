from pydantic import BaseModel
from sqlalchemy import Column, Integer, String

from backend.app.database import Base


class UserORM(Base):

    _tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True)
    fullname = Column(String(50), unique=True, index=True)
    email = Column(String(50), unique=True, index=True)
    role = Column((50), index=True)


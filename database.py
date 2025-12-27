"""数据库配置和会话管理"""

from typing import AsyncGenerator
from sqlmodel import SQLModel, create_engine
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from config import settings

# 创建同步数据库引擎（用于初始化和脚本）
sync_engine = create_engine(
    settings.database_url.replace("sqlite+aiosqlite:///", "sqlite:///"),
    echo=settings.debug,
    connect_args={"check_same_thread": False}
    if "sqlite" in settings.database_url
    else {},
)

# 创建异步数据库引擎
async_engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    connect_args={"check_same_thread": False}
    if "sqlite" in settings.database_url
    else {},
)

# 创建异步会话工厂
async_session_maker = async_sessionmaker(
    async_engine, class_=AsyncSession, expire_on_commit=False
)


def create_db_and_tables():
    """创建数据库表（同步方式，用于初始化）"""
    SQLModel.metadata.create_all(sync_engine)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """获取数据库会话的依赖项"""
    async with async_session_maker() as session:
        yield session

"""数据库模型"""

from datetime import datetime
from typing import Optional
from sqlmodel import Field, SQLModel


class RedeemCode(SQLModel, table=True):
    """兑换码表"""

    __tablename__ = "redeem_codes"

    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(unique=True, index=True, description="兑换码")
    is_used: bool = Field(default=False, description="是否已被使用")
    used_by: Optional[int] = Field(default=None, description="使用者用户ID")
    used_at: Optional[datetime] = Field(default=None, description="使用时间")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")


class UserRedeemRecord(SQLModel, table=True):
    """用户兑换记录表"""

    __tablename__ = "user_redeem_records"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True, description="用户ID")
    username: str = Field(description="用户名")
    redeem_code_id: int = Field(description="兑换码ID")
    code: str = Field(description="兑换码内容")
    redeemed_at: datetime = Field(default_factory=datetime.now, description="兑换时间")

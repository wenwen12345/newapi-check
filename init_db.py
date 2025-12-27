"""数据库初始化脚本"""

from database import create_db_and_tables
from models import RedeemCode, UserRedeemRecord


def init_database():
    """初始化数据库，创建所有表"""
    print("开始初始化数据库...")
    create_db_and_tables()
    print("数据库初始化完成！")
    print("已创建以下表：")
    print("  - redeem_codes (兑换码表)")
    print("  - user_redeem_records (用户兑换记录表)")


if __name__ == "__main__":
    init_database()

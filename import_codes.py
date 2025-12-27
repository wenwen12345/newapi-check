"""兑换码导入脚本"""

import sys
from datetime import datetime
from sqlmodel import Session, select
from database import sync_engine
from models import RedeemCode


def import_codes_from_file(file_path: str):
    """
    从文件导入兑换码

    Args:
        file_path: 兑换码文件路径，每行一个兑换码
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            codes = [line.strip() for line in f if line.strip()]

        if not codes:
            print("❌ 文件为空或没有有效的兑换码")
            return

        print(f"📖 从文件中读取到 {len(codes)} 个兑换码")

        # 导入到数据库
        with Session(sync_engine) as session:
            # 检查重复
            existing_codes = session.exec(
                select(RedeemCode.code).where(RedeemCode.code.in_(codes))
            ).all()

            existing_codes_set = set(existing_codes)
            new_codes = [code for code in codes if code not in existing_codes_set]

            if existing_codes:
                print(f"⚠️  跳过 {len(existing_codes)} 个已存在的兑换码")

            if not new_codes:
                print("✅ 没有新的兑换码需要导入")
                return

            # 批量插入新兑换码
            for code in new_codes:
                redeem_code = RedeemCode(code=code)
                session.add(redeem_code)

            session.commit()
            print(f"✅ 成功导入 {len(new_codes)} 个兑换码")

            # 统计信息
            total = session.exec(select(RedeemCode)).all()
            used = session.exec(
                select(RedeemCode).where(RedeemCode.is_used == True)
            ).all()
            available = len(total) - len(used)

            print(f"\n📊 数据库统计:")
            print(f"  - 总兑换码数: {len(total)}")
            print(f"  - 已使用: {len(used)}")
            print(f"  - 可用: {available}")

    except FileNotFoundError:
        print(f"❌ 文件不存在: {file_path}")
    except Exception as e:
        print(f"❌ 导入失败: {str(e)}")


def import_codes_from_list(codes: list):
    """
    从列表导入兑换码

    Args:
        codes: 兑换码列表
    """
    if not codes:
        print("❌ 兑换码列表为空")
        return

    print(f"📝 准备导入 {len(codes)} 个兑换码")

    with Session(sync_engine) as session:
        # 检查重复
        existing_codes = session.exec(
            select(RedeemCode.code).where(RedeemCode.code.in_(codes))
        ).all()

        existing_codes_set = set(existing_codes)
        new_codes = [code for code in codes if code not in existing_codes_set]

        if existing_codes:
            print(f"⚠️  跳过 {len(existing_codes)} 个已存在的兑换码")

        if not new_codes:
            print("✅ 没有新的兑换码需要导入")
            return

        # 批量插入新兑换码
        for code in new_codes:
            redeem_code = RedeemCode(code=code)
            session.add(redeem_code)

        session.commit()
        print(f"✅ 成功导入 {len(new_codes)} 个兑换码")


def generate_sample_codes(count: int = 10, prefix: str = "CODE"):
    """
    生成示例兑换码

    Args:
        count: 生成数量
        prefix: 兑换码前缀
    """
    import secrets
    import string

    codes = []
    for i in range(count):
        random_str = "".join(
            secrets.choice(string.ascii_uppercase + string.digits) for _ in range(12)
        )
        codes.append(f"{prefix}-{random_str}")

    return codes


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("使用方法:")
        print("  1. 从文件导入: python import_codes.py <文件路径>")
        print("     例如: python import_codes.py codes.txt")
        print()
        print("  2. 生成并导入示例兑换码: python import_codes.py --sample [数量]")
        print("     例如: python import_codes.py --sample 100")
        sys.exit(1)

    if sys.argv[1] == "--sample":
        count = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        print(f"🎲 生成 {count} 个示例兑换码...")
        sample_codes = generate_sample_codes(count)
        import_codes_from_list(sample_codes)
    else:
        file_path = sys.argv[1]
        import_codes_from_file(file_path)

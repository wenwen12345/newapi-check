"""生成测试兑换码并导入"""

from import_codes import generate_sample_codes, import_codes_from_list

# 生成 20 个示例兑换码
codes = generate_sample_codes(20, prefix="TEST")
print(f"生成了 {len(codes)} 个兑换码")

# 导入到数据库
import_codes_from_list(codes)

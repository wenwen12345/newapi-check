#!/bin/bash

echo "🚀 开始设置每日兑换码系统..."

# 检查 .env 文件
if [ ! -f .env ]; then
    echo "📝 复制环境变量配置文件..."
    cp .env.example .env
    echo "⚠️  请编辑 .env 文件，填入你的 OAuth2 凭据"
fi

# 安装依赖
echo "📦 安装依赖..."
uv sync

# 初始化数据库
echo "🗄️  初始化数据库..."
uv run python init_db.py

# 生成测试兑换码
echo "🎁 生成测试兑换码..."
uv run python generate_test_codes.py

echo ""
echo "✅ 设置完成！"
echo ""
echo "现在可以运行以下命令启动应用："
echo "  uv run python main.py"
echo ""
echo "或使用开发模式："
echo "  uv run uvicorn main:app --host 0.0.0.0 --port 8181 --reload"
echo ""
echo "然后访问: http://localhost:8181"

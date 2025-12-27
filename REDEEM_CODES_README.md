# 每日兑换码功能使用说明

## 功能概述

该功能允许用户每天领取一个兑换码。兑换码通过 New API 实时创建，用户通过 OAuth2 认证后可以领取。

## ⚠️ 重要更新

**版本 2.0 - 实时创建模式**

兑换码现在改为实时创建模式，不再需要预先导入兑换码到数据库。每次用户领取时，系统会自动调用 New API 创建新的兑换码。

## 快速开始

### 1. 安装依赖

```bash
uv sync
```

### 2. 配置环境变量

复制 `.env.example` 文件为 `.env`：

```bash
cp .env.example .env
```

编辑 `.env` 文件，配置 New API 信息：

```bash
# New API 配置（必需）
NEWAPI_SITE_URL=https://your-newapi-site.com
NEWAPI_ACCESS_TOKEN=sk-your-access-token-here
NEWAPI_USER=admin
NEWAPI_REDEEM_QUOTA=500000  # 每次创建的兑换码额度（默认 500000 tokens）
```

**配置说明：**
- `NEWAPI_SITE_URL`: 你的 New API 站点地址，例如 `https://api.example.com`
- `NEWAPI_ACCESS_TOKEN`: 你的 New API 管理员 Access Token（需要管理员权限）
- `NEWAPI_USER`: New API 用户标识（用于 `New-Api-User` 请求头，通常是管理员用户名）
- `NEWAPI_REDEEM_QUOTA`: 每次创建兑换码的额度，默认 500000 tokens

### 3. 初始化数据库

```bash
uv run python init_db.py
```

输出示例：
```
开始初始化数据库...
数据库初始化完成！
已创建以下表：
  - redeem_codes (兑换码表 - 已废弃，保留用于历史记录)
  - user_redeem_records (用户兑换记录表)
```

### 4. 启动应用

```bash
uv run python main.py
```

或者：

```bash
uv run uvicorn main:app --host 0.0.0.0 --port 8181 --reload
```

## 使用流程

### 1. 用户登录

访问 `http://localhost:8181` 并点击"使用 Linux.do 登录"按钮进行 OAuth2 认证。

### 2. 领取兑换码

登录成功后，有两种方式领取兑换码：

#### 方式一：通过 Web 页面

1. 访问 `http://localhost:8181/redeem`
2. 输入登录后获得的 `access_token`
3. 点击"领取今日兑换码"按钮
4. 成功后会显示兑换码和领取历史

#### 方式二：通过 API

```bash
# 领取兑换码
curl -X POST "http://localhost:8181/api/redeem/daily?access_token=YOUR_ACCESS_TOKEN"

# 查看领取历史
curl "http://localhost:8181/api/redeem/history?access_token=YOUR_ACCESS_TOKEN"
```

## API 端点

### POST /api/redeem/daily

每日领取兑换码

**参数：**
- `access_token` (query, required): 用户的访问令牌

**响应示例：**
```json
{
  "success": true,
  "message": "领取成功！",
  "data": {
    "code": "CODE-ABC123DEF456",
    "redeemed_at": "2025-12-27T10:30:00"
  }
}
```

**错误响应：**
```json
{
  "detail": "今天已经领取过兑换码了，请明天再来！"
}
```

### GET /api/redeem/history

获取用户的兑换历史记录

**参数：**
- `access_token` (query, required): 用户的访问令牌

**响应示例：**
```json
{
  "success": true,
  "data": {
    "total": 5,
    "history": [
      {
        "code": "CODE-ABC123DEF456",
        "redeemed_at": "2025-12-27T10:30:00"
      },
      {
        "code": "CODE-XYZ789GHI012",
        "redeemed_at": "2025-12-26T09:15:00"
      }
    ]
  }
}
```

### GET /redeem

兑换码领取的 Web 页面

## 数据库结构

### redeem_codes 表（兑换码表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 |
| code | VARCHAR | 兑换码（唯一） |
| is_used | BOOLEAN | 是否已被使用 |
| used_by | INTEGER | 使用者用户ID |
| used_at | DATETIME | 使用时间 |
| created_at | DATETIME | 创建时间 |

### user_redeem_records 表（用户兑换记录表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 |
| user_id | INTEGER | 用户ID |
| username | VARCHAR | 用户名 |
| redeem_code_id | INTEGER | 兑换码ID |
| code | VARCHAR | 兑换码内容 |
| redeemed_at | DATETIME | 兑换时间 |

## 功能特点

1. **每日限制**：每个用户每天只能领取一次兑换码
2. **自动分配**：从未使用的兑换码中自动分配
3. **记录追踪**：保存完整的兑换记录
4. **防重复**：自动检测重复导入的兑换码
5. **OAuth2 认证**：使用 Linux.do OAuth2 进行用户身份验证

## 常见问题

### Q: 如何重置每日领取限制？

A: 系统按自然日（00:00:00 - 23:59:59）计算，第二天会自动重置。如需手动重置，可删除数据库中对应日期的记录。

### Q: 兑换码用完了怎么办？

A: 使用 `import_codes.py` 脚本导入新的兑换码即可。

### Q: 如何查看剩余兑换码数量？

A: 可以通过以下 Python 脚本查看：

```python
from database import sync_engine
from sqlmodel import Session, select
from models import RedeemCode

with Session(sync_engine) as session:
    total = session.exec(select(RedeemCode)).all()
    used = session.exec(select(RedeemCode).where(RedeemCode.is_used == True)).all()
    print(f"总数: {len(total)}, 已使用: {len(used)}, 剩余: {len(total) - len(used)}")
```

### Q: 可以修改兑换码格式吗？

A: 可以。只需确保兑换码是字符串格式即可，没有长度或格式限制。

### Q: 数据库文件在哪里？

A: 默认在项目根目录下的 `redeem_codes.db` 文件。

## 注意事项

1. **生产环境**：建议使用 PostgreSQL 或 MySQL 等生产级数据库
2. **Token 安全**：不要在前端暴露 `access_token`，建议使用 Cookie 或 Session
3. **兑换码安全**：确保兑换码不易被猜测，建议使用随机生成
4. **并发处理**：当前实现已处理并发情况，避免同一用户重复领取

## 扩展功能建议

1. 添加兑换码有效期
2. 添加兑换码类型（如不同奖励）
3. 添加管理后台
4. 添加统计分析功能
5. 添加邮件或通知功能

## License

MIT License

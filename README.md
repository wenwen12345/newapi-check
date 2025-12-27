# Linux.do OAuth2 登录集成示例

这是一个使用 FastAPI 集成 Linux.do OAuth2 认证的示例项目，使用 uv 作为包管理工具。

## 功能特性

- 完整的 OAuth2 授权流程实现
- 使用授权码换取 access token
- 使用 refresh token 刷新 access token
- 获取用户信息
- **每日兑换码领取功能** 🎁
  - 每个用户每天可领取一个兑换码
  - 自动记录领取历史
  - 支持批量导入兑换码
- 美观的 Web 界面
- 完整的 API 文档（Swagger UI）

## 技术栈

- Python 3.12+
- FastAPI - 现代、快速的 Web 框架
- SQLModel - SQL 数据库 ORM
- SQLite/aiosqlite - 异步数据库
- httpx - 异步 HTTP 客户端
- pydantic-settings - 配置管理
- uvicorn - ASGI 服务器
- uv - 快速的 Python 包管理器

## 快速开始

### 1. 安装依赖

确保已安装 uv，然后运行：

```bash
uv sync
```

### 2. 配置环境变量

复制 `.env.example` 到 `.env` 并填写你的配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```env
# 使用你自己的 client_id 和 client_secret
OAUTH2_CLIENT_ID=your_client_id_here
OAUTH2_CLIENT_SECRET=your_client_secret_here
OAUTH2_REDIRECT_URI=http://localhost:8181/oauth2/callback

# 服务器配置
HOST=0.0.0.0
PORT=8181
```

**注意**：`.env.example` 中的测试凭据仅供演示使用，请在始皇论坛申请你自己的应用凭据。

### 3. 初始化数据库

```bash
uv run python init_db.py
```

### 4. 导入兑换码（可选）

生成并导入测试兑换码：

```bash
uv run python generate_test_codes.py
```

或从文件导入：

```bash
uv run python import_codes.py codes.txt
```

### 5. 运行应用

```bash
uv run python main.py
```

或者使用 uvicorn：

```bash
uv run uvicorn main:app --host 0.0.0.0 --port 8181 --reload
```

### 6. 访问应用

打开浏览器访问：

- 主页：http://localhost:8181
- 领取兑换码：http://localhost:8181/redeem
- API 文档：http://localhost:8181/docs
- 健康检查：http://localhost:8181/health

## OAuth2 认证流程

### 1. 获取授权码

访问 `/login` 端点，应用会重定向到 Linux.do 授权页面：

```
GET /login
```

用户同意授权后，会重定向回：
```
http://localhost:8181/oauth2/callback?code=YOUR_CODE&state=STATE
```

### 2. 使用 curl 手动测试

如果你想使用 curl 手动测试整个流程：

#### 步骤 1: 获取授权码

在浏览器中打开授权 URL：
```
https://connect.linux.do/oauth2/authorize?response_type=code&client_id=YOUR_CLIENT_ID&redirect_uri=http://localhost:8181/oauth2/callback&state=test_state
```

同意授权后，从重定向的 URL 中获取 `code` 参数。

#### 步骤 2: 生成 Basic Auth Header

将 `client_id:client_secret` 编码为 Base64：

使用 Python：
```python
import base64
credentials = "YOUR_CLIENT_ID:YOUR_CLIENT_SECRET"
encoded = base64.b64encode(credentials.encode()).decode()
print(f"Basic {encoded}")
```

或使用命令行：
```bash
echo -n "YOUR_CLIENT_ID:YOUR_CLIENT_SECRET" | base64
```

#### 步骤 3: 换取 Token

```bash
curl -X POST \
  -H "Authorization: Basic YOUR_BASE64_ENCODED_CREDENTIALS" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=authorization_code&code=YOUR_CODE&redirect_uri=http://localhost:8181/oauth2/callback" \
  https://connect.linux.do/oauth2/token
```

响应示例：
```json
{
  "access_token": "eyJhb...",
  "expires_in": 3600,
  "refresh_token": "e187zHrR...",
  "token_type": "bearer"
}
```

#### 步骤 4: 获取用户信息

```bash
curl -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  https://connect.linux.do/api/user
```

响应示例：
```json
{
  "id": 124,
  "username": "Bee",
  "name": "(  ⩌   ˰ ⩌)",
  "active": true,
  "trust_level": 2,
  "silenced": false
}
```

#### 步骤 5: 刷新 Token

```bash
curl -X POST \
  -H "Authorization: Basic YOUR_BASE64_ENCODED_CREDENTIALS" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=refresh_token&refresh_token=YOUR_REFRESH_TOKEN" \
  https://connect.linux.do/oauth2/token
```

## API 端点

### Web 界面

| 端点 | 方法 | 说明 |
|------|------|------|
| `/` | GET | 首页，显示登录按钮 |
| `/login` | GET | 开始 OAuth2 登录流程 |
| `/oauth2/callback` | GET | OAuth2 回调处理 |
| `/redeem` | GET | 兑换码领取页面 |

### API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/user` | GET | 获取用户信息 |
| `/refresh` | POST | 刷新 access token |
| `/api/redeem/daily` | POST | 领取每日兑换码 |
| `/api/redeem/history` | GET | 查看兑换历史 |
| `/health` | GET | 健康检查 |
| `/docs` | GET | Swagger API 文档 |

### 使用 API 端点

#### 获取用户信息

```bash
curl "http://localhost:8181/user?access_token=YOUR_ACCESS_TOKEN"
```

#### 刷新 Token

```bash
curl -X POST "http://localhost:8181/refresh?refresh_token=YOUR_REFRESH_TOKEN"
```

## 每日兑换码功能使用

### 使用流程

1. 访问首页 `http://localhost:8181`
2. 点击"使用 Linux.do 登录"
3. 完成 OAuth2 认证后，自动跳转到兑换码页面
4. 点击"领取今日兑换码"按钮即可领取
5. 查看领取历史记录

### 特点

- ✅ 无需手动输入 access_token，登录后自动获取
- ✅ 每个用户每天只能领取一次
- ✅ 自动显示用户信息和信任等级
- ✅ 实时查看领取历史
- ✅ 友好的错误提示

更多详细说明请查看 [REDEEM_CODES_README.md](./REDEEM_CODES_README.md)

## 项目结构

```
newapi-check/
├── main.py                    # FastAPI 应用主文件
├── oauth2_service.py          # OAuth2 服务逻辑
├── config.py                  # 配置管理
├── models.py                  # 数据库模型
├── database.py                # 数据库配置
├── init_db.py                 # 数据库初始化脚本
├── import_codes.py            # 兑换码导入脚本
├── generate_test_codes.py    # 生成测试兑换码
├── .env                       # 环境变量配置（需自行创建）
├── .env.example               # 环境变量模板
├── pyproject.toml             # 项目依赖配置
├── uv.lock                    # uv 锁定文件
├── README.md                  # 项目文档
├── REDEEM_CODES_README.md     # 兑换码功能详细文档
└── redeem_codes.db            # SQLite 数据库（运行后生成）
```

## 代码说明

### config.py

管理应用配置，使用 pydantic-settings 从环境变量加载配置。

### oauth2_service.py

核心 OAuth2 服务类，包含：
- `get_authorization_url()` - 生成授权 URL
- `exchange_code_for_token()` - 使用授权码换取 token
- `refresh_access_token()` - 刷新 access token
- `get_user_info()` - 获取用户信息

### main.py

FastAPI 应用，包含：
- Web 界面路由
- OAuth2 回调处理
- RESTful API 端点

## 注意事项

### 安全性

1. **生产环境配置**：
   - 不要将 `.env` 文件提交到 Git
   - 使用环境变量或密钥管理服务存储敏感信息
   - 使用 HTTPS 保护所有通信

2. **Token 存储**：
   - 示例代码使用内存存储 token，仅供演示
   - 生产环境应使用：
     - 数据库（PostgreSQL, MongoDB 等）
     - Redis 缓存
     - Session 存储

3. **State 参数**：
   - 示例代码生成了 state 但未验证
   - 生产环境应该：
     - 将 state 存储在 session 中
     - 在回调中验证 state 匹配
     - 防止 CSRF 攻击

### 申请 OAuth2 应用

在 Linux.do（始皇论坛）申请你自己的 OAuth2 应用：

1. 访问论坛的应用管理页面
2. 创建新应用
3. 设置回调 URL：`http://localhost:8181/oauth2/callback`
4. 获取 client_id 和 client_secret
5. 更新 `.env` 文件

## 开发调试

### 启用自动重载

```bash
uv run uvicorn main:app --reload
```

### 查看日志

应用会输出详细的日志信息，包括：
- 请求日志
- 错误信息
- OAuth2 流程状态

### 测试端点

使用 Swagger UI 测试 API：
```
http://localhost:8181/docs
```

## 常见问题

### Q: Token 过期怎么办？

A: 使用 refresh token 刷新：
```bash
curl -X POST "http://localhost:8181/refresh?refresh_token=YOUR_REFRESH_TOKEN"
```

### Q: 如何识别用户？

A: 使用用户的 `id` 字段，而不是 `username`，因为用户名可能会被修改。

### Q: 支持哪些 Python 版本？

A: 需要 Python 3.12 或更高版本。

## 参考资料

- [Linux.do OAuth2 文档](https://connect.linux.do/)
- [FastAPI 文档](https://fastapi.tiangolo.com/)
- [OAuth 2.0 RFC](https://tools.ietf.org/html/rfc6749)
- [uv 文档](https://github.com/astral-sh/uv)

## License

MIT License

## 贡献

欢迎提交 Issue 和 Pull Request！

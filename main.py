"""FastAPI 应用主文件 - Linux.do OAuth2 登录集成"""

from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.responses import RedirectResponse, HTMLResponse
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from config import settings
from oauth2_service import oauth2_service
from database import get_session, create_db_and_tables
from models import RedeemCode, UserRedeemRecord
from newapi_service import NewAPIService
from queue_manager import queue_manager, TaskStatus
import secrets

app = FastAPI(
    title="Linux.do OAuth2 Demo",
    description="使用 Linux.do OAuth2 认证的 FastAPI 应用",
    version="1.0.0",
)

# 用于存储 token 的简单内存存储（生产环境应使用数据库或 Redis）
token_storage = {}


@app.get("/", response_class=HTMLResponse)
async def home():
    """首页，显示登录链接"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Linux.do OAuth2 Demo</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 800px;
                margin: 50px auto;
                padding: 20px;
                background-color: #f5f5f5;
            }
            .container {
                background-color: white;
                padding: 30px;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            h1 {
                color: #333;
            }
            .btn {
                display: inline-block;
                padding: 12px 24px;
                background-color: #007bff;
                color: white;
                text-decoration: none;
                border-radius: 4px;
                margin-top: 20px;
            }
            .btn:hover {
                background-color: #0056b3;
            }
            .info {
                margin-top: 30px;
                padding: 15px;
                background-color: #e7f3ff;
                border-left: 4px solid #007bff;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚀 Linux.do OAuth2 登录演示</h1>
            <p>这是一个使用 FastAPI 和 Linux.do OAuth2 认证的示例应用。</p>
            <a href="/login" class="btn">使用 Linux.do 登录</a>
            
            <div class="info">
                <h3>可用端点：</h3>
                <ul>
                    <li><code>GET /</code> - 首页</li>
                    <li><code>GET /login</code> - 开始 OAuth2 登录流程</li>
                    <li><code>GET /oauth2/callback</code> - OAuth2 回调处理</li>
                    <li><code>GET /user</code> - 获取用户信息（需要 access_token）</li>
                    <li><code>POST /refresh</code> - 刷新 access token（需要 refresh_token）</li>
                    <li><code>GET /docs</code> - API 文档</li>
                </ul>
            </div>
        </div>
    </body>
    </html>
    """
    return html_content


@app.get("/login")
async def login():
    """开始 OAuth2 登录流程"""
    # 生成随机 state 用于防止 CSRF 攻击
    state = secrets.token_urlsafe(32)
    # 在生产环境中，应该将 state 存储在 session 或 Redis 中进行验证

    # 获取授权 URL
    auth_url = oauth2_service.get_authorization_url(state=state)

    # 重定向到 Linux.do 授权页面
    return RedirectResponse(url=auth_url)


@app.get("/oauth2/callback")
async def oauth2_callback(
    code: str = Query(..., description="授权码"),
    state: str = Query(..., description="状态参数"),
):
    """
    OAuth2 回调端点
    处理从 Linux.do 返回的授权码
    """
    if not code:
        raise HTTPException(status_code=400, detail="缺少授权码")

    try:
        # 使用授权码换取 token
        token_data = await oauth2_service.exchange_code_for_token(code)

        # 获取用户信息
        user_info = await oauth2_service.get_user_info(token_data["access_token"])

        # 存储 token（生产环境应使用更安全的方式）
        user_id = user_info["id"]
        token_storage[user_id] = token_data

        # 直接重定向到兑换码页面，通过 URL 参数传递 user_id
        return RedirectResponse(url=f"/redeem?user_id={user_id}")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"认证失败: {str(e)}")


@app.get("/user")
async def get_user_info(access_token: str = Query(..., description="访问令牌")):
    """
    获取用户信息

    使用示例：
    GET /user?access_token=YOUR_ACCESS_TOKEN
    """
    try:
        user_info = await oauth2_service.get_user_info(access_token)
        return {"success": True, "data": user_info}
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"获取用户信息失败: {str(e)}")


@app.post("/refresh")
async def refresh_token(refresh_token: str = Query(..., description="刷新令牌")):
    """
    刷新 access token

    使用示例：
    POST /refresh?refresh_token=YOUR_REFRESH_TOKEN
    """
    try:
        token_data = await oauth2_service.refresh_access_token(refresh_token)
        return {"success": True, "data": token_data}
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"刷新 token 失败: {str(e)}")


@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {"status": "healthy", "service": "Linux.do OAuth2 Demo"}


@app.post("/api/redeem/daily")
async def claim_daily_code(
    access_token: str = Query(..., description="访问令牌"),
    session: AsyncSession = Depends(get_session),
):
    """
    每日领取兑换码（队列模式）

    规则：
    - 每个用户每天只能领取一次
    - 兑换码通过队列异步创建，立即返回任务ID
    """
    try:
        # 获取用户信息
        user_info = await oauth2_service.get_user_info(access_token)
        user_id = user_info["id"]
        username = user_info["username"]

        # 检查今天是否已经领取过
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)

        existing_record = await session.execute(
            select(UserRedeemRecord)
            .where(UserRedeemRecord.user_id == user_id)
            .where(UserRedeemRecord.redeemed_at >= today_start)
            .where(UserRedeemRecord.redeemed_at < today_end)
        )

        if existing_record.scalar_one_or_none():
            raise HTTPException(
                status_code=400, detail="今天已经领取过兑换码了，请明天再来！"
            )

        # 检查 New API 配置
        if not settings.newapi_site_url or not settings.newapi_access_token:
            raise HTTPException(
                status_code=500,
                detail="系统配置错误：New API 未配置。请联系管理员配置 NEWAPI_SITE_URL 和 NEWAPI_ACCESS_TOKEN 环境变量。",
            )

        # 添加任务到队列
        task_id = await queue_manager.add_task(
            user_id=user_id,
            username=username,
            quota=settings.newapi_redeem_quota,
        )

        return {
            "success": True,
            "message": "兑换码生成任务已加入队列",
            "data": {
                "task_id": task_id,
                "status": "pending",
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"领取失败: {str(e)}")


@app.get("/api/task/{task_id}")
async def get_task_status(
    task_id: str,
    access_token: str = Query(..., description="访问令牌"),
    session: AsyncSession = Depends(get_session),
):
    """
    查询任务状态

    当任务完成后,会自动将兑换码保存到数据库
    """
    try:
        # 获取用户信息
        user_info = await oauth2_service.get_user_info(access_token)
        user_id = user_info["id"]

        # 获取任务信息
        task = await queue_manager.get_task(task_id)

        if not task:
            raise HTTPException(status_code=404, detail="任务不存在")

        # 验证任务所有权
        if task.user_id != user_id:
            raise HTTPException(status_code=403, detail="无权访问此任务")

        response_data = {
            "task_id": task.task_id,
            "status": task.status.value,
            "created_at": task.created_at.isoformat(),
        }

        if task.started_at:
            response_data["started_at"] = task.started_at.isoformat()

        if task.status == TaskStatus.COMPLETED:
            response_data["completed_at"] = task.completed_at.isoformat()
            response_data["code"] = task.result

            # 如果任务完成,保存到数据库
            existing = await session.execute(
                select(UserRedeemRecord)
                .where(UserRedeemRecord.user_id == user_id)
                .where(UserRedeemRecord.code == task.result)
            )

            if not existing.scalar_one_or_none():
                record = UserRedeemRecord(
                    user_id=user_id,
                    username=task.username,
                    redeem_code_id=None,
                    code=task.result,
                    source="newapi_queue",
                )
                session.add(record)
                await session.commit()

        elif task.status == TaskStatus.FAILED:
            response_data["completed_at"] = task.completed_at.isoformat()
            response_data["error"] = task.error

        return {
            "success": True,
            "data": response_data,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询任务失败: {str(e)}")


@app.get("/api/queue/info")
async def get_queue_info(
    access_token: str = Query(..., description="访问令牌"),
):
    """获取队列信息"""
    try:
        # 验证用户身份
        await oauth2_service.get_user_info(access_token)

        queue_info = queue_manager.get_queue_info()

        return {
            "success": True,
            "data": queue_info,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取队列信息失败: {str(e)}")


@app.get("/api/redeem/history")
async def get_redeem_history(
    access_token: str = Query(..., description="访问令牌"),
    session: AsyncSession = Depends(get_session),
):
    """获取用户的兑换历史记录"""
    try:
        # 获取用户信息
        user_info = await oauth2_service.get_user_info(access_token)
        user_id = user_info["id"]

        # 查询用户的兑换记录
        from sqlalchemy import desc
        from sqlmodel import col

        records = await session.execute(
            select(UserRedeemRecord)
            .where(UserRedeemRecord.user_id == user_id)
            .order_by(col(UserRedeemRecord.redeemed_at).desc())
        )

        history = []
        for record in records.scalars().all():
            history.append(
                {"code": record.code, "redeemed_at": record.redeemed_at.isoformat()}
            )

        return {"success": True, "data": {"total": len(history), "history": history}}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取历史记录失败: {str(e)}")


@app.get("/redeem", response_class=HTMLResponse)
async def redeem_page(user_id: int = Query(None, description="用户ID")):
    """兑换码领取页面"""

    # 如果有 user_id，从内存中获取 token
    access_token = ""
    user_info_data = {}
    if user_id and user_id in token_storage:
        access_token = token_storage[user_id].get("access_token", "")
        try:
            user_info_data = await oauth2_service.get_user_info(access_token)
        except:
            pass

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>每日兑换码</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                max-width: 800px;
                margin: 50px auto;
                padding: 20px;
                background-color: #f5f5f5;
            }}
            .container {{
                background-color: white;
                padding: 30px;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
            h1 {{
                color: #333;
            }}
            .btn {{
                display: inline-block;
                padding: 12px 24px;
                background-color: #28a745;
                color: white;
                text-decoration: none;
                border: none;
                border-radius: 4px;
                margin-top: 20px;
                cursor: pointer;
                font-size: 16px;
            }}
            .btn:hover {{
                background-color: #218838;
            }}
            .btn:disabled {{
                background-color: #6c757d;
                cursor: not-allowed;
            }}
            .result {{
                margin-top: 20px;
                padding: 15px;
                border-radius: 4px;
                display: none;
            }}
            .result.success {{
                background-color: #d4edda;
                border: 1px solid #c3e6cb;
                color: #155724;
            }}
            .result.error {{
                background-color: #f8d7da;
                border: 1px solid #f5c6cb;
                color: #721c24;
            }}
            .code-display {{
                font-size: 24px;
                font-weight: bold;
                margin: 15px 0;
                padding: 15px;
                background-color: #fff;
                border: 2px dashed #28a745;
                text-align: center;
                border-radius: 4px;
            }}
            .history {{
                margin-top: 30px;
            }}
            .history-item {{
                padding: 10px;
                margin: 5px 0;
                background-color: #f8f9fa;
                border-radius: 4px;
                display: flex;
                justify-content: space-between;
            }}
            .back-btn {{
                background-color: #007bff;
                margin-right: 10px;
            }}
            .back-btn:hover {{
                background-color: #0056b3;
            }}
            .user-info {{
                background-color: #e7f3ff;
                padding: 15px;
                border-radius: 4px;
                margin-bottom: 20px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎁 每日兑换码</h1>
            {
        f'''
            <div class="user-info">
                <p><strong>欢迎：</strong>{user_info_data.get("username", "未知用户")}</p>
                <p><strong>信任等级：</strong>{user_info_data.get("trust_level", "N/A")}</p>
            </div>
            '''
        if user_info_data
        else '<p>每天可以领取一个兑换码，<a href="/login">点击登录</a></p>'
    }
            
            <button class="btn" onclick="claimCode()" {
        "" if access_token else 'disabled title="请先登录"'
    }>领取今日兑换码</button>
            <button class="btn back-btn" onclick="location.href='/'">返回首页</button>
            
            <div class="result" id="result"></div>
            
            <div class="history" id="history" style="display:none;">
                <h2>📜 领取历史</h2>
                <div id="history-list"></div>
            </div>
        </div>
        
        <script>
            const accessToken = "{access_token}";
            
            async function claimCode() {{
                const resultDiv = document.getElementById('result');
                const btn = event.target;
                
                if (!accessToken) {{
                    showResult('error', '请先<a href="/login">登录</a>！');
                    return;
                }}
                
                btn.disabled = true;
                btn.textContent = '提交中...';
                
                try {{
                    const response = await fetch(`/api/redeem/daily?access_token=${{encodeURIComponent(accessToken)}}`, {{
                        method: 'POST'
                    }});
                    
                    const data = await response.json();
                    
                    if (data.success) {{
                        // 任务已提交到队列，开始轮询状态
                        const taskId = data.data.task_id;
                        showResult('success', `<p>⏳ 任务已提交，正在生成兑换码...</p>`);
                        btn.textContent = '生成中...';
                        
                        // 轮询任务状态
                        await pollTaskStatus(taskId, btn);
                    }} else {{
                        showResult('error', data.detail || '提交失败');
                        btn.disabled = false;
                        btn.textContent = '领取今日兑换码';
                    }}
                }} catch (error) {{
                    showResult('error', '网络错误，请重试');
                    btn.disabled = false;
                    btn.textContent = '领取今日兑换码';
                }}
            }}
            
            async function pollTaskStatus(taskId, btn) {{
                const maxAttempts = 60; // 最多轮询60次
                const interval = 1000; // 每秒轮询一次
                let attempts = 0;
                
                const poll = async () => {{
                    try {{
                        const response = await fetch(`/api/task/${{taskId}}?access_token=${{encodeURIComponent(accessToken)}}`);
                        const data = await response.json();
                        
                        if (data.success) {{
                            const status = data.data.status;
                            
                            if (status === 'completed') {{
                                // 任务完成
                                showResult('success', `
                                    <p>✅ 领取成功！</p>
                                    <div class="code-display">${{data.data.code}}</div>
                                    <p>完成时间：${{new Date(data.data.completed_at).toLocaleString('zh-CN')}}</p>
                                `);
                                btn.disabled = false;
                                btn.textContent = '领取今日兑换码';
                                loadHistory();
                                return;
                            }} else if (status === 'failed') {{
                                // 任务失败
                                showResult('error', `生成失败：${{data.data.error || '未知错误'}}`);
                                btn.disabled = false;
                                btn.textContent = '领取今日兑换码';
                                return;
                            }} else if (status === 'processing') {{
                                showResult('success', `<p>⚙️ 正在生成兑换码，请稍候...</p>`);
                            }}
                        }}
                        
                        // 继续轮询
                        attempts++;
                        if (attempts < maxAttempts) {{
                            setTimeout(poll, interval);
                        }} else {{
                            showResult('error', '任务超时，请稍后查看历史记录');
                            btn.disabled = false;
                            btn.textContent = '领取今日兑换码';
                        }}
                    }} catch (error) {{
                        console.error('轮询失败:', error);
                        attempts++;
                        if (attempts < maxAttempts) {{
                            setTimeout(poll, interval);
                        }} else {{
                            showResult('error', '网络错误，请稍后查看历史记录');
                            btn.disabled = false;
                            btn.textContent = '领取今日兑换码';
                        }}
                    }}
                }};
                
                // 开始轮询
                poll();
            }}
            
            async function loadHistory() {{
                if (!accessToken) return;
                
                try {{
                    const response = await fetch(`/api/redeem/history?access_token=${{encodeURIComponent(accessToken)}}`);
                    const data = await response.json();
                    
                    if (data.success && data.data.history.length > 0) {{
                        const historyDiv = document.getElementById('history');
                        const historyList = document.getElementById('history-list');
                        
                        historyList.innerHTML = data.data.history.map(item => `
                            <div class="history-item">
                                <span><strong>${{item.code}}</strong></span>
                                <span>${{new Date(item.redeemed_at).toLocaleString('zh-CN')}}</span>
                            </div>
                        `).join('');
                        
                        historyDiv.style.display = 'block';
                    }}
                }} catch (error) {{
                    console.error('加载历史记录失败:', error);
                }}
            }}
            
            function showResult(type, message) {{
                const resultDiv = document.getElementById('result');
                resultDiv.className = `result ${{type}}`;
                resultDiv.innerHTML = message;
                resultDiv.style.display = 'block';
            }}
            
            // 页面加载时自动加载历史记录
            window.onload = function() {{
                if (accessToken) {{
                    loadHistory();
                }}
            }};
        </script>
    </body>
    </html>
    """
    return html_content


@app.on_event("startup")
async def startup_event():
    """应用启动时创建数据库表并启动队列"""
    create_db_and_tables()
    await queue_manager.start_workers()


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时停止队列"""
    await queue_manager.stop_workers()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=settings.host, port=settings.port, log_level="info")

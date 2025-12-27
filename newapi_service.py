"""New API 服务模块 - 用于与 New API 交互创建兑换码"""

import httpx
from typing import Optional, Dict, Any


class NewAPIService:
    """New API 服务类"""

    def __init__(self, base_url: str, access_token: str):
        """
        初始化 New API 服务

        Args:
            base_url: New API 站点地址，例如 https://api.example.com
            access_token: New API 访问令牌
        """
        self.base_url = base_url.rstrip("/")
        self.access_token = access_token
        self.headers = {"Authorization": f"Bearer {access_token}"}

    async def create_redemption_code(
        self,
        quota: int = 500000,
        count: int = 1,
        name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        创建兑换码

        Args:
            quota: 额度（默认 500000 tokens）
            count: 创建数量（默认 1）
            name: 兑换码名称（可选）

        Returns:
            创建结果，包含兑换码列表

        Raises:
            Exception: 创建失败时抛出异常
        """
        url = f"{self.base_url}/api/redemption/"

        payload = {
            "quota": quota,
            "count": count,
        }

        if name:
            payload["name"] = name

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload, headers=self.headers)

            if response.status_code == 200:
                data = response.json()
                return data
            else:
                error_msg = f"创建兑换码失败: HTTP {response.status_code}"
                try:
                    error_data = response.json()
                    if "message" in error_data:
                        error_msg = f"{error_msg} - {error_data['message']}"
                    elif "detail" in error_data:
                        error_msg = f"{error_msg} - {error_data['detail']}"
                except:
                    pass
                raise Exception(error_msg)

    async def test_connection(self) -> bool:
        """
        测试与 New API 的连接

        Returns:
            连接是否成功
        """
        try:
            # 尝试调用一个简单的 API 端点来验证连接
            url = f"{self.base_url}/api/status"
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, headers=self.headers)
                return response.status_code in [200, 401, 403]  # 能连接上就算成功
        except:
            return False


# 全局服务实例（可选）
_newapi_service: Optional[NewAPIService] = None


def init_newapi_service(base_url: str, access_token: str) -> NewAPIService:
    """
    初始化全局 New API 服务实例

    Args:
        base_url: New API 站点地址
        access_token: New API 访问令牌

    Returns:
        New API 服务实例
    """
    global _newapi_service
    _newapi_service = NewAPIService(base_url, access_token)
    return _newapi_service


def get_newapi_service() -> Optional[NewAPIService]:
    """
    获取全局 New API 服务实例

    Returns:
        New API 服务实例，如果未初始化则返回 None
    """
    return _newapi_service

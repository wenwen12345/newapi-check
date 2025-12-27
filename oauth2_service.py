"""Linux.do OAuth2 服务模块"""

import base64
from typing import Optional
import httpx
from config import settings


class OAuth2Service:
    """处理 OAuth2 认证流程的服务类"""

    def __init__(self):
        self.client_id = settings.oauth2_client_id
        self.client_secret = settings.oauth2_client_secret
        self.redirect_uri = settings.oauth2_redirect_uri
        self.authorize_url = settings.oauth2_authorize_url
        self.token_url = settings.oauth2_token_url
        self.user_info_url = settings.oauth2_user_info_url

    def get_authorization_url(self, state: str = "random_state") -> str:
        """
        生成授权 URL

        Args:
            state: 状态参数，用于防止 CSRF 攻击

        Returns:
            授权 URL
        """
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "state": state,
        }

        query_string = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{self.authorize_url}?{query_string}"

    def _get_basic_auth_header(self) -> str:
        """
        生成 Basic 认证头

        Returns:
            Base64 编码的认证字符串
        """
        credentials = f"{self.client_id}:{self.client_secret}"
        encoded = base64.b64encode(credentials.encode()).decode()
        return f"Basic {encoded}"

    async def exchange_code_for_token(self, code: str) -> dict:
        """
        使用授权码换取 access token

        Args:
            code: 授权码

        Returns:
            包含 access_token, refresh_token 等信息的字典
        """
        headers = {
            "Authorization": self._get_basic_auth_header(),
            "Content-Type": "application/x-www-form-urlencoded",
        }

        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_uri,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.token_url,
                headers=headers,
                data=data,
            )
            response.raise_for_status()
            return response.json()

    async def refresh_access_token(self, refresh_token: str) -> dict:
        """
        使用 refresh token 刷新 access token

        Args:
            refresh_token: 刷新令牌

        Returns:
            包含新的 access_token 等信息的字典
        """
        headers = {
            "Authorization": self._get_basic_auth_header(),
            "Content-Type": "application/x-www-form-urlencoded",
        }

        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.token_url,
                headers=headers,
                data=data,
            )
            response.raise_for_status()
            return response.json()

    async def get_user_info(self, access_token: str) -> dict:
        """
        获取用户信息

        Args:
            access_token: 访问令牌

        Returns:
            用户信息字典
        """
        headers = {
            "Authorization": f"Bearer {access_token}",
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.user_info_url,
                headers=headers,
            )
            response.raise_for_status()
            return response.json()


# 创建全局服务实例
oauth2_service = OAuth2Service()

"""配置管理模块"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置"""

    # OAuth2 客户端配置
    oauth2_client_id: str
    oauth2_client_secret: str
    oauth2_redirect_uri: str = "http://localhost:8181/oauth2/callback"

    # 服务器配置
    host: str = "0.0.0.0"
    port: int = 8181

    # OAuth2 端点
    oauth2_authorize_url: str = "https://connect.linux.do/oauth2/authorize"
    oauth2_token_url: str = "https://connect.linux.do/oauth2/token"
    oauth2_user_info_url: str = "https://connect.linux.do/api/user"

    # 数据库配置
    database_url: str = "sqlite+aiosqlite:///./redeem_codes.db"
    debug: bool = False

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

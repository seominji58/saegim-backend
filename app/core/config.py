"""
애플리케이션 설정 관리
"""
from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache


class Settings(BaseSettings):
    """애플리케이션 설정"""
    
    # 기본 설정
    app_name: str = "새김 - 감성 AI 다이어리"
    debug: bool = False
    version: str = "1.0.0"
    environment: str = "development"
    
    # 서버 설정
    host: str = "0.0.0.0"
    port: int = 8000
    
    # 보안 설정
    secret_key: str = Field(..., description="Application secret key for general encryption")
    encryption_key: str = Field(..., description="Key for data encryption")
    allowed_hosts: List[str] = ["*"]
    allowed_origins: List[str] = ["http://localhost:3000"]
    cors_origins: str = '["http://localhost:3000"]'  # CORS 설정
    
    # JWT 설정
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60
    jwt_refresh_token_expire_days: int = 7
    jwt_secret: str = Field(..., description="Secret key for JWT token signing")
    jwt_expires_in: int = 3600
    
    # 데이터베이스 설정
    database_url: str = Field(..., description="Database connection URL")
    database_pool_size: int = 5
    database_max_overflow: int = 10
    database_pool_timeout: int = 30
    database_pool_recycle: int = 1800
    database_echo: bool = False
    database_ssl_mode: str = "prefer"
    
    # Redis 설정 (캐싱, Rate Limiting)
    redis_url: str = "redis://localhost:6379/0"
    rate_limit_requests: int = 60
    rate_limit_minutes: int = 1
    rate_limit_auth_per_min: int = 10
    
    # OAuth 설정
    google_client_id: str = ""
    google_client_secret: str = ""
    google_auth_uri: str = "https://accounts.google.com/o/oauth2/auth"
    google_token_uri: str = "https://oauth2.googleapis.com/token"
    google_certs_uri: str = "https://www.googleapis.com/oauth2/v1/certs"
    google_redirect_uri: str = "http://localhost:8000/auth/google/callback"
    
    # 쿠키 설정
    cookie_domain: str = "localhost"
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        
    @property
    def is_development(self) -> bool:
        return self.environment == "development"
    
    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache()
def get_settings() -> Settings:
    """설정 싱글톤 인스턴스 반환"""
    return Settings()
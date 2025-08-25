"""
애플리케이션 설정 관리
"""

from pydantic_settings import BaseSettings
from pydantic import field_validator
from functools import lru_cache
import secrets
import os
from typing import List, Union


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

    # 데이터베이스 설정
    database_url: str = os.getenv("DATABASE_URL", "")
    database_echo: bool = os.getenv("DATABASE_ECHO", "false").lower() == "true"
    database_pool_size: int = int(os.getenv("DATABASE_POOL_SIZE", "10"))
    database_max_overflow: int = int(os.getenv("DATABASE_MAX_OVERFLOW", "20"))
    database_pool_timeout: int = int(os.getenv("DATABASE_POOL_TIMEOUT", "30"))
    database_pool_recycle: int = int(os.getenv("DATABASE_POOL_RECYCLE", "3600"))
    database_ssl_mode: str = os.getenv("DATABASE_SSL_MODE", "prefer")

    # 보안 설정 (환경변수에서 가져오거나 기본값 사용)
    secret_key: str = os.getenv("SECRET_KEY", secrets.token_urlsafe(32))
    encryption_key: str = os.getenv("ENCRYPTION_KEY", secrets.token_urlsafe(32))

    # JWT 설정
    jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
    jwt_access_token_expire_minutes: int = int(
        os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "60")
    )
    jwt_refresh_token_expire_days: int = int(
        os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "7")
    )

    # MinIO 설정
    minio_endpoint: str = os.getenv("MINIO_ENDPOINT", "localhost:9000")
    minio_access_key: str = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    minio_secret_key: str = os.getenv("MINIO_SECRET_KEY", "minioadmin")
    minio_secure: bool = os.getenv("MINIO_SECURE", "false").lower() == "true"
    minio_bucket_name: str = os.getenv("MINIO_BUCKET_NAME", "saegim-images")

    # CORS 설정 (환경변수에서 쉼표로 구분된 문자열을 리스트로 변환)
    allowed_hosts: Union[List[str], str] = os.getenv(
        "ALLOWED_HOSTS", "http://localhost:3000,http://localhost:8080"
    )

    # FCM 설정
    fcm_project_id: str = os.getenv("FCM_PROJECT_ID", "")
    fcm_service_account_json: str = os.getenv("FCM_SERVICE_ACCOUNT_JSON", "")

    # Google OAuth 설정
    google_client_id: str = os.getenv("GOOGLE_CLIENT_ID", "")
    google_client_secret: str = os.getenv("GOOGLE_CLIENT_SECRET", "")
    google_redirect_uri: str = os.getenv(
        "GOOGLE_REDIRECT_URI", "http://localhost:8000/api/auth/google/callback"
    )
    google_auth_uri: str = os.getenv(
        "GOOGLE_AUTH_URI", "https://accounts.google.com/oauth2/auth"
    )
    google_token_uri: str = os.getenv(
        "GOOGLE_TOKEN_URI", "https://oauth2.googleapis.com/token"
    )
    google_userinfo_uri: str = os.getenv(
        "GOOGLE_USERINFO_URI", "https://www.googleapis.com/oauth2/v2/userinfo"
    )

    # 프론트엔드 URL 설정
    frontend_url: str = os.getenv(
        "FRONTEND_URL",
        "http://localhost:3000"
        if os.getenv("ENVIRONMENT", "development") == "development"
        else "https://saegim.seongjunlee.dev",
    )
    frontend_callback_url: str = os.getenv(
        "FRONTEND_CALLBACK_URL",
        "http://localhost:3000/auth/callback"
        if os.getenv("ENVIRONMENT", "development") == "development"
        else "https://saegim.seongjunlee.dev/auth/callback",
    )

    # 이메일 설정
    smtp_server: str = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port: int = int(os.getenv("SMTP_PORT", "587"))
    smtp_username: str = os.getenv("SMTP_USERNAME", "")
    smtp_password: str = os.getenv("SMTP_PASSWORD", "")
    from_email: str = os.getenv("FROM_EMAIL", "noreply@saegim.com")

    # SendGrid 설정
    sendgrid_api_key: str = os.getenv("SENDGRID_API_KEY", "")
    sendgrid_from_email: str = os.getenv(
        "SENDGRID_FROM_EMAIL", "alswlalalswl58@naver.com"
    )

    # 쿠키 설정
    cookie_domain: str = os.getenv("COOKIE_DOMAIN", "localhost")
    cookie_secure: bool = os.getenv("COOKIE_SECURE", "false").lower() == "true"
    cookie_samesite: str = os.getenv("COOKIE_SAMESITE", "lax")
    cookie_httponly: bool = os.getenv("COOKIE_HTTPONLY", "true").lower() == "true"

    @field_validator("allowed_hosts", mode="before")
    @classmethod
    def parse_allowed_hosts(cls, v):
        """ALLOWED_HOSTS 환경변수를 리스트로 파싱"""
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        return v

    def _parse_cors_origins(self, v: str) -> List[str]:
        """CORS origins 문자열을 리스트로 파싱 (deprecated: field_validator 사용)"""
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        return v

    @property
    def is_development(self) -> bool:
        """개발 환경인지 확인"""
        return self.environment.lower() == "development"

    @property
    def is_production(self) -> bool:
        """운영 환경인지 확인"""
        return self.environment.lower() == "production"

    @property
    def cors_origins(self) -> List[str]:
        """CORS origins 반환"""
        # allowed_hosts가 이미 field_validator로 처리되었으므로 그대로 반환
        if isinstance(self.allowed_hosts, list):
            return self.allowed_hosts
        # 혹시 모를 경우를 대비한 fallback
        return self._parse_cors_origins(self.allowed_hosts)

    model_config = {"env_file": ".env", "case_sensitive": False, "extra": "ignore"}


@lru_cache()
def get_settings() -> Settings:
    """설정 싱글톤 인스턴스 반환"""
    return Settings()


# 전역 settings 객체 생성
settings = get_settings()

"""애플리케이션 설정"""
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field
import os


class Settings(BaseSettings):
    """애플리케이션 설정"""
    
    # 기본 설정
    PROJECT_NAME: str = "새김 API"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")
    DEBUG: bool = Field(default=True, env="DEBUG")
    
    # 서버 설정
    HOST: str = Field(default="0.0.0.0", env="HOST")
    PORT: int = Field(default=8000, env="PORT")
    
    # 데이터베이스 설정
    DATABASE_URL: str = Field(
        default="postgresql://postgres:password@localhost:5432/saegim_dev",
        env="DATABASE_URL"
    )
    DATABASE_ECHO: bool = Field(default=False, env="DATABASE_ECHO")
    
    # Redis 설정
    REDIS_HOST: str = Field(default="localhost", env="REDIS_HOST")
    REDIS_PORT: int = Field(default=6379, env="REDIS_PORT")
    REDIS_PASSWORD: Optional[str] = Field(default=None, env="REDIS_PASSWORD")
    
    # JWT 설정
    SECRET_KEY: str = Field(
        default="your-secret-key-change-this-in-production",
        env="SECRET_KEY"
    )
    ACCESS_TOKEN_EXPIRE_HOURS: int = Field(default=24, env="ACCESS_TOKEN_EXPIRE_HOURS")
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=30, env="REFRESH_TOKEN_EXPIRE_DAYS")
    
    # 암호화 설정
    ENCRYPTION_KEY: str = Field(
        default="your-encryption-key-32-bytes-long",
        env="ENCRYPTION_KEY"
    )
    
    # CORS 설정
    ALLOWED_HOSTS: List[str] = Field(
        default=["http://localhost:3000", "http://127.0.0.1:3000"],
        env="ALLOWED_HOSTS"
    )
    
    # OpenAI 설정
    OPENAI_API_KEY: str = Field(default="", env="OPENAI_API_KEY")
    OPENAI_MODEL: str = Field(default="gpt-3.5-turbo", env="OPENAI_MODEL")
    
    # AI 사용 제한
    AI_DAILY_LIMIT: int = Field(default=20, env="AI_DAILY_LIMIT")
    AI_MONTHLY_LIMIT: int = Field(default=500, env="AI_MONTHLY_LIMIT")
    
    # 소셜 로그인 설정
    GOOGLE_CLIENT_ID: str = Field(default="", env="GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET: str = Field(default="", env="GOOGLE_CLIENT_SECRET")
    KAKAO_CLIENT_ID: str = Field(default="", env="KAKAO_CLIENT_ID")
    KAKAO_CLIENT_SECRET: str = Field(default="", env="KAKAO_CLIENT_SECRET")
    NAVER_CLIENT_ID: str = Field(default="", env="NAVER_CLIENT_ID")
    NAVER_CLIENT_SECRET: str = Field(default="", env="NAVER_CLIENT_SECRET")
    
    # 파일 업로드 설정
    MAX_FILE_SIZE: int = Field(default=15 * 1024 * 1024, env="MAX_FILE_SIZE")  # 15MB
    ALLOWED_IMAGE_TYPES: List[str] = Field(
        default=["image/jpeg", "image/png", "image/webp"],
        env="ALLOWED_IMAGE_TYPES"
    )
    
    # MinIO 설정 (이미지 저장소)
    MINIO_ENDPOINT: str = Field(default="localhost:9000", env="MINIO_ENDPOINT")
    MINIO_ACCESS_KEY: str = Field(default="minioadmin", env="MINIO_ACCESS_KEY")
    MINIO_SECRET_KEY: str = Field(default="minioadmin", env="MINIO_SECRET_KEY")
    MINIO_BUCKET: str = Field(default="saegim-images", env="MINIO_BUCKET")
    
    # 로깅 설정
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    LOG_FILE: str = Field(default="app.log", env="LOG_FILE")
    
    class Config:
        """설정 클래스"""
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


# 전역 설정 인스턴스
settings = Settings()
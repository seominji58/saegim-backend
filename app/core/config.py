"""
애플리케이션 설정 관리
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """애플리케이션 설정"""
    
    # 기본 설정
    app_name: str = "새김 - 감성 AI 다이어리"
    debug: bool = False
    version: str = "1.0.0"
    
    # 서버 설정
    host: str = "0.0.0.0"
    port: int = 8000
    
    # 데이터베이스 설정
    database_url: str = "postgresql://user:password@localhost:5432/saegim"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """설정 싱글톤 인스턴스 반환"""
    return Settings()
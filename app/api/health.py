"""
헬스체크 API 라우터
"""
from fastapi import APIRouter

router = APIRouter()


@router.get("/")
def health_check():
    """기본 헬스체크 엔드포인트"""
    return {"status": "ok", "message": "새김 백엔드가 정상적으로 실행 중입니다."}


@router.get("/health")
def detailed_health():
    """상세 헬스체크 엔드포인트"""
    return {
        "status": "healthy",
        "app_name": "새김 백엔드",
        "version": "1.0.0"
    }
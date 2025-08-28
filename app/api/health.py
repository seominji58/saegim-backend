"""
헬스체크 API 라우터
Docker 컨테이너 상태 확인 및 시스템 헬스체크
"""

import os
from datetime import datetime
from typing import Any

import psutil
from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter()

settings = get_settings()


@router.get("/")
def health_check() -> dict[str, str]:
    """기본 헬스체크 엔드포인트"""
    return {
        "status": "ok",
        "message": "새김 백엔드가 정상적으로 실행 중입니다.",
        "timestamp": datetime.now().isoformat(),
    }


@router.get("/health")
def detailed_health() -> dict[str, Any]:
    """상세 헬스체크 엔드포인트"""
    return {
        "status": "healthy",
        "app_name": "새김 백엔드",
        "version": "1.0.0",
        "environment": settings.environment,
        "timestamp": datetime.now().isoformat(),
        "uptime": _get_uptime(),
    }


def _get_uptime() -> str:
    """애플리케이션 업타임 계산"""
    try:
        # 프로세스 시작 시간 기반 업타임 계산
        process = psutil.Process(os.getpid())
        create_time = datetime.fromtimestamp(process.create_time())
        uptime = datetime.now() - create_time

        days = uptime.days
        hours, remainder = divmod(uptime.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        if days > 0:
            return f"{days}일 {hours}시간 {minutes}분"
        elif hours > 0:
            return f"{hours}시간 {minutes}분"
        else:
            return f"{minutes}분 {seconds}초"
    except Exception:
        return "알 수 없음"

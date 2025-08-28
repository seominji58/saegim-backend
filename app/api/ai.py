"""
AI 관련 API 라우터
AI 텍스트 생성 및 사용 로그 관리
"""

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.database import get_session
from app.models.user import User
from app.schemas.base import BaseResponse
from app.schemas.create_diary import CreateDiaryRequest
from app.services.ai_log import AIService
from app.services.create_diary import diary_service

router = APIRouter(prefix="/ai", tags=["AI"])


@router.post("/usage-log", response_model=BaseResponse[dict])
async def create_ai_usage_log(
    user_id: str,
    api_type: str,
    session_id: str,
    regeneration_count: int = 1,
    tokens_used: int = 0,
    request_data: Optional[Dict[str, Any]] = None,
    response_data: Optional[Dict[str, Any]] = None,
    db: Session = Depends(get_session),
) -> BaseResponse[dict]:
    """AI 사용 로그 생성"""
    service = diary_service(db)
    result = await service.create_ai_usage_log(
        user_id,
        api_type,
        session_id,
        regeneration_count,
        tokens_used,
        request_data,
        response_data,
    )
    return BaseResponse(data=result, message="AI 사용 로그가 생성되었습니다.")


@router.post("/generate", response_model=BaseResponse[dict])
async def generate_ai_text(
    data: CreateDiaryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
) -> BaseResponse[dict]:
    """AI 텍스트 생성"""
    ai_service = AIService(db)
    result = await ai_service.generate_ai_text(current_user.id, data)
    return BaseResponse(data=result, message="AI 텍스트가 생성되었습니다.")

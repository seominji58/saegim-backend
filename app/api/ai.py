"""
AI 관련 API 라우터
AI 텍스트 생성 및 사용 로그 관리
"""

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.deps import get_current_user_id
from app.db.database import get_session
from app.schemas.base import BaseResponse
from app.schemas.create_diary import CreateDiaryRequest
from app.services.ai_log import AIService
from app.services.create_diary import diary_service

router = APIRouter(
    prefix="/ai",
    tags=["AI"],
)


class AIUsageLogRequest(BaseModel):
    api_type: str
    session_id: str
    regeneration_count: int = 1
    tokens_used: int = 0
    request_data: dict[str, Any] | None = None
    response_data: dict[str, Any] | None = None


@router.post("/usage-log", response_model=BaseResponse[dict])
async def create_ai_usage_log(
    usage_log_data: AIUsageLogRequest,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    db: Annotated[Session, Depends(get_session)],
) -> BaseResponse[dict]:
    """AI 사용 로그 생성"""
    service = diary_service(db)
    result = await service.create_ai_usage_log(
        user_id,
        usage_log_data.api_type,
        usage_log_data.session_id,
        usage_log_data.regeneration_count,
        usage_log_data.tokens_used,
        usage_log_data.request_data,
        usage_log_data.response_data,
    )
    return BaseResponse(data=result, message="AI 사용 로그가 생성되었습니다.")


@router.post("/generate", response_model=BaseResponse[dict])
async def generate_ai_text(
    data: CreateDiaryRequest,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    db: Annotated[Session, Depends(get_session)],
) -> BaseResponse[dict]:
    """AI 텍스트 생성"""
    ai_service = AIService(db)
    result = await ai_service.generate_ai_text(user_id, data)
    return BaseResponse(data=result, message="AI 텍스트가 생성되었습니다.")


@router.post("/regenerate/{session_id}", response_model=BaseResponse[dict])
async def regenerate_ai_text(
    session_id: str,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    db: Annotated[Session, Depends(get_session)],
) -> BaseResponse[dict]:
    """세션 ID 기반 AI 텍스트 재생성"""
    ai_service = AIService(db)
    result = await ai_service.regenerate_by_session_id(user_id, session_id)
    return BaseResponse(data=result, message="AI 텍스트가 재생성되었습니다.")


@router.get("/session/{session_id}/original-input", response_model=BaseResponse[dict])
async def get_original_user_input(
    *,
    session_id: str = Path(..., description="세션 ID"),
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    db: Annotated[Session, Depends(get_session)],
) -> BaseResponse[dict]:
    """세션ID로 원본 사용자 입력 조회"""

    ai_service = AIService(db)
    original_input = await ai_service.get_original_user_input(user_id, session_id)

    if not original_input:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="해당 세션의 원본 입력을 찾을 수 없습니다.",
        )

    return BaseResponse(
        data={"original_input": original_input}, message="원본 사용자 입력 조회 성공"
    )


@router.post("/generate/stream")
async def stream_ai_text(
    data: CreateDiaryRequest,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    db: Annotated[Session, Depends(get_session)],
) -> StreamingResponse:
    """AI 텍스트 실시간 스트리밍 생성"""
    ai_service = AIService(db)

    async def generate_stream():
        try:
            async for chunk in ai_service.stream_ai_text(user_id, data):
                yield f"data: {chunk}\n\n"
        except Exception as e:
            error_message = (
                f'{{"error": "AI 텍스트 생성 중 오류가 발생했습니다: {str(e)}"}}'
            )
            yield f"data: {error_message}\n\n"
            yield "event: error\n"
            yield f"data: {error_message}\n\n"

    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control",
        },
    )


@router.post("/regenerate/{session_id}/stream")
async def stream_regenerate_ai_text(
    session_id: str,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    db: Annotated[Session, Depends(get_session)],
) -> StreamingResponse:
    """세션 ID 기반 AI 텍스트 실시간 스트리밍 재생성"""
    ai_service = AIService(db)

    async def regenerate_stream():
        try:
            async for chunk in ai_service.stream_regenerate_by_session_id(
                user_id, session_id
            ):
                yield f"data: {chunk}\n\n"
        except Exception as e:
            error_message = (
                f'{{"error": "AI 텍스트 재생성 중 오류가 발생했습니다: {str(e)}"}}'
            )
            yield f"data: {error_message}\n\n"
            yield "event: error\n"
            yield f"data: {error_message}\n\n"

    return StreamingResponse(
        regenerate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control",
        },
    )

"""
다이어리 API 라우터 (캘린더용)
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from sqlmodel import Session
from datetime import date
import uuid
from app.db.database import get_session
from app.schemas.diary import DiaryResponse, DiaryListResponse, DiaryUpdateRequest
from app.schemas.base import BaseResponse
from app.services.diary import DiaryService

router = APIRouter()


@router.get("", response_model=BaseResponse[List[DiaryListResponse]])
async def get_diaries(
    *,
    session: Session = Depends(get_session),
    page: int = Query(1, ge=1, description="페이지 번호"),
    page_size: int = Query(20, ge=1, le=100, description="페이지 크기"),
    searchTerm: Optional[str] = Query(None, description="제목/내용 통합 검색"),
    emotion: Optional[str] = Query(None, description="감정 필터"),
    is_public: Optional[bool] = Query(None, description="공개 여부"),
    start_date: Optional[date] = Query(None, description="시작 날짜 (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="종료 날짜 (YYYY-MM-DD)"),
    sort_order: str = Query(
        "desc",
        description="정렬 순서 (asc: 오름차순, desc: 내림차순)",
        regex="^(asc|desc)$",
    ),
) -> BaseResponse[List[DiaryListResponse]]:
    """다이어리 목록 조회 (페이지네이션 포함)"""

    diary_service = DiaryService(session)
    diaries, total_count = diary_service.get_diaries(
        page=page,
        page_size=page_size,
        searchTerm=searchTerm,
        emotion=emotion,
        is_public=is_public,
        start_date=start_date,
        end_date=end_date,
        sort_order=sort_order,
    )

    # 응답 데이터 변환
    diary_responses = [DiaryListResponse.from_orm(diary) for diary in diaries]

    return BaseResponse(
        data=diary_responses, message=f"다이어리 목록 조회 성공 (총 {total_count}개)"
    )


@router.get("/calendar/{user_id}", response_model=BaseResponse[List[DiaryListResponse]])
async def get_calendar_diaries(
    *,
    session: Session = Depends(get_session),
    user_id: str = Path(..., description="사용자 ID (UUID)"),
    start_date: date = Query(..., description="시작 날짜 (YYYY-MM-DD)"),
    end_date: date = Query(..., description="종료 날짜 (YYYY-MM-DD)"),
) -> BaseResponse[List[DiaryListResponse]]:
    """캘린더용 다이어리 조회 (특정 날짜 범위)"""

    # UUID 형식 검증
    try:
        uuid.UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="올바른 UUID 형식이 아닙니다",
        )

    diary_service = DiaryService(session)
    diaries = diary_service.get_diaries_by_date_range(
        user_id=user_id, start_date=start_date, end_date=end_date
    )

    # 응답 데이터 변환
    diary_responses = [DiaryListResponse.from_orm(diary) for diary in diaries]

    return BaseResponse(
        data=diary_responses,
        message=f"캘린더 다이어리 조회 성공 (총 {len(diary_responses)}개)",
    )


@router.get("/{diary_id}", response_model=BaseResponse[DiaryResponse])
async def get_diary(
    *,
    session: Session = Depends(get_session),
    diary_id: str = Path(..., description="다이어리 ID (UUID)"),
) -> BaseResponse[DiaryResponse]:
    """특정 다이어리 조회"""

    # UUID 형식 검증
    try:
        uuid.UUID(diary_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="올바른 UUID 형식이 아닙니다",
        )

    diary_service = DiaryService(session)
    diary = diary_service.get_diary_by_id(diary_id)

    if not diary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="다이어리를 찾을 수 없습니다"
        )

    return BaseResponse(
        data=DiaryResponse.from_orm(diary), message="다이어리 조회 성공"
    )


@router.put("/{diary_id}", response_model=BaseResponse[DiaryResponse])
async def update_diary(
    *,
    session: Session = Depends(get_session),
    diary_id: str = Path(..., description="다이어리 ID (UUID)"),
    diary_update: DiaryUpdateRequest,
) -> BaseResponse[DiaryResponse]:
    """다이어리 수정"""

    # UUID 형식 검증
    try:
        uuid.UUID(diary_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="올바른 UUID 형식이 아닙니다",
        )

    diary_service = DiaryService(session)
    updated_diary = diary_service.update_diary(diary_id, diary_update)

    if not updated_diary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="다이어리를 찾을 수 없습니다"
        )

    return BaseResponse(
        data=DiaryResponse.from_orm(updated_diary), message="다이어리 수정 성공"
    )

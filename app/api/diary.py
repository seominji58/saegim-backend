"""
다이어리 API 라우터 (JWT 인증 기반)
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from sqlmodel import Session
from datetime import date
import uuid
from app.db.database import get_session
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.diary import DiaryResponse, DiaryListResponse, DiaryCreateRequest, DiaryUpdateRequest
from app.schemas.base import BaseResponse
from app.services.diary import DiaryService

router = APIRouter()


@router.get("", response_model=BaseResponse[List[DiaryListResponse]])
async def get_my_diaries(
    *,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),  # JWT에서 사용자 정보 추출
    page: int = Query(1, ge=1, description="페이지 번호"),
    page_size: int = Query(20, ge=1, le=100, description="페이지 크기"),
    searchTerm: Optional[str] = Query(None, description="제목/내용 통합 검색"),
    emotion: Optional[str] = Query(None, description="감정 필터"),
    start_date: Optional[date] = Query(None, description="시작 날짜 (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="종료 날짜 (YYYY-MM-DD)"),
    sort_order: str = Query(
        "desc",
        description="정렬 순서 (asc: 오름차순, desc: 내림차순)",
        regex="^(asc|desc)$",
    ),
) -> BaseResponse[List[DiaryListResponse]]:
    """JWT 인증된 사용자의 다이어리 목록 조회 (페이지네이션 포함)"""

    diary_service = DiaryService(session)
    diaries, total_count = diary_service.get_diaries(
        user_id=current_user.id,  # JWT에서 추출한 사용자 ID 사용
        page=page,
        page_size=page_size,
        searchTerm=searchTerm,
        emotion=emotion,
        start_date=start_date,
        end_date=end_date,
        sort_order=sort_order,
    )

    # 응답 데이터 변환
    diary_responses = [DiaryListResponse.from_orm(diary) for diary in diaries]

    return BaseResponse(
        data=diary_responses,
        message=f"다이어리 목록 조회 성공 (총 {total_count}개)"
    )


@router.get("/calendar", response_model=BaseResponse[List[DiaryListResponse]])
async def get_calendar_diaries(
    *,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),  # JWT에서 사용자 정보 추출
    start_date: date = Query(..., description="시작 날짜 (YYYY-MM-DD)"),
    end_date: date = Query(..., description="종료 날짜 (YYYY-MM-DD)"),
) -> BaseResponse[List[DiaryListResponse]]:
    """JWT 인증된 사용자의 캘린더용 다이어리 조회 (특정 날짜 범위)"""

    diary_service = DiaryService(session)
    diaries = diary_service.get_diaries_by_date_range(
        user_id=current_user.id,  # JWT에서 추출한 사용자 ID 사용
        start_date=start_date,
        end_date=end_date
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
    current_user: User = Depends(get_current_user),  # JWT에서 사용자 정보 추출
    diary_id: str = Path(..., description="다이어리 ID (UUID)"),
) -> BaseResponse[DiaryResponse]:
    """JWT 인증된 사용자의 특정 다이어리 조회"""

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
            status_code=status.HTTP_404_NOT_FOUND,
            detail="다이어리를 찾을 수 없습니다"
        )

    # 본인의 다이어리만 조회 가능하도록 검증
    if diary.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="해당 다이어리에 접근할 권한이 없습니다"
        )

    return BaseResponse(
        data=DiaryResponse.from_orm(diary),
        message="다이어리 조회 성공"
    )


@router.post("", response_model=BaseResponse[DiaryResponse])
async def create_diary(
    *,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),  # JWT에서 사용자 정보 추출
    diary_create: DiaryCreateRequest,
) -> BaseResponse[DiaryResponse]:
    """JWT 인증된 사용자의 다이어리 생성"""

    diary_service = DiaryService(session)

    # diary_id 변수 제거하고 diary_create와 current_user.id만 전달
    created_diary = diary_service.create_diary(diary_create, current_user.id)

    return BaseResponse(
        data=DiaryResponse.from_orm(created_diary),
        message="다이어리 생성 성공"
    )


@router.put("/{diary_id}", response_model=BaseResponse[DiaryResponse])
async def update_diary(
    *,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),  # JWT에서 사용자 정보 추출
    diary_id: str = Path(..., description="다이어리 ID (UUID)"),
    diary_update: DiaryUpdateRequest,
) -> BaseResponse[DiaryResponse]:
    """JWT 인증된 사용자의 다이어리 수정"""

    # UUID 형식 검증
    try:
        uuid.UUID(diary_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="올바른 UUID 형식이 아닙니다",
        )

    diary_service = DiaryService(session)

    # 먼저 다이어리가 존재하고 본인의 것인지 확인
    existing_diary = diary_service.get_diary_by_id(diary_id)
    if not existing_diary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="다이어리를 찾을 수 없습니다"
        )

    # 본인의 다이어리만 수정 가능하도록 검증
    if existing_diary.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="해당 다이어리를 수정할 권한이 없습니다"
        )

    updated_diary = diary_service.update_diary(diary_id, diary_update)

    return BaseResponse(
        data=DiaryResponse.from_orm(updated_diary),
        message="다이어리 수정 성공"
    )


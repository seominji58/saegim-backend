"""
다이어리 API 라우터 (JWT 인증 기반)
"""

import logging
from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Path,
    Query,
    UploadFile,
    status,
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.constants import SortOrder
from app.core.deps import get_current_user_id
from app.db.database import get_session
from app.models.image import Image
from app.schemas.base import BaseResponse
from app.schemas.diary import (
    DiaryCreateRequest,
    DiaryListResponse,
    DiaryResponse,
    DiaryUpdateRequest,
)
from app.services.diary import DiaryService
from app.utils.error_handlers import ErrorPatterns, database_transaction_handler
from app.utils.minio_upload import (
    get_minio_uploader,
    upload_image_with_thumbnail_to_minio,
)
from app.utils.validators import (
    extract_minio_object_key,
    validate_image_file,
    validate_uuid,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("", response_model=BaseResponse[list[DiaryListResponse]])
async def get_my_diaries(
    *,
    session: Annotated[Session, Depends(get_session)],
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    page: Annotated[int, Query(ge=1, description="페이지 번호")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="페이지 크기")] = 20,
    searchTerm: Annotated[str | None, Query(description="제목/내용 통합 검색")] = None,
    emotion: Annotated[str | None, Query(description="감정 필터")] = None,
    start_date: Annotated[
        date | None, Query(description="시작 날짜 (YYYY-MM-DD)")
    ] = None,
    end_date: Annotated[
        date | None, Query(description="종료 날짜 (YYYY-MM-DD)")
    ] = None,
    sort_order: str = Query(
        SortOrder.DESC.value,
        description="정렬 순서 (asc: 오름차순, desc: 내림차순)",
        regex="^(asc|desc)$",
    ),
) -> BaseResponse[list[DiaryListResponse]]:
    """JWT 인증된 사용자의 다이어리 목록 조회 (페이지네이션 포함)"""

    diary_service = DiaryService(session)
    diaries, total_count = diary_service.get_diaries(
        user_id=user_id,  # JWT에서 추출한 사용자 ID 사용
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
        data=diary_responses, message=f"다이어리 목록 조회 성공 (총 {total_count}개)"
    )


@router.get("/calendar", response_model=BaseResponse[list[DiaryListResponse]])
async def get_calendar_diaries(
    *,
    session: Annotated[Session, Depends(get_session)],
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    start_date: Annotated[date, Query(description="시작 날짜 (YYYY-MM-DD)")],
    end_date: Annotated[date, Query(description="종료 날짜 (YYYY-MM-DD)")],
) -> BaseResponse[list[DiaryListResponse]]:
    """JWT 인증된 사용자의 캘린더용 다이어리 조회 (특정 날짜 범위)"""

    diary_service = DiaryService(session)
    diaries = diary_service.get_diaries_by_date_range(
        user_id=user_id,  # JWT에서 추출한 사용자 ID 사용
        start_date=start_date,
        end_date=end_date,
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
    session: Annotated[Session, Depends(get_session)],
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    diary_id: str = Path(..., description="다이어리 ID (UUID)"),
) -> BaseResponse[DiaryResponse]:
    """JWT 인증된 사용자의 특정 다이어리 조회"""

    # UUID 형식 검증
    validate_uuid(diary_id, "다이어리 ID")

    diary_service = DiaryService(session)
    diary = diary_service.get_diary_by_id(diary_id=diary_id, user_id=user_id)

    if not diary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="해당 다이어리를 찾을 수 없습니다.",
        )

    # 응답 데이터 변환
    diary_response = DiaryResponse.from_orm(diary)

    return BaseResponse(
        data=diary_response,
        message="다이어리 조회 성공",
    )


@router.post("/{diary_id}/upload-image", response_model=BaseResponse[dict])
async def upload_diary_image(
    *,
    session: Annotated[Session, Depends(get_session)],
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    diary_id: str = Path(..., description="다이어리 ID (UUID)"),
    image: Annotated[UploadFile, File(description="업로드할 이미지 파일")],
) -> BaseResponse[dict]:
    """다이어리에 이미지 업로드"""

    # UUID 형식 검증
    validate_uuid(diary_id, "다이어리 ID")

    # 다이어리 존재 여부 및 권한 확인
    diary_service = DiaryService(session)
    diary = diary_service.get_diary_by_id(diary_id=diary_id, user_id=user_id)

    if not diary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="해당 다이어리를 찾을 수 없습니다.",
        )

    # 이미지 파일 검증
    validate_image_file(image.content_type, image.size)

    with database_transaction_handler(
        session,
        ErrorPatterns.IMAGE_UPLOAD_FAILED,
        log_context=f"이미지 업로드 - diary_id: {diary_id}",
    ):
        # MinIO에 이미지와 썸네일 업로드
        _, original_url, thumbnail_url = await upload_image_with_thumbnail_to_minio(
            image
        )

        # 데이터베이스에 이미지 정보 저장
        new_image = Image(
            diary_id=diary_id,
            file_path=original_url,
            thumbnail_path=thumbnail_url,
            mime_type=image.content_type,
            file_size=image.size,
            exif_removed=True,
        )

        session.add(new_image)
        session.commit()
        session.refresh(new_image)

        return BaseResponse(
            data={
                "id": str(new_image.id),
                "file_path": new_image.file_path,
                "thumbnail_path": new_image.thumbnail_path,
                "mime_type": new_image.mime_type,
                "file_size": new_image.file_size,
            },
            message="이미지 업로드 성공",
        )


@router.delete("/{diary_id}/images/{image_id}")
async def delete_diary_image(
    *,
    session: Annotated[Session, Depends(get_session)],
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    diary_id: str = Path(..., description="다이어리 ID (UUID)"),
    image_id: str = Path(..., description="이미지 ID (UUID)"),
) -> BaseResponse[dict]:
    """다이어리 이미지 삭제"""

    # UUID 형식 검증
    validate_uuid(diary_id, "다이어리 ID")
    validate_uuid(image_id, "이미지 ID")

    # 다이어리 존재 여부 및 권한 확인
    diary_service = DiaryService(session)
    diary = diary_service.get_diary_by_id(diary_id=diary_id, user_id=user_id)

    if not diary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="해당 다이어리를 찾을 수 없습니다.",
        )

    # 이미지 존재 여부 및 권한 확인
    stmt = select(Image).where(Image.id == image_id, Image.diary_id == diary_id)
    result = session.execute(stmt)
    image = result.scalar_one_or_none()

    if not image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="해당 이미지를 찾을 수 없습니다.",
        )

    with database_transaction_handler(
        session,
        ErrorPatterns.IMAGE_DELETE_FAILED,
        log_context=f"이미지 삭제 - diary_id: {diary_id}, image_id: {image_id}",
    ):
        # MinIO에서 실제 파일 삭제
        uploader = get_minio_uploader()

        # 원본 이미지 삭제
        if image.file_path:
            original_object_key = extract_minio_object_key(image.file_path)
            if original_object_key:
                uploader.delete_image(original_object_key)

        # 썸네일 삭제
        if image.thumbnail_path:
            thumbnail_object_key = extract_minio_object_key(image.thumbnail_path)
            if thumbnail_object_key:
                uploader.delete_image(thumbnail_object_key)

        # 데이터베이스에서 이미지 정보 삭제
        session.delete(image)
        session.commit()

        return BaseResponse(
            data={"message": "이미지 삭제 성공"},
            message="이미지가 성공적으로 삭제되었습니다.",
        )


@router.get("/{diary_id}/images", response_model=BaseResponse[list[dict]])
async def get_diary_images(
    *,
    session: Annotated[Session, Depends(get_session)],
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    diary_id: str = Path(..., description="다이어리 ID (UUID)"),
) -> BaseResponse[list[dict]]:
    """다이어리의 기존 이미지들 조회"""

    # UUID 형식 검증
    validate_uuid(diary_id, "다이어리 ID")

    # 다이어리 존재 여부 및 권한 확인
    diary_service = DiaryService(session)
    diary = diary_service.get_diary_by_id(diary_id=diary_id, user_id=user_id)

    if not diary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="해당 다이어리를 찾을 수 없습니다.",
        )

    # 해당 다이어리의 이미지들 조회
    stmt = select(Image).where(Image.diary_id == diary_id)
    result = session.execute(stmt)
    images = result.scalars().all()

    # 이미지 정보 반환
    image_list = []
    for img in images:
        image_list.append(
            {
                "id": str(img.id),
                "file_path": img.file_path,
                "thumbnail_path": img.thumbnail_path,
                "mime_type": img.mime_type,
                "file_size": img.file_size,
                "created_at": img.created_at.isoformat() if img.created_at else None,
            }
        )

    return BaseResponse(
        data=image_list, message=f"다이어리 이미지 조회 성공 (총 {len(image_list)}개)"
    )


@router.post("/images/upload", response_model=BaseResponse[list[dict]])
async def upload_temporary_images(
    *,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    images: Annotated[list[UploadFile], File(description="업로드할 이미지 파일들")],
) -> BaseResponse[list[dict]]:
    """AI 글 생성용 임시 이미지 업로드 (다이어리 저장 시 연결됨)"""

    if len(images) > 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="최대 3개의 이미지만 업로드할 수 있습니다.",
        )

    uploaded_images = []

    for image in images:
        try:
            # 이미지 파일 검증
            validate_image_file(image.content_type, image.size or 0)

            # MinIO에 이미지 업로드 (썸네일 포함)
            (
                file_id,
                original_url,
                thumbnail_url,
            ) = await upload_image_with_thumbnail_to_minio(image)

            # 업로드된 이미지 정보 저장
            image_info = {
                "file_id": file_id,
                "original_url": original_url,
                "thumbnail_url": thumbnail_url,
                "mime_type": image.content_type,
                "file_size": image.size,
                "filename": image.filename,
            }
            uploaded_images.append(image_info)

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"이미지 업로드 실패: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"이미지 업로드 중 오류가 발생했습니다: {str(e)}",
            ) from e

    return BaseResponse(
        data=uploaded_images,
        message=f"이미지 업로드 성공 (총 {len(uploaded_images)}개)",
    )


@router.post("", response_model=BaseResponse[DiaryResponse])
async def create_diary(
    *,
    session: Annotated[Session, Depends(get_session)],
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    diary_create: DiaryCreateRequest,
) -> BaseResponse[DiaryResponse]:
    """JWT 인증된 사용자의 다이어리 생성"""

    diary_service = DiaryService(session)

    # diary_id 변수 제거하고 diary_create와 user_id만 전달
    created_diary = diary_service.create_diary(diary_create, user_id)

    return BaseResponse(
        data=DiaryResponse.from_orm(created_diary), message="다이어리 생성 성공"
    )


@router.put("/{diary_id}", response_model=BaseResponse[DiaryResponse])
async def update_diary(
    *,
    session: Annotated[Session, Depends(get_session)],
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    diary_id: str = Path(..., description="다이어리 ID (UUID)"),
    diary_update: DiaryUpdateRequest,
) -> BaseResponse[DiaryResponse]:
    """JWT 인증된 사용자의 다이어리 수정"""

    # UUID 형식 검증
    validate_uuid(diary_id, "다이어리 ID")

    diary_service = DiaryService(session)

    # 다이어리 존재 여부 및 권한을 한 번에 확인 (보안 강화)
    existing_diary = diary_service.get_diary_by_id(diary_id, user_id)
    if not existing_diary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="다이어리를 찾을 수 없거나 접근 권한이 없습니다",
        )

    # 권한 검증은 이미 get_diary_by_id에서 완료됨

    updated_diary = diary_service.update_diary(diary_id, diary_update)

    return BaseResponse(
        data=DiaryResponse.from_orm(updated_diary), message="다이어리 수정 성공"
    )


@router.delete("/{diary_id}", response_model=BaseResponse[dict])
async def delete_diary(
    *,
    session: Annotated[Session, Depends(get_session)],
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    diary_id: str = Path(..., description="다이어리 ID (UUID)"),
) -> BaseResponse[dict]:
    """JWT 인증된 사용자의 다이어리 삭제 (Soft Delete)"""

    # UUID 형식 검증
    validate_uuid(diary_id, "다이어리 ID")

    diary_service = DiaryService(session)

    # 다이어리 삭제 시도
    success = diary_service.delete_diary(diary_id=diary_id, user_id=user_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="해당 다이어리를 찾을 수 없습니다.",
        )

    return BaseResponse(
        data={"message": "다이어리 삭제 성공"},
        message="다이어리가 성공적으로 삭제되었습니다.",
    )

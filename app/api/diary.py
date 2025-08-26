"""
다이어리 API 라우터 (JWT 인증 기반)
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query, Path, UploadFile, File
from sqlmodel import Session, select
from datetime import date
import uuid
from app.db.database import get_session
from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.diary import DiaryResponse, DiaryListResponse, DiaryCreateRequest, DiaryUpdateRequest
from app.schemas.base import BaseResponse
from app.services.diary import DiaryService
from app.utils.minio_upload import upload_image_with_thumbnail_to_minio, get_minio_uploader
from app.models.image import Image

router = APIRouter()


def _extract_object_key_from_url(url: str) -> str:
    """MinIO URL에서 객체 키 추출"""
    try:
        # URL에서 버킷 이름 이후의 경로를 객체 키로 추출
        # 예: http://localhost:9000/saegim-images/images/2023/12/01/uuid.jpg -> images/2023/12/01/uuid.jpg
        parts = url.split('/')
        bucket_index = -1
        for i, part in enumerate(parts):
            if 'saegim-images' in part or part == 'saegim-images':
                bucket_index = i
                break
        
        if bucket_index != -1 and bucket_index + 1 < len(parts):
            return '/'.join(parts[bucket_index + 1:])
        
        return ""
    except Exception:
        return ""


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
            detail="잘못된 다이어리 ID 형식입니다.",
        )

    diary_service = DiaryService(session)
    diary = diary_service.get_diary_by_id(
        diary_id=diary_id, user_id=current_user.id
    )

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
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    diary_id: str = Path(..., description="다이어리 ID (UUID)"),
    image: UploadFile = File(..., description="업로드할 이미지 파일"),
) -> BaseResponse[dict]:
    """다이어리에 이미지 업로드"""

    # UUID 형식 검증
    try:
        uuid.UUID(diary_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="잘못된 다이어리 ID 형식입니다.",
        )

    # 다이어리 존재 여부 및 권한 확인
    diary_service = DiaryService(session)
    diary = diary_service.get_diary_by_id(
        diary_id=diary_id, user_id=current_user.id
    )

    if not diary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="해당 다이어리를 찾을 수 없습니다.",
        )

    # 이미지 파일 검증
    if not image.content_type.startswith('image/'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미지 파일만 업로드할 수 있습니다.",
        )

    if image.size > 10 * 1024 * 1024:  # 10MB 제한
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="파일 크기는 10MB 이하여야 합니다.",
        )

    try:
        # MinIO에 이미지와 썸네일 업로드  
        _, original_url, thumbnail_url = await upload_image_with_thumbnail_to_minio(image)

        # 데이터베이스에 이미지 정보 저장
        new_image = Image(
            diary_id=diary_id,
            file_path=original_url,
            thumbnail_path=thumbnail_url,
            mime_type=image.content_type,
            file_size=image.size,
            exif_removed=True
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
                "file_size": new_image.file_size
            },
            message="이미지 업로드 성공"
        )

    except Exception as e:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"이미지 업로드 실패: {str(e)}"
        )


@router.delete("/{diary_id}/images/{image_id}")
async def delete_diary_image(
    *,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    diary_id: str = Path(..., description="다이어리 ID (UUID)"),
    image_id: str = Path(..., description="이미지 ID (UUID)"),
) -> BaseResponse[dict]:
    """다이어리 이미지 삭제"""

    # UUID 형식 검증
    try:
        uuid.UUID(diary_id)
        uuid.UUID(image_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="잘못된 ID 형식입니다.",
        )

    # 다이어리 존재 여부 및 권한 확인
    diary_service = DiaryService(session)
    diary = diary_service.get_diary_by_id(
        diary_id=diary_id, user_id=current_user.id
    )

    if not diary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="해당 다이어리를 찾을 수 없습니다.",
        )

    # 이미지 존재 여부 및 권한 확인
    image = session.exec(
        select(Image).where(
            Image.id == image_id,
            Image.diary_id == diary_id
        )
    ).first()

    if not image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="해당 이미지를 찾을 수 없습니다.",
        )

    try:
        # MinIO에서 실제 파일 삭제
        uploader = get_minio_uploader()
        
        # 원본 이미지 삭제
        if image.file_path:
            original_object_key = _extract_object_key_from_url(image.file_path)
            if original_object_key:
                uploader.delete_image(original_object_key)
        
        # 썸네일 삭제
        if image.thumbnail_path:
            thumbnail_object_key = _extract_object_key_from_url(image.thumbnail_path)
            if thumbnail_object_key:
                uploader.delete_image(thumbnail_object_key)

        # 데이터베이스에서 이미지 정보 삭제
        session.delete(image)
        session.commit()

        return BaseResponse(
            data={"message": "이미지 삭제 성공"},
            message="이미지가 성공적으로 삭제되었습니다."
        )

    except Exception as e:
        session.rollback()
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"이미지 삭제 실패 - diary_id: {diary_id}, image_id: {image_id}, error: {str(e)}")
        logger.exception("상세 오류 정보:")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"이미지 삭제 실패: {str(e)}"
        )


@router.get("/{diary_id}/images", response_model=BaseResponse[List[dict]])
async def get_diary_images(
    *,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    diary_id: str = Path(..., description="다이어리 ID (UUID)"),
) -> BaseResponse[List[dict]]:
    """다이어리의 기존 이미지들 조회"""

    # UUID 형식 검증
    try:
        uuid.UUID(diary_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="잘못된 다이어리 ID 형식입니다.",
        )

    # 다이어리 존재 여부 및 권한 확인
    diary_service = DiaryService(session)
    diary = diary_service.get_diary_by_id(
        diary_id=diary_id, user_id=current_user.id
    )

    if not diary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="해당 다이어리를 찾을 수 없습니다.",
        )

    # 해당 다이어리의 이미지들 조회
    images = session.exec(
        select(Image).where(Image.diary_id == diary_id)
    ).all()

    # 이미지 정보 반환
    image_list = []
    for img in images:
        image_list.append({
            "id": str(img.id),
            "file_path": img.file_path,
            "thumbnail_path": img.thumbnail_path,
            "mime_type": img.mime_type,
            "file_size": img.file_size,
            "created_at": img.created_at.isoformat() if img.created_at else None
        })

    return BaseResponse(
        data=image_list,
        message=f"다이어리 이미지 조회 성공 (총 {len(image_list)}개)"
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




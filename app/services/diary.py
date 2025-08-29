"""
다이어리 비즈니스 로직 서비스 (캘린더용)
"""

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.constants import SortOrder
from app.models.diary import DiaryEntry
from app.schemas.diary import DiaryCreateRequest, DiaryUpdateRequest
from app.services.base import SyncBaseService
from app.utils.error_handlers import ErrorPatterns, database_transaction_handler
from app.utils.validators import extract_minio_object_key


class DiaryService(SyncBaseService):
    """다이어리 비즈니스 로직 (캘린더용)"""

    def __init__(self, session: Session):
        super().__init__(session)
        self.session = session  # 기존 코드 호환성을 위해 유지

    def get_diaries(
        self,
        user_id: UUID | None = None,
        page: int = 1,
        page_size: int = 20,
        searchTerm: str | None = None,
        emotion: str | None = None,
        is_public: bool | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        sort_order: str = SortOrder.DESC.value,
    ) -> tuple[list[DiaryEntry], int]:
        """다이어리 목록 조회 (페이지네이션 포함)"""

        # 기본 쿼리 구성
        statement = select(DiaryEntry)

        # 사용자별 필터링 (Soft Delete 제외)
        if user_id is not None:
            statement = statement.where(
                DiaryEntry.user_id == user_id, DiaryEntry.deleted_at.is_(None)
            )

        # 통합 검색 (제목 또는 내용)
        if searchTerm:
            statement = statement.where(
                (DiaryEntry.title.ilike(f"%{searchTerm}%"))
                | (DiaryEntry.content.ilike(f"%{searchTerm}%"))
            )

        # 감정별 필터링
        if emotion:
            statement = statement.where(DiaryEntry.user_emotion == emotion)

        # 공개 여부 필터링
        if is_public is not None:
            statement = statement.where(DiaryEntry.is_public == is_public)

        # 날짜 범위 필터링
        if start_date:
            statement = statement.where(func.date(DiaryEntry.created_at) >= start_date)
        if end_date:
            statement = statement.where(func.date(DiaryEntry.created_at) <= end_date)

        # # 정렬 (최신순) old
        # statement = statement.order_by(DiaryEntry.created_at.desc())
        # 정렬 적용
        if sort_order.lower() == SortOrder.DESC.value:
            statement = statement.order_by(DiaryEntry.created_at.desc())
        else:
            statement = statement.order_by(DiaryEntry.created_at.asc())

        # 전체 개수 조회 (user_id 필터 적용, Soft Delete 제외)
        count_statement = select(func.count(DiaryEntry.id))
        if user_id is not None:
            count_statement = count_statement.where(
                DiaryEntry.user_id == user_id, DiaryEntry.deleted_at.is_(None)
            )

        result = self.session.execute(count_statement)
        total_count = result.scalar_one()

        # 페이지네이션 적용
        offset = (page - 1) * page_size
        statement = statement.offset(offset).limit(page_size)

        # 결과 조회
        result = self.session.execute(statement)
        diaries = result.scalars().all()

        return diaries, total_count

    def get_diary_by_id(
        self, diary_id: str, user_id: UUID | None = None
    ) -> DiaryEntry | None:
        """ID로 다이어리 조회 (Soft Delete 제외)"""
        statement = select(DiaryEntry).where(
            DiaryEntry.id == diary_id, DiaryEntry.deleted_at.is_(None)
        )

        if user_id is not None:
            statement = statement.where(DiaryEntry.user_id == user_id)

        result = self.session.execute(statement)
        return result.scalar_one_or_none()

    def get_diaries_by_date_range(
        self, user_id: UUID, start_date: date, end_date: date
    ) -> list[DiaryEntry]:
        """특정 날짜 범위의 다이어리 조회 (캘린더용) - 이미지 정보 포함"""
        # 이미지 관계를 함께 로드하기 위해 selectinload 사용
        from sqlalchemy.orm import selectinload

        statement = (
            select(DiaryEntry)
            .options(selectinload(DiaryEntry.images))
            .where(
                DiaryEntry.user_id == user_id,
                DiaryEntry.deleted_at.is_(None),
                func.date(DiaryEntry.created_at) >= start_date,
                func.date(DiaryEntry.created_at) <= end_date,
            )
            .order_by(DiaryEntry.created_at.desc())
        )

        result = self.session.execute(statement)
        return result.scalars().all()

    def create_diary(
        self, diary_create: DiaryCreateRequest, user_id: UUID
    ) -> DiaryEntry:
        """새로운 다이어리 생성"""

        # 새 다이어리 엔트리 생성 (실제 AI 데이터 사용)
        new_diary = DiaryEntry(
            user_id=user_id,
            title=diary_create.title,
            content=diary_create.content,
            user_emotion=diary_create.user_emotion,
            ai_emotion=diary_create.ai_emotion,
            ai_emotion_confidence=diary_create.ai_emotion_confidence,
            ai_generated_text=diary_create.ai_generated_text,
            is_public=diary_create.is_public,
            keywords=diary_create.keywords,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        # 데이터베이스에 저장
        self.session.add(new_diary)
        self.session.commit()
        self.session.refresh(new_diary)

        return new_diary

    def update_diary(
        self, diary_id: str, diary_update: DiaryUpdateRequest
    ) -> DiaryEntry | None:
        """다이어리 수정"""
        diary = self.get_diary_by_id(diary_id)

        if not diary:
            return None

        # 업데이트할 필드들만 수정
        update_data = diary_update.dict(exclude_unset=True)

        for field, value in update_data.items():
            if hasattr(diary, field):
                # keywords 필드는 JSONB 타입이므로 리스트 그대로 저장
                setattr(diary, field, value)

        # updated_at 필드 자동 업데이트
        diary.updated_at = datetime.utcnow()

        # 데이터베이스에 저장
        self.session.add(diary)
        self.session.commit()
        self.session.refresh(diary)

        return diary

    def delete_diary(self, diary_id: str, user_id: UUID) -> bool:
        """다이어리 삭제 (Soft Delete) - 관련 이미지들도 MinIO에서 삭제"""
        diary = self.get_diary_by_id(diary_id, user_id)

        if not diary:
            return False

        with database_transaction_handler(
            self.session,
            ErrorPatterns.DIARY_DELETE_FAILED,
            log_context=f"다이어리 삭제 - diary_id: {diary_id}",
        ):
            # 다이어리와 관련된 이미지들 조회
            from app.models.image import Image
            from app.utils.minio_upload import get_minio_uploader

            stmt = select(Image).where(Image.diary_id == diary_id)
            result = self.session.execute(stmt)
            images = result.scalars().all()

            # MinIO에서 이미지 파일들 삭제
            if images:
                uploader = get_minio_uploader()

                for image in images:
                    # 원본 이미지 삭제
                    if image.file_path:
                        original_key = extract_minio_object_key(image.file_path)
                        if original_key:
                            uploader.delete_image(original_key)

                    # 썸네일 삭제
                    if image.thumbnail_path:
                        thumbnail_key = extract_minio_object_key(image.thumbnail_path)
                        if thumbnail_key:
                            uploader.delete_image(thumbnail_key)

                # 데이터베이스에서 이미지 레코드들 삭제
                for image in images:
                    self.session.delete(image)

            # Soft Delete: deleted_at 필드를 현재 시간으로 설정
            diary.deleted_at = datetime.utcnow()

            # 데이터베이스에 저장
            self.session.add(diary)
            self.session.commit()

            return True

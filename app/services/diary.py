"""
다이어리 비즈니스 로직 서비스 (캘린더용)
"""

from typing import List, Optional, Tuple
from sqlmodel import Session, select, func
from datetime import datetime, date
import random
import json
from app.models.diary import DiaryEntry
from app.schemas.diary import DiaryCreateRequest, DiaryUpdateRequest


class DiaryService:
    """다이어리 비즈니스 로직 (캘린더용)"""

    def __init__(self, session: Session):
        self.session = session

    def get_diaries(
        self,
        user_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
        searchTerm: Optional[str] = None,
        emotion: Optional[str] = None,
        is_public: Optional[bool] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        sort_order: str = "desc"
    ) -> Tuple[List[DiaryEntry], int]:
        """다이어리 목록 조회 (페이지네이션 포함)"""

        # 기본 쿼리 구성
        statement = select(DiaryEntry)

        # 사용자별 필터링 (Soft Delete 제외)
        if user_id is not None:
            statement = statement.where(
                DiaryEntry.user_id == user_id,
                DiaryEntry.deleted_at.is_(None)
            )

        # 통합 검색 (제목 또는 내용)
        if searchTerm:
            statement = statement.where(
            (DiaryEntry.title.ilike(f"%{searchTerm}%")) |
            (DiaryEntry.content.ilike(f"%{searchTerm}%"))
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
        if sort_order.lower() == "desc":
            statement = statement.order_by(DiaryEntry.created_at.desc())
        else:
            statement = statement.order_by(DiaryEntry.created_at.asc())

        # 전체 개수 조회 (user_id 필터 적용, Soft Delete 제외)
        count_statement = select(func.count(DiaryEntry.id))
        if user_id is not None:
            count_statement = count_statement.where(
                DiaryEntry.user_id == user_id,
                DiaryEntry.deleted_at.is_(None)
            )

        total_count = self.session.exec(count_statement).one()

        # 페이지네이션 적용
        offset = (page - 1) * page_size
        statement = statement.offset(offset).limit(page_size)

        # 결과 조회
        diaries = self.session.exec(statement).all()

        return diaries, total_count

    def get_diary_by_id(self, diary_id: str, user_id: Optional[str] = None) -> Optional[DiaryEntry]:
        """ID로 다이어리 조회 (Soft Delete 제외)"""
        statement = select(DiaryEntry).where(
            DiaryEntry.id == diary_id,
            DiaryEntry.deleted_at.is_(None)
        )

        if user_id is not None:
            statement = statement.where(DiaryEntry.user_id == user_id)

        return self.session.exec(statement).first()

    def get_diaries_by_date_range(
        self,
        user_id: str,
        start_date: date,
        end_date: date
    ) -> List[DiaryEntry]:
        """특정 날짜 범위의 다이어리 조회 (캘린더용) - 이미지 정보 포함"""
        # 이미지 관계를 함께 로드하기 위해 selectinload 사용
        from sqlmodel import select, func
        from sqlalchemy.orm import selectinload
        
        statement = select(DiaryEntry).options(
            selectinload(DiaryEntry.images)
        ).where(
            DiaryEntry.user_id == user_id,
            DiaryEntry.deleted_at.is_(None),
            func.date(DiaryEntry.created_at) >= start_date,
            func.date(DiaryEntry.created_at) <= end_date
        ).order_by(DiaryEntry.created_at.desc())

        return self.session.exec(statement).all()

    def create_diary(self, diary_create: DiaryCreateRequest, user_id: str) -> DiaryEntry:
        """새로운 다이어리 생성"""

        # 임시 AI 다이어리 생성 결과 생성
        emotions = ["happy", "sad", "angry", "peaceful", "unrest"]
        ai_emotion = random.choice(emotions)
        ai_emotion_confidence = round(random.uniform(0.1, 0.9), 2)
        ai_generated_text = f"AI가 생성한 {ai_emotion}한 감정의 텍스트입니다."

        mock_keywords = ["일기"] if not diary_create.content or len(diary_create.content.strip()) < 2 else [diary_create.content.strip()[:2]]
        # keywords를 JSON 문자열로 변환
        keywords_json = json.dumps(mock_keywords, ensure_ascii=False)

        # 새 다이어리 엔트리 생성
        new_diary = DiaryEntry(
            user_id=user_id,
            title=diary_create.title,
            content=diary_create.content,
            user_emotion=diary_create.user_emotion,
            ai_emotion=ai_emotion, 
            ai_emotion_confidence=ai_emotion_confidence, 
            ai_generated_text=ai_generated_text,
            is_public=diary_create.is_public,
            keywords=keywords_json,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        # 데이터베이스에 저장
        self.session.add(new_diary)
        self.session.commit()
        self.session.refresh(new_diary)

        return new_diary

    def update_diary(self, diary_id: str, diary_update: DiaryUpdateRequest) -> Optional[DiaryEntry]:
        """다이어리 수정"""
        diary = self.get_diary_by_id(diary_id)

        if not diary:
            return None

        # 업데이트할 필드들만 수정
        update_data = diary_update.dict(exclude_unset=True)

        for field, value in update_data.items():
            if hasattr(diary, field):
                # keywords 필드는 JSON 문자열로 변환
                if field == 'keywords' and isinstance(value, list):
                    import json
                    setattr(diary, field, json.dumps(value) if value else None)
                else:
                    setattr(diary, field, value)

        # updated_at 필드 자동 업데이트
        diary.updated_at = datetime.utcnow()

        # 데이터베이스에 저장
        self.session.add(diary)
        self.session.commit()
        self.session.refresh(diary)

        return diary

"""
다이어리 비즈니스 로직 서비스 (캘린더용)
"""

from typing import List, Optional, Tuple
from sqlmodel import Session, select, func
from datetime import datetime, date
from app.models.diary import DiaryEntry


class DiaryService:
    """다이어리 비즈니스 로직 (캘린더용)"""

    def __init__(self, session: Session):
        self.session = session

    def get_diaries(
        self,
        user_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
        emotion: Optional[str] = None,
        is_public: Optional[bool] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Tuple[List[DiaryEntry], int]:
        """다이어리 목록 조회 (페이지네이션 포함)"""

        # 기본 쿼리 구성
        statement = select(DiaryEntry)

        # 사용자별 필터링
        if user_id is not None:
            statement = statement.where(DiaryEntry.user_id == user_id)

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

        # 정렬 (최신순)
        statement = statement.order_by(DiaryEntry.created_at.desc())

        # 전체 개수 조회
        total_count = self.session.exec(
            select(func.count(DiaryEntry.id))
        ).one()

        # 페이지네이션 적용
        offset = (page - 1) * page_size
        statement = statement.offset(offset).limit(page_size)

        # 결과 조회
        diaries = self.session.exec(statement).all()

        return diaries, total_count

    def get_diary_by_id(self, diary_id: str, user_id: Optional[str] = None) -> Optional[DiaryEntry]:
        """ID로 다이어리 조회"""
        statement = select(DiaryEntry).where(
            DiaryEntry.id == diary_id
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
        """특정 날짜 범위의 다이어리 조회 (캘린더용)"""
        statement = select(DiaryEntry).where(
            DiaryEntry.user_id == user_id,
            func.date(DiaryEntry.created_at) >= start_date,
            func.date(DiaryEntry.created_at) <= end_date
        ).order_by(DiaryEntry.created_at.desc())

        return self.session.exec(statement).all()

"""
데이터베이스 초기화 및 샘플 데이터 생성
"""

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.database import create_db_and_tables, engine
from app.models.diary import DiaryEntry
from app.models.image import Image
from app.models.user import User


def init_db():
    """데이터베이스 초기화"""
    create_db_and_tables()

    with Session(engine) as session:
        # 샘플 사용자 생성
        user = create_sample_user(session)

        # 샘플 다이어리 생성
        diaries = create_sample_diaries(session, user.id)

        # 샘플 이미지 생성
        create_sample_images(session, diaries)

        print("데이터베이스 초기화 완료!")


def create_sample_user(session: Session) -> User:
    """샘플 사용자 생성"""
    # 기존 사용자 확인
    stmt = select(User).where(User.email == "test@example.com")
    result = session.execute(stmt)
    existing_user = result.scalar_one_or_none()

    if existing_user:
        return existing_user

    user = User(email="test@example.com", name="테스트 사용자", provider="local")

    session.add(user)
    session.commit()
    session.refresh(user)

    print(f"샘플 사용자 생성: {user.name} ({user.email})")
    return user


def create_sample_diaries(session: Session, user_id: int):
    """샘플 다이어리 생성"""
    # 기존 다이어리 확인
    stmt = select(DiaryEntry).where(DiaryEntry.user_id == user_id)
    result = session.execute(stmt)
    existing_diaries = result.scalars().all()

    if existing_diaries:
        print(f"기존 다이어리 {len(existing_diaries)}개 발견")
        return existing_diaries

    # 샘플 다이어리 데이터
    sample_diaries = [
        {
            "title": "오늘의 기쁨",
            "content": "친구들과 함께한 점심 시간이 정말 즐거웠다. 오랜만에 만난 친구들과 수다를 떨며 웃고 떠들었다. 이런 순간들이 인생의 진짜 보물인 것 같다.",
            "user_emotion": "happy",
            "is_public": True,
            "keywords": json.dumps(["친구", "점심", "웃음", "즐거움"], ensure_ascii=False),
        },
        {
            "title": "차분한 하루",
            "content": "오늘은 조용한 하루였다. 책을 읽고 차를 마시며 마음의 여유를 가졌다. 가끔은 이런 평온한 시간도 필요하다.",
            "user_emotion": "peaceful",
            "is_public": False,
            "keywords": json.dumps(["책", "차", "평온", "여유"], ensure_ascii=False),
        },
        {
            "title": "작은 걱정",
            "content": "내일 있을 회의가 걱정된다. 준비를 충분히 했지만 항상 긴장된다. 그래도 최선을 다해보자.",
            "user_emotion": "worried",
            "is_public": False,
            "keywords": json.dumps(["회의", "준비", "긴장", "최선"], ensure_ascii=False),
        },
        {
            "title": "감사한 순간",
            "content": "가족들이 건강하고 행복하게 지내고 있다는 것이 가장 큰 감사다. 매일매일이 축복이다.",
            "user_emotion": "happy",
            "is_public": True,
            "keywords": json.dumps(["가족", "건강", "행복", "감사", "축복"], ensure_ascii=False),
        },
        {
            "title": "새로운 도전",
            "content": "새로운 프로젝트를 시작하게 되었다. 두렵지만도 하지만 설렘도 있다. 이번 기회에 더 많이 배우고 성장하고 싶다.",
            "user_emotion": "excited",
            "is_public": True,
            "keywords": json.dumps(["프로젝트", "도전", "성장", "학습"], ensure_ascii=False),
        },
    ]

    # 다이어리 생성
    created_diaries = []
    for diary_data in sample_diaries:
        diary = DiaryEntry(user_id=user_id, **diary_data)
        session.add(diary)
        created_diaries.append(diary)

    session.commit()

    # 생성된 다이어리들을 새로고침하여 ID 가져오기
    for diary in created_diaries:
        session.refresh(diary)

    print(f"샘플 다이어리 {len(created_diaries)}개 생성")
    return created_diaries


def create_sample_images(session: Session, diaries: list):
    """샘플 이미지 생성"""
    # 기존 이미지 확인
    stmt = select(Image)
    result = session.execute(stmt)
    existing_images = result.scalars().all()

    if existing_images:
        print(f"기존 이미지 {len(existing_images)}개 발견")
        return

    # 첫 번째 다이어리에 이미지 추가
    if diaries:
        first_diary = diaries[0]

        # 샘플 이미지 데이터 (MinIO URL 사용)
        sample_image = Image(
            diary_id=first_diary.id,
            file_path="https://storage.seongjunlee.dev/saegim/images/sample/happy1.jpg",
            thumbnail_path="https://storage.seongjunlee.dev/saegim/thumbnails/sample/happy1_thumb.jpg",
            mime_type="image/jpeg",
            file_size=1024000,
            exif_removed=True,
        )

        session.add(sample_image)
        session.commit()
        session.refresh(sample_image)

        print(f"샘플 이미지 생성: {sample_image.thumbnail_path}")


if __name__ == "__main__":
    init_db()

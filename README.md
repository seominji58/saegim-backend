# 새김(Saegim) - 감성 AI 다이어리 백엔드

새김은 감정을 기록하고 AI와 함께 성장하는 다이어리 서비스입니다.

## 🚀 주요 기능

-   **다이어리 조회**: 캘린더용 다이어리 목록 및 상세 조회
-   **감정 분석**: 사용자 감정 기록 및 AI 감정 분석
-   **캘린더 연동**: 프론트엔드 캘린더와 연동되는 API
-   **RESTful API**: 표준화된 API 응답 구조

## 🛠️ 기술 스택

-   **Framework**: FastAPI 0.104+
-   **Database**: PostgreSQL 14+ (SQLModel + SQLAlchemy)
-   **Language**: Python 3.11+
-   **Authentication**: JWT (준비 중)
-   **Documentation**: OpenAPI/Swagger

## 📋 요구사항

-   Python 3.11+
-   PostgreSQL 14+
-   pip 또는 poetry

## 🚀 빠른 시작

### 1. 의존성 설치

```bash
pip install -r requirements.txt
```

### 2. 환경 설정

PostgreSQL 데이터베이스 연결 정보가 이미 `app/core/config.py`에 설정되어 있습니다:

```python
database_url: str = "postgresql://saegim_admin:saegim_pass1234!@seongjunlee.dev:55432/saegim_dev"
```

### 3. 데이터베이스 초기화

```bash
python -m app.db.init_db
```

이 명령어는 다음을 수행합니다:

-   데이터베이스 테이블 생성
-   샘플 사용자 생성
-   샘플 다이어리 데이터 생성

### 4. 서버 실행

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 5. API 문서 확인

브라우저에서 다음 URL을 열어 API 문서를 확인할 수 있습니다:

-   Swagger UI: http://localhost:8000/docs
-   ReDoc: http://localhost:8000/redoc

## 📚 API 엔드포인트

### 다이어리 API (`/api/diary`)

| Method | Endpoint              | Description                                    |
| ------ | --------------------- | ---------------------------------------------- |
| GET    | `/`                   | 다이어리 목록 조회 (페이지네이션, 필터링 지원) |
| GET    | `/{diary_id}`         | 특정 다이어리 조회                             |
| GET    | `/calendar/{user_id}` | 캘린더용 다이어리 조회 (날짜 범위)             |

### 쿼리 파라미터

#### 다이어리 목록 조회

-   `page`: 페이지 번호 (기본값: 1)
-   `page_size`: 페이지 크기 (기본값: 20, 최대: 100)
-   `emotion`: 감정 필터 (예: happy, sad, peaceful, worried, excited)
-   `is_public`: 공개 여부 필터 (true/false)
-   `start_date`: 시작 날짜 (YYYY-MM-DD)
-   `end_date`: 종료 날짜 (YYYY-MM-DD)

#### 캘린더용 다이어리 조회

-   `start_date`: 시작 날짜 (YYYY-MM-DD) - 필수
-   `end_date`: 종료 날짜 (YYYY-MM-DD) - 필수

### 응답 형식

모든 API는 표준화된 응답 형식을 사용합니다:

```json
{
  "success": true,
  "data": {...},
  "message": "작업 성공 메시지",
  "timestamp": "2024-01-01T00:00:00",
  "request_id": "uuid-string"
}
```

## 🧪 테스트

### API 테스트

```bash
python test_diary_api.py
```

이 스크립트는 다음을 테스트합니다:

-   다이어리 목록 조회
-   특정 다이어리 조회
-   캘린더용 다이어리 조회

### 단위 테스트

```bash
pytest tests/
```

## 📁 프로젝트 구조

```
app/
├── api/                    # API 라우터
│   ├── diary.py          # 다이어리 API (캘린더용)
│   └── health.py         # 헬스체크 API
├── core/                  # 핵심 설정
│   ├── config.py         # 환경 설정
│   └── security.py       # 보안 관련 (준비 중)
├── db/                    # 데이터베이스
│   ├── database.py       # DB 연결 설정
│   └── init_db.py        # DB 초기화
├── models/                # 데이터베이스 모델
│   ├── base.py           # 기본 모델
│   ├── user.py           # 사용자 모델
│   └── diary.py          # 다이어리 모델
├── schemas/               # API 스키마
│   ├── base.py           # 기본 응답 스키마
│   └── diary.py          # 다이어리 스키마 (캘린더용)
├── services/              # 비즈니스 로직
│   └── diary.py          # 다이어리 서비스 (캘린더용)
└── main.py               # FastAPI 애플리케이션
```

## 🔒 보안 기능

-   **입력 검증**: HTML 태그 및 악성 콘텐츠 차단
-   **SQL 인젝션 방지**: SQLModel ORM 사용
-   **데이터 검증**: Pydantic 스키마를 통한 엄격한 검증
-   **소프트 삭제**: 데이터 완전 삭제 대신 삭제 표시

## 🚧 향후 계획

-   [ ] JWT 인증 시스템 구현
-   [ ] 사용자 권한 관리
-   [ ] AI 감정 분석 연동
-   [ ] 이미지 업로드 기능
-   [ ] 푸시 알림 시스템
-   [ ] 다이어리 백업/복원

## 🤝 기여하기

1. 이 저장소를 포크합니다
2. 기능 브랜치를 생성합니다 (`git checkout -b feature/amazing-feature`)
3. 변경사항을 커밋합니다 (`git commit -m 'Add amazing feature'`)
4. 브랜치에 푸시합니다 (`git push origin feature/amazing-feature`)
5. Pull Request를 생성합니다

## 📄 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다.

## 📞 지원

문제가 있거나 질문이 있으시면 이슈를 생성해주세요.

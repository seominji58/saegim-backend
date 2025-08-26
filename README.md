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

프로젝트 루트에 `.env` 파일을 생성하고 다음 환경변수들을 설정하세요:

```bash
# 데이터베이스 설정
DATABASE_URL=postgresql://username:password@localhost:5432/database_name

# 보안 설정
SECRET_KEY=your-secret-key-here
ENCRYPTION_KEY=your-encryption-key-here

# MinIO 설정
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET_NAME=saegim-images

# 기타 설정
ALLOWED_HOSTS=http://localhost:3000,http://localhost:8080

# 이메일 설정 (SendGrid - 추천)
SENDGRID_API_KEY=your-sendgrid-api-key-here
SENDGRID_FROM_EMAIL=your-verified-email@yourdomain.com
FROM_EMAIL=noreply@yourdomain.com

# 테스트 설정
TEST_EMAIL=test@example.com

# 이메일 설정 (Gmail SMTP - 대안)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

### 3. 데이터베이스 초기화

```bash
python -m app.db.init_db
```

이 명령어는 다음을 수행합니다:

-   데이터베이스 테이블 생성
-   샘플 사용자 생성
-   샘플 다이어리 데이터 생성

### 4. 한글 인코딩 설정 (Windows 환경)

Windows 환경에서 한글 로그와 응답이 깨지는 문제를 해결하기 위해 다음 방법 중 하나를 사용하세요:

#### 방법 1: 배치 파일 사용 (추천)
```bash
# Windows에서 실행
run_server.bat
```

#### 방법 2: Python 스크립트 사용
```bash
python run_server.py
```

#### 방법 3: 직접 환경 변수 설정 후 실행
```bash
# Windows CMD에서
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
set PYTHONLEGACYWINDOWSSTDIO=utf-8
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### 방법 4: PowerShell에서 실행
```powershell
$env:PYTHONIOENCODING="utf-8"
$env:PYTHONUTF8="1"
$env:PYTHONLEGACYWINDOWSSTDIO="utf-8"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 5. 이메일 서비스 설정 (선택사항)

#### SendGrid 설정 (추천 - 무료)

1. [SendGrid](https://sendgrid.com) 계정 생성
2. 무료 플랜 선택 (월 100통 이메일)
3. API 키 생성: Settings → API Keys → Create API Key
4. 발신자 이메일 인증: Settings → Sender Authentication
5. 환경변수 설정:
   ```bash
   SENDGRID_API_KEY=your-api-key-here
   FROM_EMAIL=your-verified-email@yourdomain.com
   ```

#### Gmail SMTP 설정 (대안)

1. Gmail 계정에서 2단계 인증 활성화
2. 앱 비밀번호 생성: Google 계정 → 보안 → 앱 비밀번호
3. 환경변수 설정:
   ```bash
   SMTP_SERVER=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USERNAME=your-email@gmail.com
   SMTP_PASSWORD=your-app-password
   FROM_EMAIL=your-email@gmail.com
   ```

**참고**: 이메일 설정이 없어도 회원가입 기능은 정상 작동하지만, 이메일 인증과 환영 이메일이 발송되지 않습니다.

### 6. 서버 실행

#### Windows 환경 (한글 인코딩 지원)
```bash
# 방법 1: 배치 파일 사용 (추천)
run_server.bat

# 방법 2: Python 스크립트 사용
python run_server.py

# 방법 3: 직접 실행
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### Linux/Mac 환경
```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 7. API 문서 확인

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

# 새김(Saegim) 백엔드

새김 감성 AI 다이어리 서비스의 백엔드 API 서버입니다.

## 🚀 기술 스택

- **Framework**: FastAPI
- **Database**: PostgreSQL + SQLModel
- **Cache**: Redis
- **Storage**: MinIO (이미지 업로드)
- **Push Notification**: Firebase Cloud Messaging
- **Security**: JWT + AES-256-GCM 암호화

## 📁 프로젝트 구조

```
app/
├── api/          # API 라우터
├── core/         # 설정 및 보안
├── db/           # 데이터베이스 설정
├── models/       # 데이터 모델
├── schemas/      # Pydantic 스키마
├── services/     # 비즈니스 로직
└── utils/        # 유틸리티 (암호화, 파일 업로드, FCM)
```

## 🛠️ 설치 및 실행

### 1. 의존성 설치

```bash
pip install -r requirements.txt
```

### 2. 환경 설정

```bash
# 환경설정 파일 생성
cp .env.example .env

# 필수 환경변수 설정
SECRET_KEY=your_jwt_secret_key
ENCRYPTION_KEY=your_encryption_key
DATABASE_URL=postgresql://user:pass@localhost:5432/saegim
```

### 3. 서버 실행

```bash
# 개발 서버 실행
uvicorn app.main:app --reload

# API 문서 확인
open http://localhost:8000/docs
```

## 🧪 테스트

```bash
# 모든 테스트 실행
python -m pytest

# 커버리지 포함 테스트
python -m pytest --cov=app
```

## 📚 문서

자세한 설정 및 사용법은 다음 문서를 참고하세요:

- [보안 기능 가이드](docs/SECURITY.md) - 암호화, JWT, 보안 설정
- [배포 가이드](docs/DEPLOYMENT.md) - 환경 설정, MinIO, FCM 설정
- [기능 사용법](docs/FEATURES.md) - API 기능별 상세 사용법
- [테스트 가이드](docs/TESTING.md) - 테스트 실행 및 커버리지

## 🔗 관련 링크

- [API 문서](http://localhost:8000/docs) (서버 실행 후)
- [프론트엔드](https://github.com/aicc6/saegim-frontend) - Next.js 프론트엔드

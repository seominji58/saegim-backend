# 새김 백엔드

새김(Saegim) 감성 AI 다이어리 백엔드 서비스

## 🔐 보안 기능

### 암호화 지원

- **비밀번호 해싱**: bcrypt (cost factor: 12)
- **민감 데이터 암호화**: AES-256-GCM
- **JWT 인증**: HS256 알고리즘

### 사용법

#### 비밀번호 해싱

```python
from app.utils.encryption import hash_password, verify_password

# 비밀번호 해싱
hashed = hash_password("my_password")

# 비밀번호 검증
is_valid = verify_password("my_password", hashed)
```

#### 데이터 암호화

```python
from app.utils.encryption import encrypt_data, decrypt_data

# 데이터 암호화
encrypted = encrypt_data("민감한 정보")

# 데이터 복호화
decrypted = decrypt_data(encrypted)
```

#### JWT 토큰

```python
from app.core.security import create_access_token, decode_access_token

# 토큰 생성
token = create_access_token({"sub": "user_id"})

# 토큰 디코딩
payload = decode_access_token(token)
```

### 설치 및 실행

#### 1. 환경설정

```bash
# 환경설정 파일 생성
cp .env.example .env

# .env 파일 편집 (필수!)
# SECRET_KEY와 ENCRYPTION_KEY를 반드시 변경하세요
vim .env
```

#### 2. 보안 키 생성

*OpenSSL 사용 (권장):*

```bash
# JWT 시크릿 키 생성
echo "SECRET_KEY=$(openssl rand -base64 32)"

# 데이터 암호화 키 생성
echo "ENCRYPTION_KEY=$(openssl rand -base64 32)"
```

#### 3. 의존성 설치 및 실행

```bash
# 의존성 설치
pip install -r requirements.txt

# 데모 실행 (암호화 기능 테스트)
python examples/encryption_demo.py

# 서버 실행
uvicorn app.main:app --reload
```

### 🔧 환경변수 설정

주요 환경변수들:

| 변수명 | 설명 | 예시값 |
|--------|------|--------|
| `SECRET_KEY` | JWT 시크릿 키 (필수) | `your_jwt_secret_key` |
| `ENCRYPTION_KEY` | 데이터 암호화 키 (필수) | `your_encryption_key` |
| `DATABASE_URL` | PostgreSQL 연결 URL | `postgresql://user:pass@localhost:5432/saegim` |
| `ALLOWED_HOSTS` | CORS 허용 도메인 | `http://localhost:3000,http://localhost:8080` |
| `ENVIRONMENT` | 실행 환경 | `development`, `production` |

**⚠️ 보안 주의사항:**

- `SECRET_KEY`와 `ENCRYPTION_KEY`는 반드시 강력한 랜덤 값으로 설정
- `.env` 파일은 Git에 커밋하지 말 것
- 운영환경에서는 모든 기본값을 변경할 것

### 🧪 테스트

#### 테스트 실행

```bash
# 모든 테스트 실행 (깔끔한 출력)
python -m pytest

# 암호화 모듈 테스트만 실행
python -m pytest tests/test_encryption.py -v

# 커버리지 포함 테스트
python -m pytest --cov=app --cov-report=html
```

#### 테스트 커버리지

- **암호화 모듈**: 94% 커버리지
- **총 45개 테스트 케이스** (비밀번호 해싱, 데이터 암호화, 엣지 케이스 등)
- 성능 테스트 및 보안 테스트 포함
- **Deprecated 경고 완전 제거**: `bcrypt` 직접 사용으로 전환

#### 테스트 종류

- **단위 테스트**: 개별 함수 및 클래스 테스트
- **통합 테스트**: 모듈 간 상호작용 테스트
- **보안 테스트**: 암호화 및 해싱 보안성 검증
- **성능 테스트**: 암호화 성능 및 비밀번호 해싱 시간 측정
- **엣지 케이스**: 빈 문자열, 특수문자, 긴 데이터 등

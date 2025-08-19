# 테스트 가이드

새김 백엔드의 테스트 실행, 커버리지 분석 및 품질 보증에 대한 가이드입니다.

## 🧪 테스트 개요

### 테스트 구조

```
tests/
├── __init__.py
├── test_encryption.py        # 암호화 기능 테스트
├── test_fcm_push.py          # FCM 푸시 알림 테스트
├── test_minio_upload.py      # MinIO 파일 업로드 테스트
├── test_minio_integration.py # MinIO 통합 테스트
└── test_*.py                 # 기타 테스트 모듈
```

### 테스트 통계

- **총 86개 테스트 케이스**
- **암호화 모듈**: 94% 커버리지
- **테스트 유형**: 단위/통합/보안/성능 테스트
- **플랫폼**: Windows/Linux/macOS 호환

## 🚀 빠른 테스트 실행

### 기본 테스트

```bash
# 모든 테스트 실행 (커버리지 경고만)
python -m pytest

# 빠른 테스트 (커버리지 없음)
python -m pytest --no-cov

# 상세 출력
python -m pytest -v
```

### 커버리지 포함 테스트

```bash
# 기본 커버리지 (경고만)
python -m pytest --cov=app

# 엄격한 커버리지 (80% 미만 시 실패)
python -m pytest --cov-fail-under=80

# HTML 커버리지 리포트 생성
python -m pytest --cov=app --cov-report=html
```

## 📊 테스트 종류별 실행

### 1. 모듈별 테스트

```bash
# 암호화 기능 테스트
python -m pytest tests/test_encryption.py -v

# MinIO 파일 업로드 테스트
python -m pytest tests/test_minio_upload.py -v

# FCM 푸시 알림 테스트
python -m pytest tests/test_fcm_push.py -v

# MinIO 통합 테스트
python -m pytest tests/test_minio_integration.py -v
```

### 2. 마커별 테스트

```bash
# 통합 테스트만 실행
python -m pytest -m integration

# 단위 테스트만 실행
python -m pytest -m unit

# 빠른 테스트만 실행 (느린 테스트 제외)
python -m pytest -m "not slow"

# 보안 테스트만 실행
python -m pytest -m security
```

### 3. 특정 조건별 테스트

```bash
# MinIO 관련 테스트만 실행
python -m pytest tests/test_minio_upload.py tests/test_minio_integration.py --no-cov

# 특정 함수만 테스트
python -m pytest tests/test_encryption.py::test_password_hashing -v

# 특정 클래스만 테스트
python -m pytest tests/test_minio_upload.py::TestMinIOUpload -v
```

## 📈 커버리지 분석

### 커버리지 설정

#### pytest.ini 설정

```ini
[tool:pytest]
addopts = --cov=app --cov-report=term-missing
testpaths = tests
markers =
    unit: Unit tests
    integration: Integration tests
    slow: Slow running tests
    security: Security tests
```

#### .coveragerc 설정

```ini
[run]
source = app
omit =
    */venv/*
    */tests/*
    */migrations/*
    */alembic/*

[report]
exclude_lines =
    pragma: no cover
    def __repr__
    raise AssertionError
    raise NotImplementedError

[html]
directory = htmlcov
```

### 커버리지 리포트

```bash
# 터미널 커버리지 리포트
python -m pytest --cov=app --cov-report=term

# 누락된 라인 표시
python -m pytest --cov=app --cov-report=term-missing

# HTML 리포트 생성
python -m pytest --cov=app --cov-report=html
open htmlcov/index.html

# XML 리포트 생성 (CI/CD용)
python -m pytest --cov=app --cov-report=xml
```

### 커버리지 정책

- **기본**: 경고만 표시, 빌드 실패 없음
- **엄격 모드**: 80% 미만 시 실패
- **목표**: 전체 코드 90% 이상 커버리지

## 🔍 테스트 세부 사항

### 1. 암호화 테스트 (test_encryption.py)

**테스트 케이스:**

- 비밀번호 해싱 및 검증
- 데이터 암호화 및 복호화
- 성능 테스트 (해싱 시간 측정)
- 엣지 케이스 (빈 문자열, 특수문자, 긴 데이터)

```bash
# 암호화 테스트 실행
python -m pytest tests/test_encryption.py -v

# 성능 테스트 포함
python -m pytest tests/test_encryption.py -m "not slow" -v
```

### 2. MinIO 업로드 테스트 (test_minio_upload.py)

**테스트 케이스:**

- 파일 업로드 및 삭제
- 파일 크기 제한 (15MB)
- 지원 형식 검증 (JPEG, PNG, GIF, WebP, BMP)
- 에러 핸들링 (잘못된 파일, 네트워크 오류)

```bash
# MinIO 테스트 실행
python -m pytest tests/test_minio_upload.py -v

# 통합 테스트 포함
python -m pytest tests/test_minio_integration.py -v
```

### 3. FCM 푸시 알림 테스트 (test_fcm_push.py)

**테스트 케이스:**

- 기본 푸시 알림 전송
- 다이어리 작성 알림
- AI 분석 완료 알림
- 토큰 검증 및 에러 핸들링

```bash
# FCM 테스트 실행
python -m pytest tests/test_fcm_push.py -v

# FCM 데모 실행
python examples/fcm_demo.py --test
```

## 🛠️ 테스트 환경 설정

### 테스트 환경변수

```bash
# .env.test 파일 생성
ENVIRONMENT=testing
DATABASE_URL=postgresql://test:test@localhost:5432/saegim_test
MINIO_BUCKET_NAME=test
SECRET_KEY=test_secret_key
ENCRYPTION_KEY=test_encryption_key
```

### 테스트 데이터베이스

```bash
# 테스트 데이터베이스 생성
createdb saegim_test

# 테스트 마이그레이션 실행
ENVIRONMENT=testing alembic upgrade head
```

### MinIO 테스트 설정

```bash
# 테스트용 MinIO 버킷 생성
mc alias set testminio http://localhost:9000 minioadmin minioadmin
mc mb testminio/test
```

## 🔧 테스트 유틸리티

### 테스트 데이터 정리

```bash
# 캐시 및 임시 파일 정리 (크로스 플랫폼)
python -c "
import shutil, pathlib
# __pycache__ 삭제
[shutil.rmtree(p, ignore_errors=True) for p in pathlib.Path('.').glob('**/__pycache__')]
# pytest 캐시 삭제
[shutil.rmtree(p, ignore_errors=True) for p in pathlib.Path('.').glob('**/.pytest_cache')]
# 커버리지 리포트 삭제
pathlib.Path('htmlcov').exists() and shutil.rmtree('htmlcov', ignore_errors=True)
print('✅ 정리 완료')
"
```

### 테스트 데이터 생성 도구

```python
# tests/conftest.py
import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture
def client():
    """테스트 클라이언트 픽스처"""
    return TestClient(app)

@pytest.fixture
def sample_image():
    """테스트용 이미지 파일 픽스처"""
    import io
    from PIL import Image

    img = Image.new('RGB', (100, 100), color='red')
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='JPEG')
    img_bytes.seek(0)
    return img_bytes

@pytest.fixture
def mock_fcm_token():
    """Mock FCM 토큰"""
    return "mock_fcm_token_for_testing"
```

## 📋 테스트 체크리스트

### 개발 중 테스트

- [ ] 새 기능 구현 시 테스트 케이스 작성
- [ ] 기존 테스트 통과 확인
- [ ] 커버리지 80% 이상 유지
- [ ] 엣지 케이스 테스트 포함

### 커밋 전 테스트

- [ ] 전체 테스트 실행 및 통과
- [ ] 커버리지 확인
- [ ] 성능 테스트 확인
- [ ] 보안 테스트 확인

### 배포 전 테스트

- [ ] 운영 환경과 유사한 설정에서 테스트
- [ ] 통합 테스트 실행
- [ ] 부하 테스트 실행 (선택사항)
- [ ] 보안 스캔 실행

## 🚨 트러블슈팅

### 자주 발생하는 문제

#### 1. MinIO 연결 실패

```bash
# MinIO 서버 상태 확인
docker ps | grep minio

# 테스트 버킷 생성
mc mb testminio/test
```

#### 2. 데이터베이스 연결 실패

```bash
# 테스트 데이터베이스 상태 확인
psql -h localhost -U test -d saegim_test

# 테스트 데이터베이스 재생성
dropdb saegim_test && createdb saegim_test
```

#### 3. FCM 테스트 실패

```bash
# FCM 설정 확인
python -c "import os; print('FCM_PROJECT_ID:', os.getenv('FCM_PROJECT_ID'))"

# Mock 테스트로 전환
python -m pytest tests/test_fcm_push.py -k "not real_fcm"
```

### 성능 이슈

```bash
# 느린 테스트 제외
python -m pytest -m "not slow"

# 병렬 테스트 실행 (pytest-xdist 설치 필요)
pip install pytest-xdist
python -m pytest -n auto
```

# 배포 가이드

새김 백엔드의 설치, 설정 및 배포에 대한 종합 가이드입니다.

## 🚀 빠른 시작

### 1. 기본 환경 설정

```bash
# 저장소 클론
git clone <repository-url>
cd saegim-backend

# 가상환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate     # Windows

# 의존성 설치
pip install -r requirements.txt
```

### 2. 환경변수 설정

```bash
# 환경설정 파일 생성
cp .env.example .env

# 필수 환경변수 편집
vim .env
```

### 3. 서버 실행

```bash
# 개발 서버 실행
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 🔧 상세 환경변수 설정

### 기본 환경변수

| 변수명 | 필수 | 설명 | 기본값 | 예시값 |
|--------|------|------|--------|--------|
| `SECRET_KEY` | ✅ | JWT 시크릿 키 | - | `your_jwt_secret_key` |
| `ENCRYPTION_KEY` | ✅ | 데이터 암호화 키 | - | `your_encryption_key` |
| `DATABASE_URL` | ✅ | PostgreSQL 연결 URL | - | `postgresql://user:pass@localhost:5432/saegim` |
| `REDIS_URL` | ❌ | Redis 연결 URL | `redis://localhost:6379/0` | `redis://localhost:6379/0` |
| `ALLOWED_HOSTS` | ❌ | CORS 허용 도메인 | `*` | `http://localhost:3000,https://saegim.com` |
| `ENVIRONMENT` | ❌ | 실행 환경 | `development` | `development`, `production` |

### MinIO 파일 저장소 설정

| 변수명 | 필수 | 설명 | 기본값 | 예시값 |
|--------|------|------|--------|--------|
| `MINIO_ENDPOINT` | ✅ | MinIO 서버 엔드포인트 | `localhost:9000` | `localhost:9000` |
| `MINIO_ACCESS_KEY` | ✅ | MinIO 액세스 키 | `minioadmin` | `minioadmin` |
| `MINIO_SECRET_KEY` | ✅ | MinIO 시크릿 키 | `minioadmin` | `minioadmin` |
| `MINIO_SECURE` | ❌ | HTTPS 사용 여부 | `false` | `false`, `true` |
| `MINIO_BUCKET_NAME` | ❌ | MinIO 버킷명 | `saegim-images` | `saegim-images` |

### FCM 푸시 알림 설정

| 변수명 | 필수 | 설명 | 예시값 |
|--------|------|------|--------|
| `FCM_PROJECT_ID` | ✅ | Firebase 프로젝트 ID | `your-firebase-project-id` |
| `FCM_SERVICE_ACCOUNT_JSON` | ✅ | Service Account JSON 문자열 | `'{"type":"service_account",...}'` |

## 🐳 Docker 배포

### Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 시스템 의존성 설치
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY . .

# 포트 노출
EXPOSE 8000

# 서버 실행
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### docker-compose.yml

```yaml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:password@db:5432/saegim
      - REDIS_URL=redis://redis:6379/0
      - MINIO_ENDPOINT=minio:9000
    depends_on:
      - db
      - redis
      - minio
    volumes:
      - ./.env:/app/.env

  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=saegim
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  minio:
    image: minio/minio
    ports:
      - "9000:9000"
      - "9001:9001"
    environment:
      - MINIO_ROOT_USER=minioadmin
      - MINIO_ROOT_PASSWORD=minioadmin
    command: server /data --console-address ":9001"
    volumes:
      - minio_data:/data

volumes:
  postgres_data:
  minio_data:
```

### Docker 실행

```bash
# 빌드 및 실행
docker-compose up -d

# 로그 확인
docker-compose logs -f app

# 정리
docker-compose down -v
```

## 📦 MinIO 설정

### Docker로 MinIO 실행 (권장)

```bash
# MinIO 서버 실행
docker run -d \
  --name minio \
  -p 9000:9000 \
  -p 9001:9001 \
  -e "MINIO_ROOT_USER=minioadmin" \
  -e "MINIO_ROOT_PASSWORD=minioadmin" \
  minio/minio server /data --console-address ":9001"
```

### 로컬 설치

#### macOS (Homebrew)

```bash
brew install minio/stable/minio
minio server /data
```

#### Linux

```bash
# 바이너리 다운로드
wget https://dl.min.io/server/minio/release/linux-amd64/minio
chmod +x minio

# 서버 실행
./minio server /data
```

#### Windows

```powershell
# 바이너리 다운로드
Invoke-WebRequest -Uri "https://dl.min.io/server/minio/release/windows-amd64/minio.exe" -OutFile "minio.exe"

# 서버 실행
.\minio.exe server C:\data
```

### MinIO 웹 콘솔

- URL: <http://localhost:9001>
- 로그인: minioadmin / minioadmin
- 버킷 생성: `saegim-images`

## 🔥 FCM 설정

### 1. Firebase Console 설정

```bash
# Firebase Console 접속
open https://console.firebase.google.com

# 프로젝트 선택 > 프로젝트 설정 > 서비스 계정
# "새 비공개 키 생성" 클릭 > JSON 파일 다운로드
```

### 2. Service Account 설정

**방법 1: JSON 파일 사용**

```bash
# JSON 파일을 문자열로 변환
export FCM_SERVICE_ACCOUNT_JSON=$(cat path/to/service-account.json | tr -d '\n')
```

**방법 2: 직접 입력**

```bash
# .env 파일에 직접 설정
FCM_SERVICE_ACCOUNT_JSON='{"type":"service_account","project_id":"your-project",...}'
```

### 3. FCM 테스트

```bash
# FCM 데모 실행 (대화형)
python examples/fcm_demo.py

# FCM 데모 실행 (토큰 지정)
python examples/fcm_demo.py --token YOUR_FCM_TOKEN

# 도움말 확인
python examples/fcm_demo.py --help
```

## 🗄️ 데이터베이스 설정

### PostgreSQL 설치

#### Docker 사용 (권장)

```bash
# PostgreSQL 컨테이너 실행
docker run -d \
  --name postgres \
  -p 5432:5432 \
  -e POSTGRES_DB=saegim \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=password \
  postgres:15
```

#### 로컬 설치

**macOS (Homebrew)**

```bash
brew install postgresql@15
brew services start postgresql@15
createdb saegim
```

**Ubuntu/Debian**

```bash
sudo apt update
sudo apt install postgresql-15
sudo -u postgres createdb saegim
```

### 데이터베이스 마이그레이션

```bash
# Alembic 마이그레이션 실행
alembic upgrade head

# 새 마이그레이션 생성
alembic revision --autogenerate -m "Add new table"
```

## 🚀 운영 환경 배포

### 1. 환경변수 검증

```bash
# 필수 환경변수 확인
python -c "
import os
required = ['SECRET_KEY', 'ENCRYPTION_KEY', 'DATABASE_URL', 'FCM_PROJECT_ID', 'FCM_SERVICE_ACCOUNT_JSON']
missing = [var for var in required if not os.getenv(var)]
if missing:
    print(f'Missing required environment variables: {missing}')
    exit(1)
print('All required environment variables are set')
"
```

### 2. Gunicorn 사용 (운영 권장)

```bash
# Gunicorn 설치
pip install gunicorn

# 서버 실행
gunicorn app.main:app \
  --bind 0.0.0.0:8000 \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --access-logfile - \
  --error-logfile -
```

### 3. Nginx 설정 예시

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # 정적 파일 서빙 (선택사항)
    location /static/ {
        alias /app/static/;
    }
}
```

### 4. Systemd 서비스 (Linux)

```ini
# /etc/systemd/system/saegim-backend.service
[Unit]
Description=Saegim Backend API
After=network.target

[Service]
Type=exec
User=saegim
Group=saegim
WorkingDirectory=/app
Environment=PATH=/app/venv/bin
EnvironmentFile=/app/.env
ExecStart=/app/venv/bin/gunicorn app.main:app --bind 0.0.0.0:8000 --workers 4 --worker-class uvicorn.workers.UvicornWorker
ExecReload=/bin/kill -s HUP $MAINPID
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# 서비스 등록 및 시작
sudo systemctl daemon-reload
sudo systemctl enable saegim-backend
sudo systemctl start saegim-backend

# 상태 확인
sudo systemctl status saegim-backend
```

## 🔍 배포 확인

### 헬스 체크

```bash
# API 서버 상태 확인
curl http://localhost:8000/health

# 데이터베이스 연결 확인
curl http://localhost:8000/health/db

# 모든 서비스 상태 확인
curl http://localhost:8000/health/all
```

### 로그 모니터링

```bash
# 애플리케이션 로그
tail -f /var/log/saegim-backend/app.log

# Nginx 로그
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log

# Systemd 로그
journalctl -u saegim-backend -f
```

## 🔧 트러블슈팅

### 자주 발생하는 문제

#### 1. 데이터베이스 연결 오류

```bash
# PostgreSQL 서비스 상태 확인
sudo systemctl status postgresql

# 연결 테스트
psql -h localhost -U postgres -d saegim
```

#### 2. MinIO 연결 오류

```bash
# MinIO 서비스 상태 확인
docker ps | grep minio

# 버킷 존재 확인
mc alias set local http://localhost:9000 minioadmin minioadmin
mc ls local/
```

#### 3. FCM 설정 오류

```bash
# Service Account JSON 형식 확인
python -c "import json; json.loads(open('service-account.json').read())"

# FCM 테스트
python examples/fcm_demo.py --test
```

### 성능 최적화

#### Gunicorn 워커 수 설정

```bash
# CPU 코어 수에 따른 워커 수 계산
python -c "import multiprocessing; print(f'권장 워커 수: {(multiprocessing.cpu_count() * 2) + 1}')"
```

#### 데이터베이스 커넥션 풀

```python
# app/core/config.py
DATABASE_POOL_SIZE = 20
DATABASE_MAX_OVERFLOW = 30
```

## 📋 배포 체크리스트

### 배포 전 확인사항

- [ ] 모든 환경변수 설정 완료
- [ ] 보안 키 생성 및 설정
- [ ] 데이터베이스 마이그레이션 실행
- [ ] MinIO 서버 설정 및 버킷 생성
- [ ] FCM 서비스 계정 설정
- [ ] 테스트 실행 및 통과 확인

### 배포 후 확인사항

- [ ] API 서버 정상 동작 확인
- [ ] 데이터베이스 연결 확인
- [ ] 파일 업로드 기능 확인
- [ ] 푸시 알림 기능 확인
- [ ] 로그 모니터링 설정
- [ ] 백업 설정 완료

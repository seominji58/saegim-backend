# 보안 기능 가이드

새김 백엔드의 보안 기능 및 암호화 시스템에 대한 상세 가이드입니다.

## 🔐 보안 아키텍처

### 암호화 지원

- **비밀번호 해싱**: bcrypt (cost factor: 12)
- **민감 데이터 암호화**: AES-256-GCM
- **JWT 인증**: HS256 알고리즘

## 📚 사용법

### 1. 비밀번호 해싱

```python
from app.utils.encryption import hash_password, verify_password

# 비밀번호 해싱
hashed = hash_password("my_password")

# 비밀번호 검증
is_valid = verify_password("my_password", hashed)
```

### 2. 데이터 암호화

```python
from app.utils.encryption import encrypt_data, decrypt_data

# 데이터 암호화
encrypted = encrypt_data("민감한 정보")

# 데이터 복호화
decrypted = decrypt_data(encrypted)
```

### 3. JWT 토큰

```python
from app.core.security import create_access_token, decode_access_token

# 토큰 생성
token = create_access_token({"sub": "user_id"})

# 토큰 디코딩
payload = decode_access_token(token)
```

## 🔑 보안 키 생성

### OpenSSL 사용 (권장)

```bash
# JWT 시크릿 키 생성 (32바이트)
openssl rand -base64 32

# 데이터 암호화 키 생성 (32바이트)
openssl rand -base64 32
```

### Python 스크립트 사용

```python
import secrets
import base64

# JWT 시크릿 키 생성
jwt_key = base64.b64encode(secrets.token_bytes(32)).decode()
print(f"SECRET_KEY={jwt_key}")

# 데이터 암호화 키 생성
encryption_key = base64.b64encode(secrets.token_bytes(32)).decode()
print(f"ENCRYPTION_KEY={encryption_key}")
```

## 🛡️ 보안 환경변수

### 필수 보안 환경변수

| 변수명 | 설명 | 형식 | 예시 |
|--------|------|------|------|
| `SECRET_KEY` | JWT 토큰 서명용 시크릿 키 | Base64 | `your_jwt_secret_key` |
| `ENCRYPTION_KEY` | AES-256 데이터 암호화 키 | Base64 | `your_encryption_key` |

### 환경변수 설정 예시

```bash
# .env 파일
SECRET_KEY=dGhpc19pc19hX3Zlcnlfc2VjdXJlX2tleV90aGF0X25vX29uZV9jYW5fZ3Vlc3M=
ENCRYPTION_KEY=YW5vdGhlcl9zdXBlcl9zZWN1cmVfa2V5X2Zvcl9lbmNyeXB0aW9uX3B1cnBvc2Vz
```

## ⚠️ 보안 주의사항

### 개발 환경

- 기본 키 값은 절대 사용하지 말 것
- 각 개발자는 고유한 키를 생성하여 사용
- `.env` 파일은 Git에 커밋하지 말 것

### 운영 환경

- 키는 환경변수 또는 보안 볼트에서 관리
- 키 로테이션 정책 수립 및 적용
- 정기적인 보안 감사 실시

### 키 관리

- 키는 안전한 곳에 별도 백업
- 키가 노출된 경우 즉시 교체
- 키 생성 시 충분한 엔트로피 확보

## 🔍 보안 테스트

### 암호화 테스트

```bash
# 암호화 기능 테스트
python examples/encryption_demo.py

# 보안 테스트 실행
python -m pytest tests/test_encryption.py -v
```

### 성능 테스트

- bcrypt 해싱 시간: ~100ms (cost factor 12)
- AES-256-GCM 암호화: ~1ms (1KB 데이터 기준)
- JWT 토큰 생성/검증: ~1ms

## 🛠️ 보안 설정 검증

### 설정 확인 스크립트

```python
import os
import base64

def verify_security_config():
    """보안 설정 검증"""

    # SECRET_KEY 검증
    secret_key = os.getenv("SECRET_KEY")
    if not secret_key:
        print("❌ SECRET_KEY가 설정되지 않았습니다.")
        return False

    try:
        decoded = base64.b64decode(secret_key)
        if len(decoded) < 32:
            print("❌ SECRET_KEY가 너무 짧습니다. (최소 32바이트)")
            return False
    except Exception:
        print("❌ SECRET_KEY가 유효한 Base64 형식이 아닙니다.")
        return False

    # ENCRYPTION_KEY 검증
    encryption_key = os.getenv("ENCRYPTION_KEY")
    if not encryption_key:
        print("❌ ENCRYPTION_KEY가 설정되지 않았습니다.")
        return False

    try:
        decoded = base64.b64decode(encryption_key)
        if len(decoded) != 32:
            print("❌ ENCRYPTION_KEY는 정확히 32바이트여야 합니다.")
            return False
    except Exception:
        print("❌ ENCRYPTION_KEY가 유효한 Base64 형식이 아닙니다.")
        return False

    print("✅ 모든 보안 설정이 올바르게 구성되었습니다.")
    return True

if __name__ == "__main__":
    verify_security_config()
```

## 📋 보안 체크리스트

### 개발 전 확인사항

- [ ] 고유한 SECRET_KEY 생성
- [ ] 고유한 ENCRYPTION_KEY 생성
- [ ] .env 파일이 .gitignore에 포함되어 있는지 확인
- [ ] 보안 테스트 통과 확인

### 배포 전 확인사항

- [ ] 운영 환경용 키 별도 생성
- [ ] 키가 환경변수로 안전하게 설정되어 있는지 확인
- [ ] 개발용 키가 운영 환경에 사용되지 않는지 확인
- [ ] HTTPS 설정 완료

### 정기 점검사항

- [ ] 키 로테이션 일정 확인
- [ ] 보안 로그 검토
- [ ] 의존성 취약점 스캔
- [ ] 보안 테스트 정기 실행

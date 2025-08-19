# 기능 사용법 가이드

새김 백엔드의 주요 기능별 상세 사용법과 API 가이드입니다.

## 🔐 암호화 기능

### 비밀번호 해싱

사용자 비밀번호를 안전하게 해싱하고 검증하는 기능입니다.

```python
from app.utils.encryption import hash_password, verify_password

# 회원가입 시 비밀번호 해싱
def create_user(password: str):
    hashed_password = hash_password(password)
    # 데이터베이스에 hashed_password 저장
    return hashed_password

# 로그인 시 비밀번호 검증
def authenticate_user(password: str, hashed_password: str):
    is_valid = verify_password(password, hashed_password)
    return is_valid
```

**특징:**

- bcrypt 알고리즘 사용 (cost factor: 12)
- 솔트 자동 생성 및 적용
- 평균 해싱 시간: ~100ms

### 데이터 암호화

민감한 데이터를 AES-256-GCM으로 암호화하는 기능입니다.

```python
from app.utils.encryption import encrypt_data, decrypt_data

# 민감한 데이터 암호화
def save_sensitive_data(data: str):
    encrypted_data = encrypt_data(data)
    # 데이터베이스에 encrypted_data 저장
    return encrypted_data

# 데이터 복호화
def get_sensitive_data(encrypted_data: str):
    original_data = decrypt_data(encrypted_data)
    return original_data
```

**특징:**

- AES-256-GCM 알고리즘
- 자동 IV(Initialization Vector) 생성
- 무결성 검증 포함

### JWT 토큰 인증

사용자 인증을 위한 JWT 토큰 생성 및 검증 기능입니다.

```python
from app.core.security import create_access_token, decode_access_token

# 로그인 성공 시 토큰 생성
def login_user(user_id: str):
    token_data = {"sub": user_id}
    access_token = create_access_token(token_data)
    return access_token

# API 요청 시 토큰 검증
def verify_token(token: str):
    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        return user_id
    except:
        return None
```

**설정:**

- 만료 시간: 24시간 (기본값)
- 알고리즘: HS256
- 클레임: sub (subject), exp (expiration), iat (issued at)

## 📁 파일 업로드 (MinIO)

이미지 파일을 MinIO 객체 스토리지에 업로드하는 기능입니다.

### 기본 사용법

```python
from fastapi import UploadFile
from app.utils.minio_upload import upload_image_to_minio, delete_image_from_minio

# 이미지 업로드
async def upload_profile_image(file: UploadFile):
    try:
        file_id, image_url = await upload_image_to_minio(file)
        return {
            "success": True,
            "file_id": file_id,
            "url": image_url
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

# 이미지 삭제
def delete_profile_image(object_key: str):
    success = delete_image_from_minio(object_key)
    return {"deleted": success}
```

### FastAPI 엔드포인트 예시

```python
from fastapi import APIRouter, UploadFile, File, HTTPException

router = APIRouter()

@router.post("/upload")
async def upload_image(file: UploadFile = File(...)):
    """이미지 업로드 API"""

    # 파일 유효성 검사
    if not file.content_type.startswith('image/'):
        raise HTTPException(400, "이미지 파일만 업로드 가능합니다")

    try:
        file_id, image_url = await upload_image_to_minio(file)
        return {
            "message": "업로드 성공",
            "file_id": file_id,
            "url": image_url
        }
    except Exception as e:
        raise HTTPException(500, f"업로드 실패: {str(e)}")

@router.delete("/delete/{object_key}")
async def delete_image(object_key: str):
    """이미지 삭제 API"""

    success = delete_image_from_minio(object_key)
    if success:
        return {"message": "삭제 성공"}
    else:
        raise HTTPException(404, "파일을 찾을 수 없습니다")
```

### 기능 특징

- **파일 크기 제한**: 최대 15MB
- **지원 형식**: JPEG, PNG, GIF, WebP, BMP
- **자동 폴더 구성**: `images/YYYY/MM/DD/파일ID.확장자`
- **안전한 파일명**: UUID 기반 고유 식별자
- **자동 MIME 타입 검증**

### 설정 옵션

```python
# app/core/config.py
MINIO_ENDPOINT = "localhost:9000"
MINIO_ACCESS_KEY = "minioadmin"
MINIO_SECRET_KEY = "minioadmin"
MINIO_SECURE = False
MINIO_BUCKET_NAME = "saegim-images"
MAX_FILE_SIZE = 15 * 1024 * 1024  # 15MB
```

## 🔥 FCM 푸시 알림

Firebase Cloud Messaging을 사용한 푸시 알림 기능입니다.

### 기본 푸시 알림

```python
from app.utils.fcm_push import send_push_notification

# 기본 알림 전송
async def send_notification(user_fcm_token: str, title: str, message: str):
    try:
        result = await send_push_notification(
            token=user_fcm_token,
            title=title,
            body=message,
            data={"type": "general", "timestamp": str(datetime.now())}
        )
        return {"success": True, "message_id": result}
    except Exception as e:
        return {"success": False, "error": str(e)}
```

### 다이어리 관련 알림

```python
from app.utils.fcm_push import send_diary_reminder, send_ai_analysis_complete

# 다이어리 작성 알림
async def remind_diary_writing(user_fcm_token: str, user_name: str):
    try:
        result = await send_diary_reminder(
            token=user_fcm_token,
            user_name=user_name
        )
        return {"success": True, "message_id": result}
    except Exception as e:
        return {"success": False, "error": str(e)}

# AI 분석 완료 알림
async def notify_ai_analysis_complete(user_fcm_token: str, diary_id: str):
    try:
        result = await send_ai_analysis_complete(
            token=user_fcm_token,
            diary_id=diary_id
        )
        return {"success": True, "message_id": result}
    except Exception as e:
        return {"success": False, "error": str(e)}
```

### FastAPI 엔드포인트 예시

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

class NotificationRequest(BaseModel):
    token: str
    title: str
    body: str
    data: dict = {}

router = APIRouter()

@router.post("/send-notification")
async def send_notification_endpoint(request: NotificationRequest):
    """푸시 알림 전송 API"""

    try:
        result = await send_push_notification(
            token=request.token,
            title=request.title,
            body=request.body,
            data=request.data
        )
        return {
            "success": True,
            "message": "알림이 성공적으로 전송되었습니다",
            "message_id": result
        }
    except Exception as e:
        raise HTTPException(500, f"알림 전송 실패: {str(e)}")

@router.post("/diary-reminder")
async def send_diary_reminder_endpoint(token: str, user_name: str):
    """다이어리 작성 알림 API"""

    try:
        result = await send_diary_reminder(token=token, user_name=user_name)
        return {"success": True, "message_id": result}
    except Exception as e:
        raise HTTPException(500, f"알림 전송 실패: {str(e)}")
```

### 알림 타입별 템플릿

```python
# 다이어리 작성 리마인더
DIARY_REMINDER = {
    "title": "오늘의 일기를 써보세요! ✍️",
    "body": "{user_name}님, 하루를 마무리하며 소중한 순간을 기록해보세요.",
    "data": {
        "type": "diary_reminder",
        "action": "write_diary"
    }
}

# AI 분석 완료
AI_ANALYSIS_COMPLETE = {
    "title": "AI 분석이 완료되었습니다! 🤖",
    "body": "새로운 감정 분석 결과를 확인해보세요.",
    "data": {
        "type": "ai_analysis",
        "action": "view_analysis",
        "diary_id": "{diary_id}"
    }
}

# 소셜 알림
SOCIAL_NOTIFICATION = {
    "title": "새로운 소식이 있어요! 👥",
    "body": "친구들의 새로운 활동을 확인해보세요.",
    "data": {
        "type": "social",
        "action": "view_feed"
    }
}
```

## 🛡️ 보안 미들웨어

### CORS 설정

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://saegim.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 인증 미들웨어

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """현재 사용자 인증"""

    try:
        payload = decode_access_token(credentials.credentials)
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="유효하지 않은 토큰입니다"
            )
        return user_id
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증에 실패했습니다"
        )

# 보호된 엔드포인트 예시
@router.get("/profile")
async def get_profile(current_user: str = Depends(get_current_user)):
    """사용자 프로필 조회 (인증 필요)"""
    return {"user_id": current_user, "message": "프로필 정보"}
```

## 📊 API 응답 형식

### 표준 응답 형식

```python
from pydantic import BaseModel
from typing import Optional, Any

class ApiResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Any] = None
    error: Optional[str] = None

# 성공 응답
def success_response(data: Any = None, message: str = "성공"):
    return ApiResponse(
        success=True,
        message=message,
        data=data
    )

# 에러 응답
def error_response(error: str, message: str = "오류가 발생했습니다"):
    return ApiResponse(
        success=False,
        message=message,
        error=error
    )
```

### 페이지네이션

```python
from pydantic import BaseModel
from typing import List, TypeVar, Generic

T = TypeVar('T')

class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    size: int
    pages: int

def paginate_response(items: List[T], page: int, size: int, total: int):
    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size
    )
```

## 🔧 유틸리티 함수

### 날짜/시간 처리

```python
from datetime import datetime, timezone
import pytz

def get_kst_now():
    """한국 시간 현재 시각"""
    kst = pytz.timezone('Asia/Seoul')
    return datetime.now(kst)

def format_datetime(dt: datetime, format_str: str = "%Y-%m-%d %H:%M:%S"):
    """날짜 형식화"""
    return dt.strftime(format_str)

def parse_datetime(date_str: str, format_str: str = "%Y-%m-%d %H:%M:%S"):
    """문자열을 datetime으로 변환"""
    return datetime.strptime(date_str, format_str)
```

### 데이터 검증

```python
import re
from typing import Optional

def validate_email(email: str) -> bool:
    """이메일 형식 검증"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_password(password: str) -> tuple[bool, Optional[str]]:
    """비밀번호 강도 검증"""
    if len(password) < 8:
        return False, "비밀번호는 8자 이상이어야 합니다"

    if not re.search(r'[A-Za-z]', password):
        return False, "비밀번호에 영문자가 포함되어야 합니다"

    if not re.search(r'\d', password):
        return False, "비밀번호에 숫자가 포함되어야 합니다"

    return True, None

def sanitize_filename(filename: str) -> str:
    """파일명 안전하게 정리"""
    import uuid
    from pathlib import Path

    # 확장자 추출
    ext = Path(filename).suffix
    # UUID로 새 파일명 생성
    safe_name = str(uuid.uuid4())
    return f"{safe_name}{ext}"
```

## 📋 기능별 체크리스트

### 암호화 기능 사용 시

- [ ] 환경변수에 강력한 키 설정
- [ ] 비밀번호 해싱에 bcrypt 사용
- [ ] 민감 데이터 암호화에 AES-256-GCM 사용
- [ ] JWT 토큰 만료 시간 적절히 설정

### 파일 업로드 사용 시

- [ ] MinIO 서버 설정 및 버킷 생성
- [ ] 파일 크기 제한 설정 (15MB)
- [ ] 지원 파일 형식 제한
- [ ] 파일명 안전하게 처리

### FCM 푸시 알림 사용 시

- [ ] Firebase 프로젝트 설정
- [ ] Service Account JSON 설정
- [ ] FCM 토큰 유효성 검증
- [ ] 알림 타입별 템플릿 준비

### API 보안 설정 시

- [ ] CORS 정책 적절히 설정
- [ ] JWT 인증 미들웨어 적용
- [ ] 입력 데이터 검증 및 살균
- [ ] 에러 메시지에 민감 정보 노출 방지

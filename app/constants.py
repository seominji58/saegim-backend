"""
상수 정의 모듈

애플리케이션 전반에서 사용되는 상수들을 중앙 집중식으로 관리
"""

from enum import Enum


class EmotionType(str, Enum):
    """감정 타입 열거형"""

    HAPPY = "happy"
    SAD = "sad"
    ANGRY = "angry"
    PEACEFUL = "peaceful"
    UNREST = "unrest"


class APIType(str, Enum):
    """OpenAI API 타입 열거형"""

    GENERATE = "generate"
    KEYWORDS = "keywords"
    EMOTION_ANALYSIS = "emotion_analysis"
    INTEGRATED_ANALYSIS = "integrated_analysis"


class AccountType(str, Enum):
    """계정 타입 열거형"""

    SOCIAL = "social"
    EMAIL = "email"


class OAuthProvider(str, Enum):
    """OAuth 제공자 열거형"""

    GOOGLE = "google"
    KAKAO = "kakao"
    NAVER = "naver"


class TaskStatus(str, Enum):
    """작업 상태 열거형"""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class NotificationStatus(str, Enum):
    """알림 상태 열거형"""

    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL_SUCCESS = "partial_success"


class SortOrder(str, Enum):
    """정렬 순서 열거형"""

    ASC = "asc"
    DESC = "desc"


class HttpMethod(str, Enum):
    """HTTP 메서드 열거형"""

    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"


# 시스템 상수
class SystemConstants:
    """시스템 전반에서 사용되는 상수들"""

    # 페이지네이션
    DEFAULT_PAGE_SIZE = 20
    MAX_PAGE_SIZE = 100
    MIN_PAGE_SIZE = 1

    # 인증
    ACCESS_TOKEN_EXPIRE_MINUTES = 30
    REFRESH_TOKEN_EXPIRE_DAYS = 30

    # 파일 업로드
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}

    # AI 모델
    DEFAULT_AI_EMOTION_CONFIDENCE = 0.5
    MIN_CONTENT_LENGTH_FOR_KEYWORDS = 2

    # 소프트 삭제
    SOFT_DELETE_RETENTION_DAYS = 30


# 응답 메시지 상수
class ResponseMessages:
    """API 응답 메시지 상수"""

    # 성공 메시지
    SUCCESS = "성공적으로 처리되었습니다."
    CREATED = "생성되었습니다."
    UPDATED = "수정되었습니다."
    DELETED = "삭제되었습니다."

    # 에러 메시지
    NOT_FOUND = "요청한 리소스를 찾을 수 없습니다."
    UNAUTHORIZED = "인증이 필요합니다."
    FORBIDDEN = "접근 권한이 없습니다."
    BAD_REQUEST = "잘못된 요청입니다."
    INTERNAL_SERVER_ERROR = "내부 서버 오류가 발생했습니다."

    # 인증 관련
    INVALID_CREDENTIALS = "잘못된 인증 정보입니다."
    TOKEN_EXPIRED = "토큰이 만료되었습니다."
    TOKEN_BLACKLISTED = "블랙리스트에 등록된 토큰입니다."

    # 계정 관련
    ACCOUNT_DELETED = "탈퇴된 계정입니다."
    ACCOUNT_PERMANENTLY_DELETED = "영구적으로 삭제된 계정입니다."

    # 다이어리 관련
    DIARY_NOT_FOUND = "다이어리를 찾을 수 없습니다."
    DIARY_ACCESS_DENIED = "다이어리에 접근할 권한이 없습니다."


# API 엔드포인트 상수
class APIEndpoints:
    """API 엔드포인트 상수"""

    # 인증
    AUTH_LOGIN = "/auth/login"
    AUTH_LOGOUT = "/auth/logout"
    AUTH_REFRESH = "/auth/refresh"
    AUTH_GOOGLE_CALLBACK = "/auth/google/callback"

    # 사용자
    USERS_ME = "/users/me"
    USERS_DELETE = "/users/delete"

    # 다이어리
    DIARIES_ROOT = "/diaries"
    DIARIES_BY_ID = "/diaries/{diary_id}"

    # 이미지
    IMAGES_UPLOAD = "/images/upload"
    IMAGES_BY_ID = "/images/{image_id}"


# FCM 상수
class FCMConstants:
    """Firebase Cloud Messaging 관련 상수"""

    # 메시지 타입
    class MessageType(str, Enum):
        DATA = "data"
        NOTIFICATION = "notification"
        MIXED = "mixed"

    # 우선순위
    class Priority(str, Enum):
        HIGH = "high"
        NORMAL = "normal"

    # 기본값
    DEFAULT_PRIORITY = Priority.NORMAL
    DEFAULT_TTL = 86400  # 24시간 (초)
    MAX_TOKENS_PER_REQUEST = 1000
    BATCH_SIZE = 500


# 에러 코드 상수
class ErrorCodes:
    """애플리케이션 에러 코드"""

    # 일반 에러
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    NOT_FOUND_ERROR = "NOT_FOUND_ERROR"

    # 인증/권한 에러
    AUTH_ERROR = "AUTH_ERROR"
    TOKEN_ERROR = "TOKEN_ERROR"
    PERMISSION_ERROR = "PERMISSION_ERROR"

    # 계정 에러
    ACCOUNT_DELETED = "ACCOUNT_DELETED"
    ACCOUNT_PERMANENTLY_DELETED = "ACCOUNT_PERMANENTLY_DELETED"

    # 외부 서비스 에러
    OPENAI_ERROR = "OPENAI_ERROR"
    FCM_ERROR = "FCM_ERROR"
    OAUTH_ERROR = "OAUTH_ERROR"

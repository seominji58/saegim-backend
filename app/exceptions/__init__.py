"""
예외 클래스 패키지

도메인별로 분리된 예외 클래스들을 관리합니다:
- base: 기본 예외 클래스
- ai: AI 서비스 관련 예외
- diary: 다이어리 관련 예외
- auth: 인증 관련 예외
"""

from .base import BusinessException
from .ai import (
    AIServiceException,
    AIServiceUnavailableException,
    AITokenLimitExceededException,
    AIGenerationFailedException,
    AIRateLimitExceededException,
    RegenerationLimitExceededException,
    SessionNotFoundException,
    InvalidRequestException
)
from .diary import (
    DiaryServiceException,
    DiaryNotFoundException,
    DiaryAccessDeniedException,
    DiaryValidationException,
    DiaryImageException,
    DiaryStorageLimitException
)

__all__ = [
    # Base exceptions
    "BusinessException",
    
    # AI exceptions
    "AIServiceException",
    "AIServiceUnavailableException", 
    "AITokenLimitExceededException",
    "AIGenerationFailedException",
    "AIRateLimitExceededException",
    "RegenerationLimitExceededException",
    "SessionNotFoundException",
    "InvalidRequestException",
    
    # Diary exceptions
    "DiaryServiceException",
    "DiaryNotFoundException",
    "DiaryAccessDeniedException",
    "DiaryValidationException",
    "DiaryImageException",
    "DiaryStorageLimitException",
]
"""
AI 서비스 관련 예외 클래스들
"""

from typing import Optional
from .base import BusinessException


class AIServiceException(BusinessException):
    """AI 서비스 관련 예외 기본 클래스"""
    pass


class AIServiceUnavailableException(AIServiceException):
    """AI 서비스 일시적 오류 (3001)"""
    
    def __init__(
        self,
        detail: str = "AI 서비스가 일시적으로 이용할 수 없습니다. 잠시 후 다시 시도해주세요.",
        service_name: Optional[str] = None
    ):
        self.service_name = service_name
        
        super().__init__(
            status_code=503,
            detail=detail,
            error_code="AI_SERVICE_UNAVAILABLE",
            headers={"Retry-After": "30"}  # 30초 후 재시도 권장
        )


class AITokenLimitExceededException(AIServiceException):
    """AI 토큰 한도 초과 (3002)"""
    
    def __init__(
        self,
        used_tokens: int,
        limit_tokens: int,
        user_id: Optional[str] = None
    ):
        self.used_tokens = used_tokens
        self.limit_tokens = limit_tokens
        self.user_id = user_id
        
        detail = (
            f"일일 토큰 사용량을 초과했습니다. "
            f"사용량: {used_tokens}/{limit_tokens} 토큰"
        )
        
        super().__init__(
            status_code=429,
            detail=detail,
            error_code="AI_TOKEN_LIMIT_EXCEEDED"
        )


class AIGenerationFailedException(AIServiceException):
    """AI 텍스트 생성 실패 (3004)"""
    
    def __init__(
        self,
        detail: str = "AI 텍스트 생성에 실패했습니다. 다시 시도해주세요.",
        model_name: Optional[str] = None,
        error_type: Optional[str] = None
    ):
        self.model_name = model_name
        self.error_type = error_type
        
        super().__init__(
            status_code=500,
            detail=detail,
            error_code="AI_GENERATION_FAILED"
        )


class AIRateLimitExceededException(AIServiceException):
    """API 호출 한도 초과 (3005)"""
    
    def __init__(
        self,
        detail: str = "API 호출 한도를 초과했습니다. 잠시 후 다시 시도해주세요.",
        current_count: Optional[int] = None,
        limit_count: Optional[int] = None,
        retry_after: int = 60  # 기본 60초 후 재시도
    ):
        self.current_count = current_count
        self.limit_count = limit_count
        self.retry_after = retry_after
        
        super().__init__(
            status_code=429,
            detail=detail,
            error_code="AI_RATE_LIMIT_EXCEEDED",
            headers={"Retry-After": str(retry_after)}
        )


class RegenerationLimitExceededException(AIRateLimitExceededException):
    """AI 재생성 횟수 제한 초과 예외 (재생성은 Rate Limit의 특수한 경우)"""
    
    def __init__(
        self,
        current_count: int,
        max_count: int = 5,
        session_id: Optional[str] = None
    ):
        self.session_id = session_id
        
        detail = (
            f"AI 글귀 재생성은 최대 {max_count}회까지만 가능합니다. "
            f"현재 {current_count-1}회 사용하셨습니다. "
            f"새로운 세션으로 다시 시도해주세요."
        )
        
        super().__init__(
            detail=detail,
            current_count=current_count,
            limit_count=max_count,
            retry_after=0  # 새 세션으로 즉시 재시도 가능
        )


class SessionNotFoundException(AIServiceException):
    """세션을 찾을 수 없는 예외"""
    
    def __init__(self, session_id: str):
        self.session_id = session_id
        
        detail = f"세션을 찾을 수 없습니다: {session_id}"
        
        super().__init__(
            status_code=404,
            detail=detail,
            error_code="SESSION_NOT_FOUND"
        )


class InvalidRequestException(BusinessException):
    """잘못된 요청 예외"""
    
    def __init__(
        self,
        detail: str = "잘못된 요청입니다.",
        field: Optional[str] = None
    ):
        self.field = field
        
        super().__init__(
            status_code=400,
            detail=detail,
            error_code="INVALID_REQUEST"
        )
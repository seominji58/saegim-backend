"""
기본 예외 클래스
"""

from fastapi import HTTPException
from typing import Optional, Dict, Any


class BusinessException(HTTPException):
    """비즈니스 로직 관련 예외 기본 클래스"""
    
    def __init__(
        self,
        status_code: int = 400,
        detail: str = "비즈니스 로직 오류가 발생했습니다.",
        headers: Optional[Dict[str, Any]] = None,
        error_code: Optional[str] = None
    ):
        super().__init__(status_code=status_code, detail=detail, headers=headers)
        self.error_code = error_code
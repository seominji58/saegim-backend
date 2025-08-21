"""
응답 유틸리티 함수
한글 인코딩을 위한 응답 헬퍼 함수들
"""

from fastapi.responses import JSONResponse
from typing import Any, Dict, Optional
from datetime import datetime
import uuid


def create_korean_response(
    data: Any = None,
    message: Optional[str] = None,
    status_code: int = 200,
    success: bool = True
) -> JSONResponse:
    """
    한글 인코딩이 명시된 JSON 응답 생성
    
    Args:
        data: 응답 데이터
        message: 응답 메시지
        status_code: HTTP 상태 코드
        success: 성공 여부
        
    Returns:
        UTF-8 인코딩이 명시된 JSONResponse
    """
    response_data = {
        "success": success,
        "data": data,
        "message": message,
        "timestamp": datetime.now().isoformat(),
        "request_id": str(uuid.uuid4())
    }
    
    return JSONResponse(
        content=response_data,
        status_code=status_code,
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "Cache-Control": "no-cache"
        }
    )


def create_error_response(
    message: str,
    status_code: int = 500,
    error_code: Optional[str] = None
) -> JSONResponse:
    """
    한글 에러 응답 생성
    
    Args:
        message: 에러 메시지
        status_code: HTTP 상태 코드
        error_code: 에러 코드
        
    Returns:
        UTF-8 인코딩이 명시된 에러 JSONResponse
    """
    error_data = {
        "success": False,
        "error": {
            "message": message,
            "code": error_code,
            "timestamp": datetime.now().isoformat(),
            "request_id": str(uuid.uuid4())
        }
    }
    
    return JSONResponse(
        content=error_data,
        status_code=status_code,
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "Cache-Control": "no-cache"
        }
    )

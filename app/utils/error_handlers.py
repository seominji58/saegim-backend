"""
통일된 에러 응답 핸들러
"""

from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse


class StandardHTTPException(HTTPException):
    """표준화된 HTTP 예외 클래스"""

    def __init__(
        self,
        status_code: int,
        detail: str,
        error_code: Optional[str] = None,
        headers: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(status_code=status_code, detail=detail, headers=headers)
        self.error_code = error_code


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """HTTP 예외 처리기"""
    error_code = getattr(exc, "error_code", None)

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": error_code or f"HTTP_{exc.status_code}",
                "message": exc.detail,
            },
            "timestamp": datetime.now().isoformat(),
            "path": request.url.path,
        },
    )


async def validation_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    """검증 예외 처리기"""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "입력 데이터가 유효하지 않습니다.",
                "details": str(exc),
            },
            "timestamp": datetime.now().isoformat(),
            "path": request.url.path,
        },
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """일반 예외 처리기"""
    import logging

    logger = logging.getLogger(__name__)
    logger.error(f"Unhandled exception: {exc}", exc_info=True)

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "내부 서버 오류가 발생했습니다.",
            },
            "timestamp": datetime.now().isoformat(),
            "path": request.url.path,
        },
    )


# 공통 예외 팩토리 함수들
def not_found_exception(resource: str = "리소스") -> StandardHTTPException:
    """404 Not Found 예외 생성"""
    return StandardHTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"{resource}를 찾을 수 없습니다.",
        error_code="NOT_FOUND",
    )


def forbidden_exception(action: str = "작업") -> StandardHTTPException:
    """403 Forbidden 예외 생성"""
    return StandardHTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=f"{action}에 대한 권한이 없습니다.",
        error_code="FORBIDDEN",
    )


def unauthorized_exception(message: str = "인증이 필요합니다.") -> StandardHTTPException:
    """401 Unauthorized 예외 생성"""
    return StandardHTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=message,
        error_code="UNAUTHORIZED",
        headers={"WWW-Authenticate": "Bearer"},
    )


def bad_request_exception(
    message: str, error_code: str = "BAD_REQUEST"
) -> StandardHTTPException:
    """400 Bad Request 예외 생성"""
    return StandardHTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=message,
        error_code=error_code,
    )

"""
통일된 에러 응답 핸들러
데이터베이스 트랜잭션 및 API 에러 처리를 위한 데코레이터와 컨텍스트 매니저
"""

import logging
from contextlib import contextmanager
from datetime import datetime
from functools import wraps
from typing import Any, Callable, Dict, Optional, ParamSpec, TypeVar

from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

# 타입 힌팅을 위한 제네릭 타입들
P = ParamSpec('P')
T = TypeVar('T')

logger = logging.getLogger(__name__)


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


def handle_database_errors(
    error_message: str = "작업 처리 중 오류가 발생했습니다",
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
    log_message: str | None = None,
    reraise_http_exceptions: bool = True
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """
    데이터베이스 트랜잭션 에러 처리 데코레이터

    Args:
        error_message: 사용자에게 표시할 에러 메시지
        status_code: HTTP 상태 코드
        log_message: 로그에 남길 메시지 템플릿 (None이면 기본 템플릿 사용)
        reraise_http_exceptions: HTTPException을 그대로 재발생할지 여부

    Returns:
        데코레이터 함수
    """
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            # 함수 매개변수에서 session 찾기
            session = None
            for arg in args:
                if isinstance(arg, Session):
                    session = arg
                    break
            for value in kwargs.values():
                if isinstance(value, Session):
                    session = value
                    break

            try:
                return func(*args, **kwargs)

            except HTTPException:
                if session:
                    session.rollback()
                if reraise_http_exceptions:
                    raise

            except Exception as e:
                if session:
                    session.rollback()

                # 로그 메시지 생성
                if log_message is None:
                    final_log_message = f"{func.__name__} 실패: {str(e)}"
                else:
                    final_log_message = log_message.format(error=str(e), function=func.__name__)

                logger.error(final_log_message)

                raise HTTPException(
                    status_code=status_code,
                    detail=error_message,
                ) from e

        return wrapper
    return decorator


@contextmanager
def database_transaction_handler(
    session: Session,
    error_message: str = "작업 처리 중 오류가 발생했습니다",
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
    log_context: str = "Database operation"
):
    """
    데이터베이스 트랜잭션 에러 처리 컨텍스트 매니저

    Args:
        session: SQLAlchemy 세션
        error_message: 사용자에게 표시할 에러 메시지
        status_code: HTTP 상태 코드
        log_context: 로그 컨텍스트

    Usage:
        with database_transaction_handler(session, "다이어리 삭제 실패"):
            # database operations
            pass
    """
    try:
        yield
    except HTTPException:
        session.rollback()
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"{log_context} 실패: {str(e)}")
        raise HTTPException(
            status_code=status_code,
            detail=error_message,
        ) from e


def safe_database_operation(
    session: Session,
    operation: Callable[[], T],
    error_message: str = "작업 처리 중 오류가 발생했습니다",
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
    log_context: str = "Database operation"
) -> T:
    """
    안전한 데이터베이스 작업 실행 함수

    Args:
        session: SQLAlchemy 세션
        operation: 실행할 작업 함수
        error_message: 사용자에게 표시할 에러 메시지
        status_code: HTTP 상태 코드
        log_context: 로그 컨텍스트

    Returns:
        작업 결과

    Usage:
        result = safe_database_operation(
            session,
            lambda: session.add(new_item),
            "아이템 생성 실패"
        )
    """
    try:
        return operation()
    except HTTPException:
        session.rollback()
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"{log_context} 실패: {str(e)}")
        raise HTTPException(
            status_code=status_code,
            detail=error_message,
        ) from e


def handle_service_errors(
    error_message: str = "서비스 처리 중 오류가 발생했습니다",
    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
    log_prefix: str | None = None
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """
    서비스 레이어 에러 처리 데코레이터 (세션 없는 작업용)

    Args:
        error_message: 사용자에게 표시할 에러 메시지
        status_code: HTTP 상태 코드
        log_prefix: 로그 메시지 접두사

    Returns:
        데코레이터 함수
    """
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            try:
                return func(*args, **kwargs)
            except HTTPException:
                raise
            except Exception as e:
                if log_prefix:
                    logger.error(f"{log_prefix} - {func.__name__} 실패: {str(e)}")
                else:
                    logger.error(f"{func.__name__} 실패: {str(e)}")

                raise HTTPException(
                    status_code=status_code,
                    detail=error_message,
                ) from e

        return wrapper
    return decorator


class ErrorPatterns:
    """공통 에러 메시지 패턴 상수"""

    # 다이어리 관련
    DIARY_NOT_FOUND = "해당 다이어리를 찾을 수 없습니다"
    DIARY_CREATE_FAILED = "다이어리 생성에 실패했습니다"
    DIARY_UPDATE_FAILED = "다이어리 수정에 실패했습니다"
    DIARY_DELETE_FAILED = "다이어리 삭제에 실패했습니다"

    # 이미지 관련
    IMAGE_NOT_FOUND = "해당 이미지를 찾을 수 없습니다"
    IMAGE_UPLOAD_FAILED = "이미지 업로드에 실패했습니다"
    IMAGE_DELETE_FAILED = "이미지 삭제에 실패했습니다"

    # 알림 관련
    NOTIFICATION_SEND_FAILED = "알림 전송에 실패했습니다"
    NOTIFICATION_UPDATE_FAILED = "알림 설정 수정에 실패했습니다"

    # 인증 관련
    AUTH_FAILED = "인증에 실패했습니다"
    TOKEN_INVALID = "유효하지 않은 토큰입니다"

    # 일반적인 에러
    INTERNAL_ERROR = "내부 서버 오류가 발생했습니다"
    VALIDATION_ERROR = "입력 데이터 검증에 실패했습니다"

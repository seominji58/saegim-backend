"""
통합 응답 팩토리 클래스
BaseResponse와 response_utils.py의 중복을 제거하고 일관된 응답 생성을 제공
"""

import uuid
from datetime import datetime
from typing import Any, Optional, TypeVar

from fastapi import status
from fastapi.responses import JSONResponse

from app.schemas.base import BaseResponse

T = TypeVar("T")


class ResponseFactory:
    """통합 응답 생성 팩토리 클래스"""

    @staticmethod
    def success(
        data: T = None,
        message: Optional[str] = None,
        status_code: int = status.HTTP_200_OK,
    ) -> BaseResponse[T]:
        """성공 응답 생성

        Args:
            data: 응답 데이터
            message: 응답 메시지
            status_code: HTTP 상태 코드

        Returns:
            BaseResponse: 표준화된 성공 응답
        """
        return BaseResponse(
            success=True,
            data=data,
            message=message,
            timestamp=datetime.now(),
            request_id=str(uuid.uuid4()),
        )

    @staticmethod
    def error(
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code: Optional[str] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> JSONResponse:
        """에러 응답 생성 (한글 인코딩 지원)

        Args:
            message: 에러 메시지
            status_code: HTTP 상태 코드
            error_code: 에러 코드
            details: 추가 에러 세부사항

        Returns:
            JSONResponse: UTF-8 인코딩이 명시된 에러 응답
        """
        error_data = {
            "success": False,
            "data": None,
            "message": message,
            "error": {
                "code": error_code,
                "details": details,
                "timestamp": datetime.now().isoformat(),
            },
            "timestamp": datetime.now().isoformat(),
            "request_id": str(uuid.uuid4()),
        }

        return JSONResponse(
            content=error_data,
            status_code=status_code,
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "Cache-Control": "no-cache",
            },
        )

    @staticmethod
    def korean_response(
        data: Any = None,
        message: Optional[str] = None,
        status_code: int = status.HTTP_200_OK,
        success: bool = True,
    ) -> JSONResponse:
        """한글 인코딩이 보장된 응답 생성

        Args:
            data: 응답 데이터
            message: 응답 메시지
            status_code: HTTP 상태 코드
            success: 성공 여부

        Returns:
            JSONResponse: UTF-8 인코딩이 명시된 응답
        """
        response_data = {
            "success": success,
            "data": data,
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "request_id": str(uuid.uuid4()),
        }

        return JSONResponse(
            content=response_data,
            status_code=status_code,
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "Cache-Control": "no-cache",
            },
        )


class ResponseMessages:
    """표준화된 응답 메시지 상수"""

    # 성공 메시지
    CREATED_SUCCESS = "성공적으로 생성되었습니다"
    UPDATED_SUCCESS = "성공적으로 수정되었습니다"
    DELETED_SUCCESS = "성공적으로 삭제되었습니다"
    RETRIEVED_SUCCESS = "성공적으로 조회되었습니다"

    # 에러 메시지
    NOT_FOUND = "요청한 리소스를 찾을 수 없습니다"
    UNAUTHORIZED = "인증이 필요합니다"
    FORBIDDEN = "접근 권한이 없습니다"
    VALIDATION_ERROR = "입력 데이터가 올바르지 않습니다"
    INTERNAL_ERROR = "서버 내부 오류가 발생했습니다"


# 기존 response_utils.py 함수들과의 호환성을 위한 별칭
create_korean_response = ResponseFactory.korean_response
create_error_response = ResponseFactory.error

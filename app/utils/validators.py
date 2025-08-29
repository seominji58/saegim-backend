"""
공통 검증 유틸리티 함수들
"""

from typing import Optional
from uuid import UUID

from fastapi import HTTPException, status
from app.constants import FileConstants, ResponseMessages


def validate_uuid(uuid_str: str, field_name: str = "ID") -> UUID:
    """
    UUID 형식 검증 및 변환

    Args:
        uuid_str: 검증할 UUID 문자열
        field_name: 에러 메시지에 사용할 필드명

    Returns:
        검증된 UUID 객체

    Raises:
        HTTPException: UUID 형식이 올바르지 않은 경우
    """
    try:
        return UUID(uuid_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"올바른 {field_name} 형식이 아닙니다.",
        )


def validate_image_file(content_type: Optional[str], file_size: Optional[int]) -> None:
    """
    이미지 파일 검증

    Args:
        content_type: 파일의 MIME 타입
        file_size: 파일 크기 (바이트)

    Raises:
        HTTPException: 이미지 파일이 아니거나 크기가 초과된 경우
    """
    if not content_type or not content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미지 파일만 업로드할 수 있습니다.",
        )

    # 파일 크기 제한 (상수 사용)
    if file_size and file_size > FileConstants.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"파일 크기는 {FileConstants.MAX_FILE_SIZE_MB}MB 이하여야 합니다.",
        )


def validate_emotion_type(emotion: str) -> str:
    """
    감정 타입 검증

    Args:
        emotion: 검증할 감정 타입

    Returns:
        검증된 감정 타입

    Raises:
        HTTPException: 유효하지 않은 감정 타입인 경우
    """
    valid_emotions = {"happy", "sad", "angry", "peaceful", "unrest"}

    if emotion not in valid_emotions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"유효하지 않은 감정 타입입니다. 가능한 값: {', '.join(valid_emotions)}",
        )

    return emotion

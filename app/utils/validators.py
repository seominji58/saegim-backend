"""
공통 검증 유틸리티 함수들
"""

from typing import Any, Optional
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


def parse_keywords_from_json(keywords_data: Any) -> list[str]:
    """
    keywords를 JSON 문자열에서 리스트로 변환하는 공통 함수

    Args:
        keywords_data: JSON 문자열, 리스트, 또는 기타 타입

    Returns:
        파싱된 키워드 리스트
    """
    import json

    if isinstance(keywords_data, str):
        try:
            return json.loads(keywords_data) if keywords_data else []
        except json.JSONDecodeError:
            return []
    elif isinstance(keywords_data, list):
        return keywords_data
    return []


def convert_uuid_to_string(uuid_value: Any) -> str:
    """
    UUID 객체를 문자열로 변환하는 공통 함수 (스키마용)

    Args:
        uuid_value: UUID 객체 또는 문자열

    Returns:
        UUID 문자열
    """
    import uuid

    if isinstance(uuid_value, uuid.UUID):
        return str(uuid_value)
    return uuid_value


def extract_minio_object_key(url: str) -> str:
    """
    MinIO URL에서 객체 키 추출하는 공통 함수

    Args:
        url: MinIO 객체 URL

    Returns:
        추출된 객체 키 (경로)

    Examples:
        extract_minio_object_key("http://localhost:9000/saegim-images/images/2023/12/01/uuid.jpg")
        # Returns: "images/2023/12/01/uuid.jpg"
    """
    try:
        # URL에서 버킷 이름 이후의 경로를 객체 키로 추출
        parts = url.split("/")
        bucket_index = -1
        for i, part in enumerate(parts):
            if "saegim-images" in part or part == "saegim-images":
                bucket_index = i
                break

        if bucket_index != -1 and bucket_index + 1 < len(parts):
            return "/".join(parts[bucket_index + 1:])

        return ""
    except Exception:
        return ""


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

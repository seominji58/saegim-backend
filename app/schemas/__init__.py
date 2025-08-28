"""
API 스키마
"""

from .base import BaseResponse, PaginatedResponse, PaginationInfo
from .diary import DiaryListResponse, DiaryResponse

__all__ = [
    "BaseResponse",
    "PaginatedResponse",
    "PaginationInfo",
    "DiaryResponse",
    "DiaryListResponse",
]

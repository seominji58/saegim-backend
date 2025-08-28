"""
비밀번호 변경 API 라우터
"""

import logging
import re
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, validator
from sqlalchemy.orm import Session

from app.constants import AccountType
from app.core.deps import get_current_user
from app.db.database import get_session
from app.models.user import User
from app.schemas.base import BaseResponse
from app.utils.encryption import password_hasher

router = APIRouter(prefix="/change-password", tags=["change-password"])
logger = logging.getLogger(__name__)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

    @validator("new_password")
    def validate_new_password(cls, v):
        if len(v) < 9:
            raise ValueError("비밀번호는 9자 이상이어야 합니다")

        # 영문, 숫자, 특수문자 포함 검사
        has_letter = bool(re.search(r"[a-zA-Z]", v))
        has_number = bool(re.search(r"\d", v))
        has_special = bool(re.search(r'[!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>/?]', v))

        if not (has_letter and has_number and has_special):
            raise ValueError("비밀번호는 영문, 숫자, 특수문자를 모두 포함해야 합니다")

        return v


@router.post("/", response_model=BaseResponse[Dict[str, str]])
async def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
) -> BaseResponse[Dict[str, str]]:
    """
    비밀번호 변경 API (이메일 회원가입 사용자만)

    Args:
        request: 현재 비밀번호와 새 비밀번호
        current_user: 현재 로그인한 사용자
        db: 데이터베이스 세션

    Returns:
        비밀번호 변경 성공 응답
    """
    try:
        # 1. 이메일 회원가입 사용자인지 확인
        if current_user.account_type != AccountType.EMAIL.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="소셜 로그인 사용자는 비밀번호 변경이 불가능합니다.",
            )

        # 2. 현재 비밀번호 검증
        if not password_hasher.verify_password(
            request.current_password, current_user.password_hash
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="현재 비밀번호가 올바르지 않습니다."
            )

        # 3. 새 비밀번호가 현재 비밀번호와 같은지 확인
        if password_hasher.verify_password(
            request.new_password, current_user.password_hash
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="새 비밀번호는 현재 비밀번호와 달라야 합니다.",
            )

        # 4. 새 비밀번호 해싱
        new_password_hash = password_hasher.hash_password(request.new_password)

        # 5. 비밀번호 변경
        current_user.password_hash = new_password_hash

        db.commit()
        db.refresh(current_user)

        logger.info(f"비밀번호 변경 성공: {current_user.email}")

        return BaseResponse(
            data={
                "message": "비밀번호가 성공적으로 변경되었습니다.",
                "password_changed": "true",
                "requires_logout": "true",
                "redirect_to": "/login",
            },
            message="비밀번호 변경이 완료되었습니다. 보안을 위해 다시 로그인해주세요.",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"비밀번호 변경 실패: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="비밀번호 변경 중 오류가 발생했습니다.",
        )

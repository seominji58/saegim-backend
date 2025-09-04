"""
고객센터 문의 API 라우터
로그인한 사용자만 문의 접수 및 관리자 이메일 발송
"""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.core.deps import get_current_user
from app.models.user import User
from app.schemas.base import BaseResponse
from app.utils.email_service import EmailService

router = APIRouter(tags=["Support"])
logger = logging.getLogger(__name__)


# 문의 요청 모델
class SupportInquiryRequest(BaseModel):
    title: str = Field(..., min_length=3, max_length=100, description="문의 제목")
    content: str = Field(..., min_length=10, max_length=1000, description="문의 내용")
    image_attached: bool = Field(default=False, description="이미지 첨부 여부")
    image_data: str | None = Field(
        default=None, description="Base64 인코딩된 이미지 데이터"
    )
    image_filename: str | None = Field(default=None, description="이미지 파일명")
    image_type: str | None = Field(default=None, description="이미지 MIME 타입")


# 문의 응답 모델
class SupportInquiryResponse(BaseModel):
    message: str
    inquiry_id: str
    created_at: datetime


@router.post("/inquiries", response_model=BaseResponse[SupportInquiryResponse])
async def create_support_inquiry(
    request: SupportInquiryRequest,
    current_user: User = Depends(get_current_user),
) -> BaseResponse[SupportInquiryResponse]:
    """
    고객센터 문의 접수 (로그인한 사용자만)

    Args:
        request: 문의 내용
        current_user: 현재 로그인한 사용자

    Returns:
        문의 접수 결과
    """
    try:
        # 문의 ID 생성 (타임스탬프 + 사용자 ID 기반)
        inquiry_id = (
            f"INQ_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{str(current_user.id)[:8]}"
        )

        # 관리자에게 이메일 발송
        email_service = EmailService()

        # 이메일 제목
        subject = f"[새김 고객센터] {request.title}"

        # 이메일 내용 (HTML 형식으로 이미지 포함)
        html_body = f"""
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .header {{ background-color: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
        .content {{ background-color: #ffffff; padding: 20px; border: 1px solid #e9ecef; border-radius: 8px; }}
        .image-section {{ margin-top: 20px; padding: 15px; background-color: #f8f9fa; border-radius: 8px; }}
        .footer {{ margin-top: 20px; padding: 15px; background-color: #e9ecef; border-radius: 8px; font-size: 12px; color: #6c757d; }}
    </style>
</head>
<body>
    <div class="header">
        <h2>새로운 고객센터 문의가 접수되었습니다</h2>
    </div>

    <div class="content">
        <h3>문의 정보</h3>
        <p><strong>문의 ID:</strong> {inquiry_id}</p>
        <p><strong>접수 시간:</strong> {datetime.now().strftime('%Y년 %m월 %d일 %H:%M:%S')}</p>
        <p><strong>사용자:</strong> {current_user.nickname} ({current_user.email})</p>

        <h3>문의 내용</h3>
        <p><strong>제목:</strong> {request.title}</p>
        <p><strong>내용:</strong></p>
        <div style="white-space: pre-wrap; background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 10px 0;">
{request.content}
        </div>
"""

        # 이미지가 첨부된 경우
        if request.image_attached and request.image_data and request.image_filename:
            html_body += f"""
        <div class="image-section">
            <h3>첨부된 이미지</h3>
            <p><strong>파일명:</strong> {request.image_filename}</p>
            <p><strong>파일 타입:</strong> {request.image_type}</p>
            <p><strong>이미지:</strong></p>
            <img src="data:{request.image_type};base64,{request.image_data}"
                 alt="첨부된 이미지"
                 style="max-width: 100%; max-height: 400px; border: 1px solid #ddd; border-radius: 5px;" />
        </div>
"""
        else:
            html_body += """
        <div class="image-section">
            <p><strong>이미지 첨부:</strong> 없음</p>
        </div>
"""

        html_body += """
    </div>

    <div class="footer">
        <p>빠른 답변 부탁드립니다.</p>
        <p>새김 고객센터</p>
    </div>
</body>
</html>
"""

        # 일반 텍스트 버전 (이미지 첨부가 없는 경우)
        text_body = f"""
새로운 고객센터 문의가 접수되었습니다.

문의 ID: {inquiry_id}
접수 시간: {datetime.now().strftime('%Y년 %m월 %d일 %H:%M:%S')}
사용자: {current_user.nickname} ({current_user.email})

제목: {request.title}

내용:
{request.content}

이미지 첨부: {'있음' if request.image_attached else '없음'}
"""

        # 관리자 이메일로 발송
        admin_email = "alswlalswl58@naver.com"  # TODO: 환경변수로 설정

        # HTML 이메일 발송 (이미지 포함)
        await email_service.send_email(
            to_email=admin_email,
            subject=subject,
            body=html_body,
            html=True,  # HTML 이메일로 발송
        )

        logger.info(f"Support inquiry created: {inquiry_id} by user {current_user.id}")

        return BaseResponse(
            success=True,
            data=SupportInquiryResponse(
                message="문의가 성공적으로 접수되었습니다.",
                inquiry_id=inquiry_id,
                created_at=datetime.now(),
            ),
            message="문의가 성공적으로 접수되었습니다.",
        )

    except Exception as e:
        logger.error(f"Support inquiry creation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="문의 접수 중 오류가 발생했습니다.",
        )

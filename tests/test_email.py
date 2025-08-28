#!/usr/bin/env python3
"""
이메일 발송 테스트 스크립트
"""

import asyncio
import os

from app.core.config import settings
from app.utils.email_service import EmailService


async def test_email_sending():
    """이메일 발송 테스트"""
    print("=== 이메일 발송 테스트 ===")
    print(f"SendGrid API Key: {'Set' if settings.sendgrid_api_key else 'Not set'}")
    print(f"SendGrid From Email: {settings.sendgrid_from_email}")
    print(f"SMTP Username: {settings.smtp_username}")
    print()

    email_service = EmailService()

    # 테스트 이메일 주소 (실제 이메일로 변경하세요)
    test_email = os.getenv(
        "TEST_EMAIL", "test@example.com"
    )  # 환경변수에서 테스트 이메일 읽기

    try:
        print(f"테스트 이메일 발송 중: {test_email}")

        # 소셜 계정 에러 이메일 테스트
        result = await email_service.send_social_account_password_reset_error(
            to_email=test_email,
            nickname="테스트 사용자",
            provider="Google",
            error_url="http://localhost:3000/error/reset-password",
        )

        if result:
            print("✅ 이메일 발송 성공!")
        else:
            print("❌ 이메일 발송 실패!")

    except Exception as e:
        print(f"❌ 이메일 발송 중 오류: {e}")


if __name__ == "__main__":
    asyncio.run(test_email_sending())

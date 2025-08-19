"""
모델 모듈
모델 간의 순환 참조를 방지하기 위해 import 순서가 중요합니다.
"""
# 1. 기본 모델 (다른 모델에 의존성이 없는 모델)
from .user import User

# 2. User 모델에 의존성이 있는 모델들
from .oauth_token import OAuthToken
from .email_verification import EmailVerification
from .password_reset_token import PasswordResetToken

# 명시적으로 모든 모델을 노출
__all__ = [
    "User",
    "OAuthToken", 
    "EmailVerification",
    "PasswordResetToken",
]
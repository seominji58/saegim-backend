"""
OAuth 관련 스키마
"""

from pydantic import BaseModel

from app.constants import OAuthProvider


class GoogleOAuthResponse(BaseModel):
    """구글 OAuth 응답 스키마"""

    access_token: str
    refresh_token: str | None = None
    id_token: str | None = None
    token_type: str
    expires_in: int


class OAuthUserInfo(BaseModel):
    """OAuth 사용자 정보 스키마"""

    id: str
    email: str
    name: str
    picture: str | None = None
    provider: str = OAuthProvider.GOOGLE.value

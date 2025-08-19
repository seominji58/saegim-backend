"""
OAuth 인증 서비스
"""
from typing import Optional, Tuple
import json
import logging
from datetime import datetime, timezone, timedelta
import httpx
from fastapi import HTTPException, status

# 로거 설정
logger = logging.getLogger(__name__)

from app.core.config import get_settings
from app.schemas.oauth import GoogleOAuthResponse, OAuthUserInfo
from app.models.oauth_token import OAuthToken
from app.models.user import User
from sqlmodel import Session, select

settings = get_settings()


class GoogleOAuthService:
    """구글 OAuth 서비스"""

    def __init__(self):
        """초기화"""
        self.client_id = settings.google_client_id
        self.client_secret = settings.google_client_secret
        self.redirect_uri = settings.google_redirect_uri
        self.token_url = settings.google_token_uri
        self.userinfo_url = "https://www.googleapis.com/oauth2/v2/userinfo"

    async def get_access_token(self, code: str) -> GoogleOAuthResponse:
        """인증 코드로 액세스 토큰 요청

        Args:
            code: 인증 코드

        Returns:
            GoogleOAuthResponse: 토큰 응답

        Raises:
            HTTPException: 토큰 요청 실패 시
        """
        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": self.redirect_uri,
        }
        
        logger.info(f"Requesting token with redirect_uri: {self.redirect_uri}")
        logger.info(f"Client ID configured: {self.client_id[:8]}...")
        logger.info(f"Token URL: {self.token_url}")
        logger.info(f"Grant type: {data['grant_type']}")
        logger.info(f"Code length: {len(code)}")

        async with httpx.AsyncClient() as client:
            response = await client.post(self.token_url, data=data)

            if response.status_code != 200:
                error_detail = response.json() if response.content else "No error details available"
                logger.error(f"Failed to get access token. Status: {response.status_code}, Details: {error_detail}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Failed to get access token: {error_detail}",
                )

            return GoogleOAuthResponse(**response.json())

    async def get_user_info(self, access_token: str) -> OAuthUserInfo:
        """액세스 토큰으로 사용자 정보 요청

        Args:
            access_token: 액세스 토큰

        Returns:
            OAuthUserInfo: 사용자 정보

        Raises:
            HTTPException: 사용자 정보 요청 실패 시
        """
        headers = {"Authorization": f"Bearer {access_token}"}

        async with httpx.AsyncClient() as client:
            response = await client.get(self.userinfo_url, headers=headers)

            if response.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to get user info",
                )

            user_data = response.json()
            # 디버깅: 구글 API 응답 확인
            print(f"Google API Response: {user_data}")
            
            # 구글 userinfo API 응답 구조 확인 및 안전한 ID 추출
            user_id = user_data.get("sub") or user_data.get("id") or user_data.get("email")
            
            return OAuthUserInfo(
                id=user_id,  # 구글 사용자 ID (sub, id, 또는 email 폴백)
                email=user_data["email"],
                name=user_data.get("name", ""),
                picture=user_data.get("picture"),
            )

    async def process_oauth_callback(
        self, code: str, db: Session
    ) -> Tuple[User, OAuthToken]:
        """OAuth 콜백 처리

        Args:
            code: 인증 코드
            db: 데이터베이스 세션

        Returns:
            Tuple[User, OAuthToken]: (사용자, OAuth 토큰)
        """
        # 액세스 토큰 요청
        token_response = await self.get_access_token(code)
        
        # 사용자 정보 요청
        user_info = await self.get_user_info(token_response.access_token)

        # 기존 사용자 확인 또는 새로 생성
        user = db.exec(
            select(User).where(User.email == user_info.email)
        ).first()

        if not user:
            user = User(
                email=user_info.email,
                nickname=user_info.name,
                profile_image_url=user_info.picture,
                account_type="social",
                provider="google",
                provider_id=user_info.id,  # 구글 사용자 ID 설정
                is_active=True,
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        # OAuth 토큰 저장/업데이트
        oauth_token = db.exec(
            select(OAuthToken).where(
                OAuthToken.user_id == user.id,
                OAuthToken.provider == "google",
            )
        ).first()

        if oauth_token:
            oauth_token.access_token = token_response.access_token
            oauth_token.refresh_token = token_response.refresh_token
            if token_response.expires_in:
                oauth_token.expires_at = datetime.now(timezone.utc).replace(
                    microsecond=0
                ) + timedelta(seconds=token_response.expires_in)
        else:
            oauth_token = OAuthToken(
                user_id=user.id,
                provider="google",
                access_token=token_response.access_token,
                refresh_token=token_response.refresh_token,
                expires_at=datetime.now(timezone.utc).replace(microsecond=0)
                + timedelta(seconds=token_response.expires_in)
                if token_response.expires_in
                else None,
            )
            db.add(oauth_token)

        db.commit()
        db.refresh(oauth_token)

        return user, oauth_token

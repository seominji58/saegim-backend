"""
토큰 블랙리스트 서비스
JWT 토큰 무효화 및 검증
"""

import logging
from typing import Optional

from app.services.base import BaseService

logger = logging.getLogger(__name__)


class TokenBlacklistService(BaseService):
    """토큰 블랙리스트 관리 서비스"""

    def __init__(self, redis_client):
        """
        토큰 블랙리스트 서비스 초기화

        Args:
            redis_client: Redis 클라이언트 인스턴스
        """
        super().__init__()  # BaseService 초기화 (DB 없이)
        self.redis = redis_client

    async def revoke_token(self, token: str, expires_in: int) -> bool:
        """
        토큰을 블랙리스트에 추가 (무효화)

        Args:
            token: 무효화할 JWT 토큰
            expires_in: 만료 시간 (초)

        Returns:
            무효화 성공 여부
        """
        try:
            await self.redis.setex(f"revoked:{token}", expires_in, "1")
            logger.info(f"Token revoked successfully: {token[:10]}...")
            return True
        except Exception as e:
            logger.error(f"Failed to revoke token: {e}")
            return False

    async def is_token_revoked(self, token: str) -> bool:
        """
        토큰이 블랙리스트에 있는지 확인

        Args:
            token: 확인할 JWT 토큰

        Returns:
            토큰 무효화 여부 (True: 무효화됨, False: 유효함)
        """
        try:
            result = await self.redis.exists(f"revoked:{token}")
            return bool(result)
        except Exception as e:
            logger.error(f"Failed to check token revocation status: {e}")
            # Redis 연결 오류 시 안전을 위해 토큰을 무효화된 것으로 처리
            return True

    async def revoke_all_user_tokens(self, user_id: str, expires_in: int) -> bool:
        """
        특정 사용자의 모든 토큰을 무효화

        Args:
            user_id: 사용자 ID
            expires_in: 만료 시간 (초)

        Returns:
            무효화 성공 여부
        """
        try:
            await self.redis.setex(f"revoked_user:{user_id}", expires_in, "1")
            logger.info(f"All tokens revoked for user: {user_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to revoke all user tokens: {e}")
            return False

    async def is_user_tokens_revoked(self, user_id: str) -> bool:
        """
        특정 사용자의 모든 토큰이 무효화되었는지 확인

        Args:
            user_id: 사용자 ID

        Returns:
            사용자 토큰 무효화 여부
        """
        try:
            result = await self.redis.exists(f"revoked_user:{user_id}")
            return bool(result)
        except Exception as e:
            logger.error(f"Failed to check user token revocation status: {e}")
            # Redis 연결 오류 시 안전을 위해 토큰을 무효화된 것으로 처리
            return True

    async def cleanup_expired_tokens(self) -> int:
        """
        만료된 블랙리스트 토큰 정리 (Redis의 TTL 기능을 사용하므로 자동 처리)

        Returns:
            정리된 토큰 수 (Redis TTL 사용 시 항상 0 반환)
        """
        # Redis의 TTL 기능을 사용하므로 별도 정리 불필요
        logger.info("Expired tokens are automatically cleaned up by Redis TTL")
        return 0


# 전역 토큰 블랙리스트 서비스 인스턴스 (초기화는 app 시작 시 수행)
token_blacklist_service: Optional[TokenBlacklistService] = None


def get_token_blacklist_service() -> TokenBlacklistService:
    """
    토큰 블랙리스트 서비스 의존성

    Returns:
        TokenBlacklistService 인스턴스

    Raises:
        RuntimeError: 서비스가 초기화되지 않은 경우
    """
    if token_blacklist_service is None:
        raise RuntimeError(
            "TokenBlacklistService is not initialized. Please initialize it in app startup."
        )

    return token_blacklist_service


def initialize_token_blacklist_service(redis_client) -> None:
    """
    토큰 블랙리스트 서비스 초기화

    Args:
        redis_client: Redis 클라이언트 인스턴스
    """
    global token_blacklist_service
    token_blacklist_service = TokenBlacklistService(redis_client)
    logger.info("TokenBlacklistService initialized successfully")

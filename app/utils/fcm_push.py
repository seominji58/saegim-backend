"""
FCM 푸시 알림 유틸리티

Firebase Cloud Messaging을 사용하여 푸시 알림을 전송하는 유틸리티입니다.
"""

import json
from typing import Dict, Optional
import httpx
import jwt
from datetime import datetime, timedelta
import logging

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class FCMPushService:
    """FCM 푸시 알림 서비스 클래스"""

    def __init__(self):
        """FCM 푸시 알림 서비스 초기화"""
        settings = get_settings()
        self.project_id = settings.fcm_project_id
        self.service_account_json = settings.fcm_service_account_json

        if not self.project_id:
            raise ValueError("FCM_PROJECT_ID 환경변수가 설정되지 않았습니다")
        if not self.service_account_json:
            raise ValueError("FCM_SERVICE_ACCOUNT_JSON 환경변수가 설정되지 않았습니다")

        # Service Account 정보 파싱
        try:
            self.service_account = json.loads(self.service_account_json)
        except json.JSONDecodeError:
            raise ValueError("FCM_SERVICE_ACCOUNT_JSON이 유효한 JSON 형식이 아닙니다")

        # FCM API URL
        self.fcm_url = (
            f"https://fcm.googleapis.com/v1/projects/{self.project_id}/messages:send"
        )

        # Access Token 캐시
        self._access_token = None
        self._token_expires_at = None

    def _create_jwt_token(self) -> str:
        """JWT 토큰 생성"""
        now = datetime.utcnow()
        payload = {
            "iss": self.service_account["client_email"],
            "scope": "https://www.googleapis.com/auth/firebase.messaging",
            "aud": "https://oauth2.googleapis.com/token",
            "iat": now,
            "exp": now + timedelta(hours=1),
        }

        return jwt.encode(
            payload, self.service_account["private_key"], algorithm="RS256"
        )

    def _get_access_token(self) -> str:
        """OAuth 2.0 Access Token 획득"""
        # 캐시된 토큰이 유효하면 반환
        if (
            self._access_token
            and self._token_expires_at
            and datetime.utcnow() < self._token_expires_at
        ):
            return self._access_token

        # JWT 토큰 생성
        jwt_token = self._create_jwt_token()

        # Access Token 요청
        try:
            with httpx.Client() as client:
                response = client.post(
                    "https://oauth2.googleapis.com/token",
                    data={
                        "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                        "assertion": jwt_token,
                    },
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    timeout=30,
                )
                response.raise_for_status()

                token_data = response.json()
                self._access_token = token_data["access_token"]
                # 50분 후 만료로 설정 (실제는 1시간이지만 여유를 둠)
                self._token_expires_at = datetime.utcnow() + timedelta(minutes=50)

                return self._access_token

        except Exception as e:
            logger.error(f"Access Token 획득 실패: {e}")
            raise

    async def send_notification(
        self, token: str, title: str, body: str, data: Optional[Dict[str, str]] = None
    ) -> bool:
        """
        FCM 푸시 알림 전송

        Args:
            token: FCM 등록 토큰
            title: 알림 제목
            body: 알림 내용
            data: 추가 데이터 (선택사항)

        Returns:
            bool: 전송 성공 여부
        """
        try:
            # Access Token 획득
            access_token = self._get_access_token()

            # FCM 메시지 구성
            message = {
                "message": {
                    "token": token,
                    "notification": {"title": title, "body": body},
                }
            }

            # 추가 데이터가 있으면 포함
            if data:
                message["message"]["data"] = data

            # FCM API 호출
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.fcm_url,
                    json=message,
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json",
                    },
                    timeout=30,
                )

                if response.status_code == 200:
                    logger.info(f"FCM 알림 전송 성공: {title}")
                    return True
                else:
                    logger.error(
                        f"FCM 알림 전송 실패: {response.status_code} - {response.text}"
                    )
                    return False

        except Exception as e:
            logger.error(f"FCM 알림 전송 중 오류: {e}")
            return False

    async def send_diary_reminder(self, token: str, user_name: str) -> bool:
        """다이어리 작성 알림 전송"""
        return await self.send_notification(
            token=token,
            title="새김 다이어리 📝",
            body=f"{user_name}님, 오늘의 감정을 새김에 기록해보세요.",
            data={"type": "diary_reminder"},
        )

    async def send_ai_analysis_complete(self, token: str, diary_id: str) -> bool:
        """AI 감정 분석 완료 알림 전송"""
        return await self.send_notification(
            token=token,
            title="감정 분석 완료 ✨",
            body="AI가 당신의 감정을 분석했습니다. 확인해보세요!",
            data={"type": "ai_analysis", "diary_id": diary_id},
        )


# 전역 FCM 인스턴스
_fcm_instance = None


def get_fcm_service() -> FCMPushService:
    """FCM 서비스 인스턴스 반환 (싱글톤)"""
    global _fcm_instance
    if _fcm_instance is None:
        _fcm_instance = FCMPushService()
    return _fcm_instance


# 편의 함수들
async def send_push_notification(
    token: str, title: str, body: str, data: Optional[Dict[str, str]] = None
) -> bool:
    """푸시 알림 전송 함수"""
    fcm_service = get_fcm_service()
    return await fcm_service.send_notification(token, title, body, data)


async def send_diary_reminder(token: str, user_name: str) -> bool:
    """다이어리 작성 알림 전송 함수"""
    fcm_service = get_fcm_service()
    return await fcm_service.send_diary_reminder(token, user_name)


async def send_ai_analysis_complete(token: str, diary_id: str) -> bool:
    """AI 분석 완료 알림 전송 함수"""
    fcm_service = get_fcm_service()
    return await fcm_service.send_ai_analysis_complete(token, diary_id)

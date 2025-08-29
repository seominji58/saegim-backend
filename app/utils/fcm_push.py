"""
FCM 푸시 알림 유틸리티

Firebase Cloud Messaging을 사용하여 푸시 알림을 전송하는 유틸리티입니다.
"""

import json
from typing import Dict, Optional
import httpx
import jwt
from datetime import datetime, timedelta, timezone
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
            # 환경변수에서 따옴표 제거 (필요한 경우)
            json_str = self.service_account_json.strip()
            if json_str.startswith("'") and json_str.endswith("'"):
                json_str = json_str[1:-1]
            elif json_str.startswith('"') and json_str.endswith('"'):
                json_str = json_str[1:-1]

            # JSON 파싱 먼저 시도 (private key의 \n을 실제 개행으로 변환하기 전에)
            try:
                # 먼저 기본적인 이스케이프 처리만
                json_str = (
                    json_str.replace("\\\\", "\\")  # 이중 이스케이프된 \ 처리
                    .replace('\\"', '"')  # 이스케이프된 " 처리
                    .replace("\\'", "'")  # 이스케이프된 ' 처리
                    .replace("-----BEGINPRIVATEKEY-----", "-----BEGIN PRIVATE KEY-----")  # Private key 시작 태그 수정
                    .replace("-----ENDPRIVATEKEY-----", "-----END PRIVATE KEY-----")  # Private key 종료 태그 수정
                )

                # JSON 파싱 시도
                self.service_account = json.loads(json_str)

                # 파싱 성공 후 private_key의 \n을 실제 개행으로 변환
                if "private_key" in self.service_account:
                    self.service_account["private_key"] = self.service_account["private_key"].replace("\\n", "\n")

            except json.JSONDecodeError:
                # 기본 파싱이 실패하면 기존 방식으로 시도
                json_str = (
                    json_str.replace("\\\\n", "\\n")  # 이중 이스케이프된 \n 처리
                    .replace("\\n", "\n")  # 일반 \n 처리
                )
                self.service_account = json.loads(json_str)

            # 필수 필드 검증
            required_fields = ["client_email", "private_key", "project_id"]
            for field in required_fields:
                if field not in self.service_account:
                    raise ValueError(
                        f"FCM Service Account JSON에 필수 필드 '{field}'가 없습니다"
                    )

        except json.JSONDecodeError as e:
            logger.error(f"FCM_SERVICE_ACCOUNT_JSON 파싱 오류: {e}")
            logger.error(
                f"원본 JSON 내용 (처음 200자): {self.service_account_json[:200]}..."
            )
            logger.error(
                f"처리된 JSON 내용 (처음 200자): {json_str[:200] if 'json_str' in locals() else 'N/A'}..."
            )

            # 디버깅을 위해 JSON 내용의 문제가 되는 부분 찾기
            try:
                # 문제가 되는 문자 찾기
                for i, char in enumerate(json_str[:500]):
                    if ord(char) < 32 and char not in ["\n", "\r", "\t"]:
                        logger.error(
                            f"Invalid control character at position {i}: {repr(char)}"
                        )
                        break
            except Exception:
                pass

            raise ValueError("FCM_SERVICE_ACCOUNT_JSON이 유효한 JSON 형식이 아닙니다")
        except Exception as e:
            logger.error(f"FCM Service Account 초기화 오류: {e}")
            raise ValueError(f"FCM Service Account 설정 오류: {str(e)}")

        # FCM API URL
        self.fcm_url = (
            f"https://fcm.googleapis.com/v1/projects/{self.project_id}/messages:send"
        )

        # Access Token 캐시
        self._access_token = None
        self._token_expires_at = None

    def _create_jwt_token(self) -> str:
        """JWT 토큰 생성"""
        now = datetime.now(timezone.utc)
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
            and datetime.now(timezone.utc) < self._token_expires_at
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
                self._token_expires_at = datetime.now(timezone.utc) + timedelta(minutes=50)

                return self._access_token

        except Exception as e:
            logger.error(f"Access Token 획득 실패: {e}")
            raise

    async def send_notification(
        self, token: str, title: str, body: str, data: Optional[Dict[str, str]] = None
    ) -> Dict[str, any]:
        """
        FCM 푸시 알림 전송

        Args:
            token: FCM 등록 토큰
            title: 알림 제목
            body: 알림 내용
            data: 추가 데이터 (선택사항)

        Returns:
            Dict: {'success': bool, 'error_type': str|None, 'response': dict|None}
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
                    return {"success": True, "error_type": None, "response": response.json()}
                else:
                    response_data = response.json() if response.content else {}
                    error_type = self._get_error_type(response.status_code, response_data)

                    logger.error(
                        f"FCM 알림 전송 실패: {response.status_code} - {response.text}"
                    )

                    return {
                        "success": False,
                        "error_type": error_type,
                        "response": response_data
                    }

        except Exception as e:
            logger.error(f"FCM 알림 전송 중 오류: {e}")
            return {"success": False, "error_type": "EXCEPTION", "response": None}

    def _get_error_type(self, status_code: int, response_data: dict) -> str:
        """FCM 응답에서 오류 타입을 추출"""
        if status_code == 404:
            # FCM 특정 오류 코드 확인
            error_details = response_data.get("error", {}).get("details", [])
            for detail in error_details:
                if detail.get("@type") == "type.googleapis.com/google.firebase.fcm.v1.FcmError":
                    return detail.get("errorCode", "NOT_FOUND")
            return "NOT_FOUND"
        elif status_code == 400:
            return "INVALID_ARGUMENT"
        elif status_code == 401:
            return "UNAUTHENTICATED"
        elif status_code == 403:
            return "PERMISSION_DENIED"
        elif status_code == 429:
            return "QUOTA_EXCEEDED"
        elif status_code >= 500:
            return "INTERNAL_ERROR"
        else:
            return "UNKNOWN_ERROR"

    async def send_diary_reminder(self, token: str, user_name: str) -> Dict[str, any]:
        """다이어리 작성 알림 전송"""
        return await self.send_notification(
            token=token,
            title="새김 다이어리 📝",
            body=f"{user_name}님, 오늘의 감정을 새김에 기록해보세요.",
            data={"type": "diary_reminder"},
        )

    async def send_ai_analysis_complete(self, token: str, diary_id: str) -> Dict[str, any]:
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
        try:
            _fcm_instance = FCMPushService()
        except Exception as e:
            logger.error(f"FCM 서비스 초기화 실패: {e}")
            # FCM 서비스가 초기화되지 않았음을 나타내는 None 반환
            return None
    return _fcm_instance


# 편의 함수들
async def send_push_notification(
    token: str, title: str, body: str, data: Optional[Dict[str, str]] = None
) -> Dict[str, any]:
    """푸시 알림 전송 함수"""
    fcm_service = get_fcm_service()
    if fcm_service is None:
        return {"success": False, "error_type": "SERVICE_UNAVAILABLE", "response": None}
    return await fcm_service.send_notification(token, title, body, data)


async def send_diary_reminder(token: str, user_name: str) -> Dict[str, any]:
    """다이어리 작성 알림 전송 함수"""
    fcm_service = get_fcm_service()
    if fcm_service is None:
        return {"success": False, "error_type": "SERVICE_UNAVAILABLE", "response": None}
    return await fcm_service.send_diary_reminder(token, user_name)


async def send_ai_analysis_complete(token: str, diary_id: str) -> Dict[str, any]:
    """AI 분석 완료 알림 전송 함수"""
    fcm_service = get_fcm_service()
    if fcm_service is None:
        return {"success": False, "error_type": "SERVICE_UNAVAILABLE", "response": None}
    return await fcm_service.send_ai_analysis_complete(token, diary_id)

#!/usr/bin/env python3
"""
FCM 푸시 알림 데모

FCM 푸시 알림 기능의 간단한 사용 예제입니다.
"""

import asyncio
import sys
import argparse
from pathlib import Path
from dotenv import load_dotenv

from app.core.config import get_settings
from app.utils.fcm_push import (
    send_push_notification,
    send_diary_reminder,
    send_ai_analysis_complete,
)

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

load_dotenv()


async def test_fcm_notifications(test_token: str):
    """FCM 알림 테스트"""

    print("🔥 FCM 푸시 알림 테스트 시작")
    print("=" * 50)

    # 기본 푸시 알림 테스트
    print("📱 기본 푸시 알림 전송 중...")
    result = await send_push_notification(
        token=test_token,
        title="새김 테스트",
        body="FCM 푸시 알림이 정상적으로 작동합니다!",
        data={"type": "test", "timestamp": str(asyncio.get_event_loop().time())},
    )
    print(f"결과: {'✅ 성공' if result else '❌ 실패'}")

    # 다이어리 알림 테스트
    print("\n📝 다이어리 작성 알림 전송 중...")
    result = await send_diary_reminder(token=test_token, user_name="테스트 사용자")
    print(f"결과: {'✅ 성공' if result else '❌ 실패'}")

    # AI 분석 완료 알림 테스트
    print("\n🤖 AI 분석 완료 알림 전송 중...")
    result = await send_ai_analysis_complete(
        token=test_token, diary_id="test_diary_123"
    )
    print(f"결과: {'✅ 성공' if result else '❌ 실패'}")

    print("\n" + "=" * 50)
    print("🔥 FCM 푸시 알림 테스트 완료")


def main():
    """메인 함수"""
    # 명령행 인수 파싱
    parser = argparse.ArgumentParser(
        description="FCM 푸시 알림 테스트 도구",
        epilog="예시: python fcm_demo.py --token YOUR_FCM_TOKEN",
    )
    parser.add_argument(
        "--token", "-t", type=str, help="FCM 테스트 토큰 (생략 시 대화형 입력)"
    )
    args = parser.parse_args()

    # 설정 확인
    settings = get_settings()

    if not settings.fcm_project_id:
        print("❌ FCM_PROJECT_ID 환경변수가 설정되지 않았습니다")
        print("💡 .env 파일에 FCM_PROJECT_ID를 설정하세요")
        return

    if not settings.fcm_service_account_json:
        print("❌ FCM_SERVICE_ACCOUNT_JSON 환경변수가 설정되지 않았습니다")
        print("💡 .env 파일에 FCM_SERVICE_ACCOUNT_JSON을 설정하세요")
        return

    print(f"✅ FCM 프로젝트 ID: {settings.fcm_project_id}")
    print("✅ FCM Service Account: 설정됨")
    print()

    # FCM 토큰 가져오기 (명령행 인수 또는 대화형 입력)
    if args.token:
        test_token = args.token.strip()
        print(f"✅ 명령행에서 토큰 입력 받음 (길이: {len(test_token)}자)")
    else:
        print("📱 FCM 푸시 알림 테스트를 위해 테스트 토큰이 필요합니다.")
        print(
            "💡 Firebase Console > 프로젝트 > Cloud Messaging에서 테스트 토큰을 확인할 수 있습니다."
        )
        print("💡 또는 다음과 같이 명령행에서 직접 지정할 수 있습니다:")
        print("   python fcm_demo.py --token YOUR_FCM_TOKEN")
        print()

        test_token = input("🔑 FCM 테스트 토큰을 입력하세요: ").strip()

    if not test_token:
        print("❌ 토큰이 입력되지 않았습니다. 테스트를 종료합니다.")
        return

    if len(test_token) < 10:
        print("❌ 입력된 토큰이 너무 짧습니다. 올바른 FCM 토큰을 입력하세요.")
        return

    if not args.token:  # 대화형 입력인 경우만 표시
        print(f"✅ 토큰 입력 완료 (길이: {len(test_token)}자)")
    print()

    # FCM 테스트 실행
    asyncio.run(test_fcm_notifications(test_token))


if __name__ == "__main__":
    main()

"""
다이어리 API 테스트 스크립트 (캘린더용)
"""

import requests
import json
from datetime import date, timedelta

# API 기본 URL
BASE_URL = "http://localhost:8000/api/diary"

def test_get_diaries():
    """다이어리 목록 조회 테스트"""
    print("=== 다이어리 목록 조회 테스트 ===")

    # 기본 조회
    response = requests.get(f"{BASE_URL}/")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    print()

    # 페이지네이션 테스트
    response = requests.get(f"{BASE_URL}/?page=1&page_size=3")
    print(f"페이지네이션 테스트 - Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    print()

    # 감정별 필터링 테스트
    response = requests.get(f"{BASE_URL}/?emotion=happy")
    print(f"감정별 필터링 테스트 - Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    print()

def test_get_diary():
    """특정 다이어리 조회 테스트"""
    print("=== 특정 다이어리 조회 테스트 ===")

    # ID 1번 다이어리 조회
    response = requests.get(f"{BASE_URL}/1")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    print()

def test_get_calendar_diaries():
    """캘린더용 다이어리 조회 테스트"""
    print("=== 캘린더용 다이어리 조회 테스트 ===")

    # 오늘부터 30일 전까지의 다이어리 조회
    end_date = date.today()
    start_date = end_date - timedelta(days=30)

    response = requests.get(
        f"{BASE_URL}/calendar/1",
        params={
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d")
        }
    )
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    print()

def main():
    """메인 테스트 실행"""
    print("새김 다이어리 API 테스트 시작 (캘린더용)\n")

    try:
        # 1. 다이어리 목록 조회
        test_get_diaries()

        # 2. 특정 다이어리 조회
        test_get_diary()

        # 3. 캘린더용 다이어리 조회
        test_get_calendar_diaries()

        print("모든 테스트 완료!")

    except requests.exceptions.ConnectionError:
        print("❌ 서버에 연결할 수 없습니다. 서버가 실행 중인지 확인해주세요.")
        print("   서버 실행 명령: uvicorn app.main:app --reload")
    except Exception as e:
        print(f"❌ 테스트 중 오류 발생: {e}")

if __name__ == "__main__":
    main()

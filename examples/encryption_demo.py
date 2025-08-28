"""
암호화 함수 사용 예제
새김 프로젝트에서 암호화 기능을 사용하는 방법을 보여줍니다.
"""

import os
import sys

# 프로젝트 루트를 Python 경로에 추가 (import 전에 실행 필요)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ruff: noqa: E402
from app.core.security import (
    decode_access_token,
    security_service,
)
from app.utils.encryption import (
    DataEncryption,
    decrypt_data,
    encrypt_data,
    hash_password,
    verify_password,
)


def demo_password_hashing():
    """비밀번호 해싱 데모"""
    print("🔐 비밀번호 해싱 데모 (bcrypt, cost factor: 12)")
    print("-" * 50)

    # 테스트 비밀번호
    password = "my_secure_password123!"

    # 해싱
    hashed = hash_password(password)
    print(f"원본 비밀번호: {password}")
    print(f"해싱된 비밀번호: {hashed}")
    print(f"해시 길이: {len(hashed)} 문자")

    # 검증
    is_valid = verify_password(password, hashed)
    is_invalid = verify_password("wrong_password", hashed)

    print(f"올바른 비밀번호 검증: {is_valid}")
    print(f"잘못된 비밀번호 검증: {is_invalid}")
    print()


def demo_data_encryption():
    """데이터 암호화 데모"""
    print("🔒 데이터 암호화 데모 (AES-256-GCM)")
    print("-" * 40)

    # 민감한 데이터
    sensitive_data = "이것은 매우 민감한 개인정보입니다. 사용자의 일기 내용이에요."

    # 암호화
    encrypted = encrypt_data(sensitive_data)
    print(f"원본 데이터: {sensitive_data}")
    print(f"암호화된 데이터: {encrypted}")
    print(f"암호화 데이터 길이: {len(encrypted)} 문자")

    # 복호화
    decrypted = decrypt_data(encrypted)
    print(f"복호화된 데이터: {decrypted}")
    print(f"복호화 성공: {sensitive_data == decrypted}")
    print()


def demo_dict_encryption():
    """딕셔너리 필드 암호화 데모"""
    print("📋 딕셔너리 필드 암호화 데모")
    print("-" * 35)

    # 사용자 데이터 (일기 엔트리)
    diary_entry = {
        "id": 1,
        "user_id": 123,
        "title": "오늘의 기분",
        "content": "오늘은 정말 행복한 하루였다. 친구들과 만나서 즐거운 시간을 보냈고...",
        "emotion": "happy",
        "created_at": "2024-01-15T10:30:00",
        "public": False,
    }

    # 민감한 필드 정의
    sensitive_fields = ["content", "title"]

    # 암호화
    encryptor = DataEncryption()
    encrypted_entry = encryptor.encrypt_dict(diary_entry, sensitive_fields)

    print("원본 데이터:")
    for key, value in diary_entry.items():
        print(f"  {key}: {value}")

    print("\n암호화된 데이터:")
    for key, value in encrypted_entry.items():
        if key in sensitive_fields:
            print(f"  {key}: {value[:50]}... (암호화됨)")
        else:
            print(f"  {key}: {value}")

    # 복호화
    decrypted_entry = encryptor.decrypt_dict(encrypted_entry, sensitive_fields)

    print("\n복호화된 데이터:")
    for key, value in decrypted_entry.items():
        print(f"  {key}: {value}")

    # 검증
    original_match = all(
        diary_entry[key] == decrypted_entry[key] for key in diary_entry
    )
    print(f"\n복호화 검증: {original_match}")
    print()


def demo_jwt_tokens():
    """JWT 토큰 데모"""
    print("🎫 JWT 토큰 데모")
    print("-" * 20)

    # 사용자 ID
    user_id = 123

    # 토큰 생성
    tokens = security_service.create_user_tokens(user_id)

    print(f"사용자 ID: {user_id}")
    print(f"액세스 토큰: {tokens['access_token'][:50]}...")
    print(f"리프레시 토큰: {tokens['refresh_token'][:50]}...")
    print(f"토큰 타입: {tokens['token_type']}")

    # 토큰 디코딩
    try:
        access_payload = decode_access_token(tokens["access_token"])
        print("\n액세스 토큰 페이로드:")
        for key, value in access_payload.items():
            print(f"  {key}: {value}")

        # 새 액세스 토큰 생성 (리프레시)
        new_access_token = security_service.refresh_access_token(
            tokens["refresh_token"]
        )
        print(f"\n새 액세스 토큰: {new_access_token[:50]}...")

    except Exception as e:
        print(f"토큰 처리 오류: {e}")

    print()


def demo_security_integration():
    """보안 기능 통합 데모"""
    print("🛡️ 보안 기능 통합 데모")
    print("-" * 25)

    # 사용자 등록 시뮬레이션
    user_data = {
        "email": "user@example.com",
        "password": "secure_password123!",
        "profile": {
            "name": "홍길동",
            "phone": "010-1234-5678",
            "bio": "안녕하세요, 새김을 사용하고 있습니다.",
        },
    }

    print("1. 사용자 등록 데이터:")
    print(f"  이메일: {user_data['email']}")
    print(f"  비밀번호: {user_data['password']}")
    print(f"  프로필: {user_data['profile']}")

    # 비밀번호 해싱
    hashed_password = hash_password(user_data["password"])
    user_data["password"] = hashed_password

    # 민감한 데이터 암호화
    sensitive_fields = ["phone", "bio"]
    encrypted_profile = security_service.encrypt_sensitive_fields(
        user_data["profile"], sensitive_fields
    )
    user_data["profile"] = encrypted_profile

    print("\n2. 저장될 데이터 (암호화 후):")
    print(f"  이메일: {user_data['email']}")
    print(f"  비밀번호: {user_data['password'][:30]}... (해싱됨)")
    print("  프로필:")
    for key, value in user_data["profile"].items():
        if key in sensitive_fields:
            print(f"    {key}: {str(value)[:30]}... (암호화됨)")
        else:
            print(f"    {key}: {value}")

    # 로그인 시뮬레이션
    login_password = "secure_password123!"
    is_valid_login = verify_password(login_password, user_data["password"])

    print(f"\n3. 로그인 검증: {is_valid_login}")

    if is_valid_login:
        # JWT 토큰 생성
        tokens = security_service.create_user_tokens(user_id=1)

        # 프로필 데이터 복호화 (사용자에게 표시용)
        decrypted_profile = security_service.decrypt_sensitive_fields(
            user_data["profile"].copy(), sensitive_fields
        )

        print("4. 로그인 성공!")
        print(f"  액세스 토큰: {tokens['access_token'][:40]}...")
        print("  복호화된 프로필:")
        for key, value in decrypted_profile.items():
            print(f"    {key}: {value}")


def main():
    """메인 데모 실행"""
    print("🚀 새김 암호화 시스템 데모")
    print("=" * 50)
    print()

    try:
        demo_password_hashing()
        demo_data_encryption()
        demo_dict_encryption()
        demo_jwt_tokens()
        demo_security_integration()

        print("✅ 모든 데모가 성공적으로 완료되었습니다!")
        print("\n📝 사용법 요약:")
        print("- 비밀번호: hash_password(), verify_password()")
        print("- 데이터 암호화: encrypt_data(), decrypt_data()")
        print("- JWT 토큰: create_access_token(), decode_access_token()")
        print("- 통합 서비스: security_service 클래스 사용")

    except Exception as e:
        print(f"❌ 데모 실행 중 오류 발생: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()

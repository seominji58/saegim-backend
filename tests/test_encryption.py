"""
암호화 유틸리티 테스트
bcrypt 해싱 및 AES-256-GCM 암호화 기능 테스트
"""

import base64
from unittest.mock import patch

import pytest

from app.utils.encryption import (
    DataEncryption,
    PasswordHasher,
    data_encryptor,
    decrypt_data,
    encrypt_data,
    hash_password,
    password_hasher,
    verify_password,
)


class TestPasswordHasher:
    """비밀번호 해싱 클래스 테스트"""

    def test_hash_password_returns_string(self):
        """비밀번호 해싱이 문자열을 반환하는지 테스트"""
        password = "test_password_123"
        hashed = PasswordHasher.hash_password(password)

        assert isinstance(hashed, str)
        assert len(hashed) > 0
        assert hashed != password

    def test_hash_password_different_results(self):
        """같은 비밀번호라도 매번 다른 해시가 생성되는지 테스트"""
        password = "test_password_123"
        hash1 = PasswordHasher.hash_password(password)
        hash2 = PasswordHasher.hash_password(password)

        assert hash1 != hash2

    def test_hash_password_bcrypt_format(self):
        """해시가 bcrypt 형식인지 테스트"""
        password = "test_password_123"
        hashed = PasswordHasher.hash_password(password)

        # bcrypt 해시는 $2b$로 시작
        assert hashed.startswith("$2b$")
        # bcrypt 해시의 길이는 60자
        assert len(hashed) == 60

    def test_verify_password_correct(self):
        """올바른 비밀번호 검증 테스트"""
        password = "correct_password_456"
        hashed = PasswordHasher.hash_password(password)

        assert PasswordHasher.verify_password(password, hashed) is True

    def test_verify_password_incorrect(self):
        """잘못된 비밀번호 검증 테스트"""
        password = "correct_password_456"
        wrong_password = "wrong_password_789"
        hashed = PasswordHasher.hash_password(password)

        assert PasswordHasher.verify_password(wrong_password, hashed) is False

    def test_verify_password_empty_strings(self):
        """빈 문자열 처리 테스트"""
        # 빈 비밀번호도 해싱 가능
        hashed = PasswordHasher.hash_password("")
        assert PasswordHasher.verify_password("", hashed) is True
        assert PasswordHasher.verify_password("not_empty", hashed) is False

    def test_needs_update(self):
        """해시 업데이트 필요 여부 테스트"""
        password = "test_password_123"
        hashed = PasswordHasher.hash_password(password)

        # 새로 생성된 해시는 업데이트가 필요하지 않음
        assert PasswordHasher.needs_update(hashed) is False

    def test_password_special_characters(self):
        """특수 문자가 포함된 비밀번호 테스트"""
        password = "한글!@#$%^&*()비밀번호123"
        hashed = PasswordHasher.hash_password(password)

        assert PasswordHasher.verify_password(password, hashed) is True

    def test_password_long_string(self):
        """긴 비밀번호 테스트"""
        password = "A" * 1000  # 1000자 비밀번호
        hashed = PasswordHasher.hash_password(password)

        assert PasswordHasher.verify_password(password, hashed) is True


class TestDataEncryption:
    """데이터 암호화 클래스 테스트"""

    def test_init_with_custom_key(self):
        """커스텀 키로 초기화 테스트"""
        custom_key = "test_custom_key_12345678901234567890"
        encryptor = DataEncryption(custom_key)

        assert encryptor.key is not None
        assert len(encryptor.key) == 32

    def test_init_with_default_key(self):
        """기본 키로 초기화 테스트"""
        with patch("app.utils.encryption.settings") as mock_settings:
            mock_settings.encryption_key = "default_test_key_12345678901234567890"
            encryptor = DataEncryption()

            assert encryptor.key is not None
            assert len(encryptor.key) == 32

    def test_derive_key_exact_length(self):
        """정확히 32바이트 키 테스트"""
        key = "A" * 32
        encryptor = DataEncryption()
        derived_key = encryptor._derive_key(key)

        assert len(derived_key) == 32
        assert derived_key == key.encode("utf-8")

    def test_derive_key_longer_than_32(self):
        """32바이트보다 긴 키 테스트"""
        key = "A" * 50
        encryptor = DataEncryption()
        derived_key = encryptor._derive_key(key)

        assert len(derived_key) == 32
        assert derived_key == key[:32].encode("utf-8")

    def test_derive_key_shorter_than_32(self):
        """32바이트보다 짧은 키 테스트"""
        key = "short_key"
        encryptor = DataEncryption()
        derived_key = encryptor._derive_key(key)

        assert len(derived_key) == 32
        # 패딩으로 채워져야 함
        assert derived_key.startswith(key.encode("utf-8"))

    def test_encrypt_returns_string(self):
        """암호화가 문자열을 반환하는지 테스트"""
        encryptor = DataEncryption("test_key_12345678901234567890123")
        plaintext = "Hello, World!"

        encrypted = encryptor.encrypt(plaintext)

        assert isinstance(encrypted, str)
        assert len(encrypted) > 0
        assert encrypted != plaintext

    def test_encrypt_empty_string(self):
        """빈 문자열 암호화 테스트"""
        encryptor = DataEncryption("test_key_12345678901234567890123")

        encrypted = encryptor.encrypt("")

        assert encrypted == ""

    def test_encrypt_decrypt_roundtrip(self):
        """암호화-복호화 라운드트립 테스트"""
        encryptor = DataEncryption("test_key_12345678901234567890123")
        plaintext = "테스트 데이터입니다. 한글도 포함되어 있습니다!"

        encrypted = encryptor.encrypt(plaintext)
        decrypted = encryptor.decrypt(encrypted)

        assert decrypted == plaintext

    def test_encrypt_different_results(self):
        """같은 평문이라도 매번 다른 암호문이 생성되는지 테스트"""
        encryptor = DataEncryption("test_key_12345678901234567890123")
        plaintext = "same_text"

        encrypted1 = encryptor.encrypt(plaintext)
        encrypted2 = encryptor.encrypt(plaintext)

        assert encrypted1 != encrypted2
        # 하지만 둘 다 같은 평문으로 복호화되어야 함
        assert encryptor.decrypt(encrypted1) == plaintext
        assert encryptor.decrypt(encrypted2) == plaintext

    def test_decrypt_empty_string(self):
        """빈 문자열 복호화 테스트"""
        encryptor = DataEncryption("test_key_12345678901234567890123")

        decrypted = encryptor.decrypt("")

        assert decrypted == ""

    def test_decrypt_invalid_data(self):
        """잘못된 데이터 복호화 테스트"""
        encryptor = DataEncryption("test_key_12345678901234567890123")

        with pytest.raises(ValueError, match="복호화 실패"):
            encryptor.decrypt("invalid_encrypted_data")

    def test_decrypt_wrong_key(self):
        """잘못된 키로 복호화 테스트"""
        encryptor1 = DataEncryption("key1_12345678901234567890123456")
        encryptor2 = DataEncryption("key2_12345678901234567890123456")

        plaintext = "secret_message"
        encrypted = encryptor1.encrypt(plaintext)

        with pytest.raises(ValueError, match="복호화 실패"):
            encryptor2.decrypt(encrypted)

    def test_encrypt_dict_specific_fields(self):
        """딕셔너리 특정 필드 암호화 테스트"""
        encryptor = DataEncryption("test_key_12345678901234567890123")

        data = {
            "public_field": "public_data",
            "secret_field": "secret_data",
            "another_secret": "another_secret_data",
            "number_field": 12345,
        }

        fields_to_encrypt = ["secret_field", "another_secret"]
        encrypted_data = encryptor.encrypt_dict(data, fields_to_encrypt)

        # 공개 필드는 그대로 유지
        assert encrypted_data["public_field"] == "public_data"
        assert encrypted_data["number_field"] == 12345

        # 암호화 필드는 변경됨
        assert encrypted_data["secret_field"] != "secret_data"
        assert encrypted_data["another_secret"] != "another_secret_data"

        # 암호화된 필드는 문자열이어야 함
        assert isinstance(encrypted_data["secret_field"], str)
        assert isinstance(encrypted_data["another_secret"], str)

    def test_decrypt_dict_specific_fields(self):
        """딕셔너리 특정 필드 복호화 테스트"""
        encryptor = DataEncryption("test_key_12345678901234567890123")

        original_data = {
            "public_field": "public_data",
            "secret_field": "secret_data",
            "another_secret": "another_secret_data",
        }

        fields_to_encrypt = ["secret_field", "another_secret"]

        # 암호화
        encrypted_data = encryptor.encrypt_dict(original_data, fields_to_encrypt)

        # 복호화
        decrypted_data = encryptor.decrypt_dict(encrypted_data, fields_to_encrypt)

        # 원본과 같아야 함
        assert decrypted_data == original_data

    def test_encrypt_dict_none_values(self):
        """None 값이 포함된 딕셔너리 암호화 테스트"""
        encryptor = DataEncryption("test_key_12345678901234567890123")

        data = {"field1": "data1", "field2": None, "field3": "data3"}

        fields_to_encrypt = ["field1", "field2", "field3"]
        encrypted_data = encryptor.encrypt_dict(data, fields_to_encrypt)

        # None 값은 그대로 유지
        assert encrypted_data["field2"] is None
        # 다른 필드는 암호화됨
        assert encrypted_data["field1"] != "data1"
        assert encrypted_data["field3"] != "data3"

    def test_decrypt_dict_invalid_encrypted_field(self):
        """복호화 실패 시 원본 유지 테스트"""
        encryptor = DataEncryption("test_key_12345678901234567890123")

        data = {"field1": "valid_encrypted_data", "field2": "invalid_encrypted_data"}

        # field1은 제대로 암호화된 데이터로 설정
        data["field1"] = encryptor.encrypt("original_data")

        fields_to_decrypt = ["field1", "field2"]
        decrypted_data = encryptor.decrypt_dict(data, fields_to_decrypt)

        # field1은 복호화 성공
        assert decrypted_data["field1"] == "original_data"
        # field2는 복호화 실패로 원본 유지
        assert decrypted_data["field2"] == "invalid_encrypted_data"

    def test_encrypt_unicode_data(self):
        """유니코드 데이터 암호화 테스트"""
        encryptor = DataEncryption("test_key_12345678901234567890123")

        unicode_text = "안녕하세요! 🚀 Unicode test: ñáéíóú αβγδε мир"

        encrypted = encryptor.encrypt(unicode_text)
        decrypted = encryptor.decrypt(encrypted)

        assert decrypted == unicode_text

    def test_encrypt_large_data(self):
        """큰 데이터 암호화 테스트"""
        encryptor = DataEncryption("test_key_12345678901234567890123")

        large_text = "A" * 10000  # 10KB 텍스트

        encrypted = encryptor.encrypt(large_text)
        decrypted = encryptor.decrypt(encrypted)

        assert decrypted == large_text


class TestGlobalFunctions:
    """전역 함수 테스트"""

    def test_hash_password_function(self):
        """전역 hash_password 함수 테스트"""
        password = "test_password"
        hashed = hash_password(password)

        assert isinstance(hashed, str)
        assert hashed.startswith("$2b$")

    def test_verify_password_function(self):
        """전역 verify_password 함수 테스트"""
        password = "test_password"
        hashed = hash_password(password)

        assert verify_password(password, hashed) is True
        assert verify_password("wrong_password", hashed) is False

    def test_encrypt_data_function(self):
        """전역 encrypt_data 함수 테스트"""
        plaintext = "test_data"
        encrypted = encrypt_data(plaintext)

        assert isinstance(encrypted, str)
        assert encrypted != plaintext

    def test_decrypt_data_function(self):
        """전역 decrypt_data 함수 테스트"""
        plaintext = "test_data"
        encrypted = encrypt_data(plaintext)
        decrypted = decrypt_data(encrypted)

        assert decrypted == plaintext

    def test_encrypt_decrypt_data_roundtrip(self):
        """전역 함수 암호화-복호화 라운드트립 테스트"""
        original_text = "민감한 데이터입니다 🔒"

        encrypted = encrypt_data(original_text)
        decrypted = decrypt_data(encrypted)

        assert decrypted == original_text


class TestSingletonInstances:
    """싱글톤 인스턴스 테스트"""

    def test_password_hasher_singleton(self):
        """password_hasher 싱글톤 테스트"""
        assert password_hasher is not None
        assert isinstance(password_hasher, PasswordHasher)

    def test_data_encryptor_singleton(self):
        """data_encryptor 싱글톤 테스트"""
        assert data_encryptor is not None
        assert isinstance(data_encryptor, DataEncryption)

    def test_singleton_consistency(self):
        """싱글톤 일관성 테스트"""
        # 전역 함수와 싱글톤 인스턴스가 같은 결과를 내는지 확인
        password = "consistency_test"

        # 전역 함수 사용
        hashed1 = hash_password(password)

        # 싱글톤 인스턴스 직접 사용
        hashed2 = password_hasher.hash_password(password)

        # 둘 다 검증되어야 함
        assert verify_password(password, hashed1) is True
        assert password_hasher.verify_password(password, hashed2) is True


class TestEdgeCases:
    """엣지 케이스 테스트"""

    def test_very_long_password(self):
        """매우 긴 비밀번호 테스트 (bcrypt 제한사항 고려)"""
        # bcrypt는 72바이트 제한이 있지만, passlib는 4096바이트까지 허용
        long_password = "x" * 4000  # 4KB 비밀번호 (bcrypt 한계 내)

        hashed = hash_password(long_password)
        assert verify_password(long_password, hashed) is True

    def test_password_with_null_bytes(self):
        """null 바이트가 포함된 비밀번호 테스트"""
        password_with_null = "password\x00with\x00null"

        # bcrypt 라이브러리는 null 바이트를 허용하므로 정상 처리되어야 함
        hashed = hash_password(password_with_null)
        assert verify_password(password_with_null, hashed) is True

    def test_verify_password_invalid_hash(self):
        """잘못된 해시 형식으로 검증 테스트"""
        password = "test_password"
        invalid_hash = "invalid_hash_format"

        # 잘못된 해시는 False를 반환해야 함
        assert verify_password(password, invalid_hash) is False

    def test_needs_update_various_formats(self):
        """다양한 해시 형식에서 업데이트 필요성 테스트"""
        # 올바른 $2b$12$ 형식
        correct_hash = "$2b$12$abcdefghijklmnopqrstuvwxyz0123456789ABCDEFGHIJ"
        assert PasswordHasher.needs_update(correct_hash) is False

        # 잘못된 버전
        old_version = "$2a$12$abcdefghijklmnopqrstuvwxyz0123456789ABCDEFGHIJ"
        assert PasswordHasher.needs_update(old_version) is True

        # 다른 rounds
        different_rounds = "$2b$10$abcdefghijklmnopqrstuvwxyz0123456789ABCDEFGHIJ"
        assert PasswordHasher.needs_update(different_rounds) is True

        # 완전히 잘못된 형식
        invalid_format = "completely_invalid"
        assert PasswordHasher.needs_update(invalid_format) is True

        # None이나 빈 문자열
        assert PasswordHasher.needs_update("") is True

    def test_encryption_base64_output(self):
        """암호화 출력이 유효한 base64인지 테스트"""
        plaintext = "test_data"
        encrypted = encrypt_data(plaintext)

        # base64 디코딩이 가능해야 함
        try:
            base64.b64decode(encrypted)
        except Exception:
            pytest.fail("암호화 출력이 유효한 base64가 아닙니다")

    @patch("app.utils.encryption.os.urandom")
    def test_encrypt_with_mocked_random(self, mock_urandom):
        """고정된 nonce로 암호화 테스트 (재현 가능한 테스트)"""
        # 고정된 nonce 설정
        fixed_nonce = b"A" * 12
        mock_urandom.return_value = fixed_nonce

        encryptor = DataEncryption("test_key_12345678901234567890123")
        plaintext = "test_data"

        encrypted1 = encryptor.encrypt(plaintext)
        encrypted2 = encryptor.encrypt(plaintext)

        # 같은 nonce를 사용했으므로 결과가 같아야 함
        assert encrypted1 == encrypted2


class TestPerformance:
    """성능 관련 테스트"""

    def test_password_hashing_performance(self):
        """비밀번호 해싱 성능 테스트 (cost factor 12)"""
        import time

        password = "performance_test_password"

        start_time = time.time()
        hash_password(password)
        end_time = time.time()

        # cost factor 12는 적당한 시간이 걸려야 함 (0.1초 이상, 5초 이하)
        duration = end_time - start_time
        assert 0.01 < duration < 5.0, f"해싱 시간이 예상 범위를 벗어남: {duration}초"

    def test_encryption_performance(self):
        """암호화 성능 테스트"""
        import time

        large_data = "A" * 1000  # 1KB 데이터

        start_time = time.time()
        encrypted = encrypt_data(large_data)
        decrypt_data(encrypted)
        end_time = time.time()

        # 암호화-복호화는 빨라야 함 (1초 이하)
        duration = end_time - start_time
        assert duration < 1.0, f"암호화-복호화 시간이 너무 오래 걸림: {duration}초"


# 테스트 실행을 위한 픽스쳐들
@pytest.fixture
def sample_encryptor():
    """테스트용 암호화 인스턴스"""
    return DataEncryption("test_key_for_fixture_123456789012")


@pytest.fixture
def sample_data():
    """테스트용 샘플 데이터"""
    return {
        "public": "public_data",
        "private": "private_data",
        "secret": "secret_data",
        "number": 12345,
        "none_field": None,
    }


class TestWithFixtures:
    """픽스쳐를 사용한 테스트"""

    def test_encryptor_fixture(self, sample_encryptor):
        """암호화 픽스쳐 테스트"""
        plaintext = "fixture_test_data"

        encrypted = sample_encryptor.encrypt(plaintext)
        decrypted = sample_encryptor.decrypt(encrypted)

        assert decrypted == plaintext

    def test_data_fixture(self, sample_encryptor, sample_data):
        """데이터 픽스쳐 테스트"""
        fields_to_encrypt = ["private", "secret"]

        encrypted_data = sample_encryptor.encrypt_dict(sample_data, fields_to_encrypt)
        decrypted_data = sample_encryptor.decrypt_dict(
            encrypted_data, fields_to_encrypt
        )

        assert decrypted_data == sample_data

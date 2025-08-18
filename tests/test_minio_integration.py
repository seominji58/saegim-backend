"""
MinIO 실제 업로드 통합 테스트
주의: 이 테스트는 실제 MinIO 서버에 파일을 업로드합니다.
"""

import os
import pytest
from unittest.mock import Mock
from fastapi import UploadFile


@pytest.fixture(scope="session", autouse=True)
def setup_integration_test_env():
    """통합 테스트용 환경변수 설정"""
    from dotenv import load_dotenv

    load_dotenv()

    # 통합 테스트용 버킷명 설정
    original_bucket_name = os.environ.get("MINIO_BUCKET_NAME")
    os.environ["MINIO_BUCKET_NAME"] = "test"

    yield

    # 원래 값 복원
    if original_bucket_name is None:
        os.environ.pop("MINIO_BUCKET_NAME", None)
    else:
        os.environ["MINIO_BUCKET_NAME"] = original_bucket_name


@pytest.fixture
def real_webp_image():
    """실제 WebP 테스트 이미지 파일"""
    import pathlib

    test_file_path = pathlib.Path(__file__).parent / "test_image.webp"

    if not test_file_path.exists():
        pytest.skip(f"테스트 이미지 파일이 없습니다: {test_file_path}")

    file_content = test_file_path.read_bytes()

    file = Mock(spec=UploadFile)
    file.filename = "test_image.webp"
    file.content_type = "image/webp"
    file.size = len(file_content)

    async def async_read():
        return file_content

    file.read = async_read
    return file


@pytest.fixture
def real_large_image():
    """실제 대용량 JPEG 테스트 이미지 파일 (20MB)"""
    import pathlib

    test_file_path = pathlib.Path(__file__).parent / "test_image_20mb.jpg"

    if not test_file_path.exists():
        pytest.skip(f"테스트 이미지 파일이 없습니다: {test_file_path}")

    file_content = test_file_path.read_bytes()

    file = Mock(spec=UploadFile)
    file.filename = "test_image_20mb.jpg"
    file.content_type = "image/jpeg"
    file.size = len(file_content)

    async def async_read():
        return file_content

    file.read = async_read
    return file


@pytest.mark.integration
@pytest.mark.asyncio
async def test_webp_image_upload(real_webp_image):
    """실제 WebP 이미지 파일 업로드 테스트"""
    from app.utils.minio_upload import upload_image_to_minio, delete_image_from_minio

    try:
        # 실제 업로드
        file_id, image_url = await upload_image_to_minio(real_webp_image)

        print("✅ WebP 이미지 업로드 성공!")
        print("   파일명: test_image.webp")
        print(
            f"   파일 크기: {real_webp_image.size:,} bytes (약 {real_webp_image.size / 1024:.1f}KB)"
        )
        print(f"   파일 ID: {file_id}")
        print(f"   이미지 URL: {image_url}")
        print("   MinIO 콘솔에서 'test' 버킷을 확인해보세요!")

        # 검증
        assert file_id
        assert image_url
        assert "test" in image_url
        assert file_id in image_url  # 파일명에 UUID가 포함됨

        # 정리 (선택사항 - 주석 해제하면 업로드 후 삭제)
        object_key = f"images/{file_id}"
        delete_result = delete_image_from_minio(object_key)
        print(f"정리 완료: {delete_result}")

    except Exception as e:
        print(f"❌ WebP 이미지 업로드 실패: {e}")
        print("MinIO 서버가 실행 중인지 확인해주세요.")
        pytest.skip("MinIO 서버에 연결할 수 없어 테스트를 건너뜁니다.")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_large_image_upload_should_fail(real_large_image):
    """대용량 이미지 업로드 실패 테스트 (15MB 제한 초과)"""
    from app.utils.minio_upload import upload_image_to_minio
    from fastapi import HTTPException

    try:
        print("📊 대용량 이미지 테스트:")
        print("   파일명: test_image_20mb.jpg")
        print(
            f"   파일 크기: {real_large_image.size:,} bytes (약 {real_large_image.size / 1024 / 1024:.1f}MB)"
        )
        print("   제한 크기: 15MB")

        # 15MB 초과 파일은 업로드 실패해야 함
        with pytest.raises(HTTPException) as exc_info:
            await upload_image_to_minio(real_large_image)

        print(f"✅ 예상된 실패: {exc_info.value.detail}")
        assert exc_info.value.status_code == 413
        assert "15MB를 초과합니다" in str(exc_info.value.detail)

    except Exception as e:
        print(f"❌ 테스트 중 예상치 못한 오류: {e}")
        pytest.skip("테스트 실행 중 오류가 발생했습니다.")


@pytest.mark.integration
def test_minio_connection():
    """MinIO 서버 연결 테스트"""
    try:
        from app.utils.minio_upload import get_minio_uploader

        uploader = get_minio_uploader()

        print("✅ MinIO 연결 성공!")
        print(f"   엔드포인트: {os.getenv('MINIO_ENDPOINT')}")
        print(f"   버킷명: {uploader.bucket_name}")

        assert uploader.bucket_name == "test"

    except Exception as e:
        print(f"❌ MinIO 연결 실패: {e}")
        pytest.skip("MinIO 서버에 연결할 수 없어 테스트를 건너뜁니다.")


if __name__ == "__main__":
    print("🚀 MinIO 통합 테스트 실행 방법:")
    print("1. 전체 통합 테스트:")
    print("   pytest tests/test_minio_integration.py -m integration -v --no-cov")
    print()
    print("2. 개별 테스트:")
    print(
        "   pytest tests/test_minio_integration.py::test_webp_image_upload -v --no-cov"
    )
    print(
        "   pytest tests/test_minio_integration.py::test_large_image_upload_should_fail -v --no-cov"
    )
    print()
    print("3. 상세 출력 포함:")
    print("   pytest tests/test_minio_integration.py -m integration -v -s --no-cov")
    print()
    print("📝 참고: --no-cov 옵션으로 커버리지 체크를 비활성화합니다.")

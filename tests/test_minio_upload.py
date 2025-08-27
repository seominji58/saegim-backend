"""
MinIO 이미지 업로드 유틸리티 테스트 (환경변수 사용)
"""

import os
import uuid
import pytest
from unittest.mock import patch, MagicMock
from fastapi import HTTPException


@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    """테스트용 환경변수 설정 - 무조건 test 버킷 사용"""
    # .env 파일 로드
    from dotenv import load_dotenv

    load_dotenv()

    # 버킷명을 무조건 테스트용으로 설정
    original_bucket_name = os.environ.get("MINIO_BUCKET_NAME")
    os.environ["MINIO_BUCKET_NAME"] = "test"

    # 테스트가 test 버킷을 사용하는지 확인
    assert os.environ["MINIO_BUCKET_NAME"] == "test", (
        "테스트는 반드시 'test' 버킷을 사용해야 합니다"
    )

    # 설정 캐시 클리어 (lru_cache 때문에 캐시된 설정을 클리어)
    from app.core.config import get_settings

    get_settings.cache_clear()

    # 전역 MinIO 업로더 인스턴스 초기화 (싱글톤 패턴 재설정)
    import app.utils.minio_upload

    app.utils.minio_upload._minio_uploader = None

    yield

    # 버킷명 원래 값 복원
    if original_bucket_name is None:
        os.environ.pop("MINIO_BUCKET_NAME", None)
    else:
        os.environ["MINIO_BUCKET_NAME"] = original_bucket_name

    # 설정 캐시 다시 클리어 (원래 설정으로 복원)
    get_settings.cache_clear()
    # 전역 업로더 인스턴스도 다시 초기화
    app.utils.minio_upload._minio_uploader = None


@pytest.fixture
def sample_image_file():
    """테스트용 이미지 파일 Mock 생성"""
    from unittest.mock import Mock
    from fastapi import UploadFile

    file_content = b"fake image content for testing"
    file = Mock(spec=UploadFile)
    file.filename = "test_image.jpg"
    file.content_type = "image/jpeg"
    file.size = len(file_content)

    # async read 메서드 Mock
    async def async_read():
        return file_content

    file.read = async_read
    return file


@pytest.fixture
def large_image_file():
    """크기가 큰 테스트용 이미지 파일 Mock"""
    from unittest.mock import Mock
    from fastapi import UploadFile

    file = Mock(spec=UploadFile)
    file.filename = "large_image.jpg"
    file.content_type = "image/jpeg"
    file.size = 20 * 1024 * 1024  # 20MB (15MB 초과)

    async def async_read():
        return b"x" * file.size

    file.read = async_read
    return file


@pytest.fixture
def invalid_type_file():
    """허용되지 않는 파일 형식 Mock"""
    from unittest.mock import Mock
    from fastapi import UploadFile

    file = Mock(spec=UploadFile)
    file.filename = "document.txt"
    file.content_type = "text/plain"
    file.size = 1024

    async def async_read():
        return b"text content"

    file.read = async_read
    return file


class TestMinIOUploader:
    """MinIOUploader 클래스 테스트"""

    @pytest.fixture(autouse=True)
    def reset_minio_uploader(self):
        """각 테스트마다 MinIO 업로더 인스턴스 초기화"""
        import app.utils.minio_upload

        app.utils.minio_upload._minio_uploader = None

        # 설정 캐시도 클리어
        from app.core.config import get_settings

        get_settings.cache_clear()

        yield

        # 테스트 후 다시 초기화
        app.utils.minio_upload._minio_uploader = None

    @pytest.fixture
    def mock_minio_client(self):
        """MinIO 클라이언트 Mock"""
        with patch("app.utils.minio_upload.Minio") as mock:
            client = MagicMock()
            mock.return_value = client
            client.bucket_exists.return_value = True
            yield client

    def test_bucket_name_is_test(self, mock_minio_client):
        """테스트 환경에서 버킷명이 'test'인지 확인"""
        from app.utils.minio_upload import MinIOUploader

        uploader = MinIOUploader()

        # 테스트 환경에서는 반드시 'test' 버킷을 사용해야 함
        assert uploader.bucket_name == "test", (
            f"테스트는 'test' 버킷을 사용해야 하지만 '{uploader.bucket_name}'을 사용 중입니다"
        )
        assert os.environ.get("MINIO_BUCKET_NAME") == "test", (
            "환경변수 MINIO_BUCKET_NAME이 'test'로 설정되지 않았습니다"
        )

    def test_init_success(self, mock_minio_client):
        """MinIOUploader 초기화 성공 테스트"""
        from app.utils.minio_upload import MinIOUploader

        uploader = MinIOUploader()

        assert uploader.bucket_name == "test"
        mock_minio_client.bucket_exists.assert_called_once_with("test")

    def test_init_bucket_creation(self, mock_minio_client):
        """버킷이 없을 때 생성 테스트"""
        mock_minio_client.bucket_exists.return_value = False

        from app.utils.minio_upload import MinIOUploader

        MinIOUploader()

        mock_minio_client.make_bucket.assert_called_once_with("test")

    def test_init_client_error(self):
        """MinIO 클라이언트 초기화 실패 테스트"""
        with patch(
            "app.utils.minio_upload.Minio", side_effect=Exception("Connection error")
        ):
            from app.utils.minio_upload import MinIOUploader

            with pytest.raises(HTTPException) as exc_info:
                MinIOUploader()

            assert exc_info.value.status_code == 500
            assert "MinIO 스토리지 서비스 초기화에 실패했습니다" in str(
                exc_info.value.detail
            )

    def test_init_bucket_error(self, mock_minio_client):
        """버킷 설정 실패 테스트"""
        mock_minio_client.bucket_exists.side_effect = Exception("Bucket error")

        from app.utils.minio_upload import MinIOUploader

        with pytest.raises(HTTPException) as exc_info:
            MinIOUploader()

        assert exc_info.value.status_code == 500
        assert "MinIO 스토리지 서비스 초기화에 실패했습니다" in str(
            exc_info.value.detail
        )

    @pytest.mark.asyncio
    async def test_upload_image_success(self, mock_minio_client, sample_image_file):
        """이미지 업로드 성공 테스트"""
        from app.utils.minio_upload import MinIOUploader

        uploader = MinIOUploader()

        with (
            patch.object(
                uploader,
                "_generate_object_key",
                return_value="images/2024/01/15/test.jpg",
            ),
            patch.object(
                uploader,
                "_generate_image_url",
                return_value="http://localhost:9000/test/images/2024/01/15/test.jpg",
            ),
        ):
            file_id, image_url = await uploader.upload_image(sample_image_file)

            # UUID 형식 확인
            assert uuid.UUID(file_id)  # 유효한 UUID인지 확인
            assert image_url == "http://localhost:9000/test/images/2024/01/15/test.jpg"

            # MinIO 클라이언트 호출 확인
            mock_minio_client.put_object.assert_called_once()

    @pytest.mark.asyncio
    async def test_upload_image_validation_error(
        self, mock_minio_client, large_image_file
    ):
        """파일 검증 실패 테스트 (크기 초과)"""
        from app.utils.minio_upload import MinIOUploader

        uploader = MinIOUploader()

        with pytest.raises(HTTPException) as exc_info:
            await uploader.upload_image(large_image_file)

        assert exc_info.value.status_code == 413
        assert "파일 크기가 15MB를 초과합니다" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_upload_image_type_error(self, mock_minio_client, invalid_type_file):
        """파일 형식 검증 실패 테스트"""
        from app.utils.minio_upload import MinIOUploader

        uploader = MinIOUploader()

        with pytest.raises(HTTPException) as exc_info:
            await uploader.upload_image(invalid_type_file)

        assert exc_info.value.status_code == 400
        assert "허용되지 않는 파일 형식입니다" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_upload_image_minio_error(self, mock_minio_client, sample_image_file):
        """MinIO 업로드 실패 테스트"""
        from app.utils.minio_upload import MinIOUploader

        uploader = MinIOUploader()
        mock_minio_client.put_object.side_effect = Exception("Upload failed")

        with pytest.raises(HTTPException) as exc_info:
            await uploader.upload_image(sample_image_file)

        assert exc_info.value.status_code == 500
        assert "이미지 업로드 중 오류가 발생했습니다" in str(exc_info.value.detail)

    def test_delete_image_success(self, mock_minio_client):
        """이미지 삭제 성공 테스트"""
        from app.utils.minio_upload import MinIOUploader

        uploader = MinIOUploader()
        object_key = "images/2024/01/15/test.jpg"

        result = uploader.delete_image(object_key)

        assert result is True
        mock_minio_client.remove_object.assert_called_once_with("test", object_key)

    def test_delete_image_error(self, mock_minio_client):
        """이미지 삭제 실패 테스트"""
        from app.utils.minio_upload import MinIOUploader

        uploader = MinIOUploader()
        mock_minio_client.remove_object.side_effect = Exception("Delete failed")

        result = uploader.delete_image("test/image.jpg")

        assert result is False

    def test_get_image_url(self, mock_minio_client):
        """이미지 URL 생성 테스트"""
        from app.utils.minio_upload import MinIOUploader
        import os

        uploader = MinIOUploader()
        object_key = "images/2024/01/15/test.jpg"

        url = uploader.get_image_url(object_key)

        # .env에서 읽은 실제 엔드포인트 사용, 버킷명만 test
        expected_endpoint = os.getenv("MINIO_ENDPOINT")
        expected_secure = os.getenv("MINIO_SECURE", "false").lower() == "true"
        protocol = "https" if expected_secure else "http"
        expected_url = f"{protocol}://{expected_endpoint}/test/{object_key}"

        assert url == expected_url

    @pytest.mark.parametrize(
        "content_type",
        [
            "image/jpeg",
            "image/jpg",
            "image/png",
            "image/gif",
            "image/webp",
            "image/bmp",
        ],
    )
    def test_validate_file_allowed_types(self, mock_minio_client, content_type):
        """허용된 파일 형식들 테스트"""
        from app.utils.minio_upload import MinIOUploader
        from unittest.mock import Mock
        from fastapi import UploadFile

        uploader = MinIOUploader()

        file = Mock(spec=UploadFile)
        file.content_type = content_type
        file.size = 1024  # 1KB

        # 예외가 발생하지 않아야 함
        uploader._validate_file(file)

    def test_generate_object_key(self, mock_minio_client):
        """객체 키 생성 테스트"""
        from app.utils.minio_upload import MinIOUploader

        uploader = MinIOUploader()
        file_id = "test-uuid"
        filename = "test_image.JPG"

        with patch("app.utils.minio_upload.datetime") as mock_datetime:
            mock_datetime.now.return_value.strftime.return_value = "2024/01/15"

            object_key = uploader._generate_object_key(file_id, filename)

            assert object_key == "images/2024/01/15/test-uuid.jpg"

    def test_generate_image_url_http(self, mock_minio_client):
        """HTTP 이미지 URL 생성 테스트"""
        from app.utils.minio_upload import MinIOUploader
        import os

        uploader = MinIOUploader()
        object_key = "images/2024/01/15/test.jpg"

        url = uploader._generate_image_url(object_key)

        # .env에서 읽은 실제 엔드포인트 사용, MINIO_SECURE=false이므로 HTTP
        expected_endpoint = os.getenv("MINIO_ENDPOINT")
        expected_secure = os.getenv("MINIO_SECURE", "false").lower() == "true"
        protocol = "https" if expected_secure else "http"
        expected_url = f"{protocol}://{expected_endpoint}/test/{object_key}"

        assert url == expected_url

    def test_generate_thumbnail_object_key(self, mock_minio_client):
        """썸네일 객체 키 생성 테스트"""
        from app.utils.minio_upload import MinIOUploader

        uploader = MinIOUploader()
        file_id = "test-uuid"
        filename = "test_image.PNG"

        with patch("app.utils.minio_upload.datetime") as mock_datetime:
            mock_datetime.now.return_value.strftime.return_value = "2024/01/15"

            object_key = uploader._generate_thumbnail_object_key(file_id, filename)

            assert object_key == "thumbnails/2024/01/15/test-uuid_thumb.jpg"

    def test_create_thumbnail(self, mock_minio_client):
        """썸네일 생성 테스트"""
        from app.utils.minio_upload import MinIOUploader
        from PIL import Image as PILImage
        import io

        uploader = MinIOUploader()
        
        # 간단한 테스트 이미지 생성
        test_image = PILImage.new('RGB', (300, 300), color='red')
        img_buffer = io.BytesIO()
        test_image.save(img_buffer, format='JPEG')
        img_data = img_buffer.getvalue()

        # 썸네일 생성
        thumbnail_data = uploader._create_thumbnail(img_data, size=(150, 150))

        # 썸네일이 생성되었는지 확인
        assert thumbnail_data
        assert len(thumbnail_data) > 0
        
        # 썸네일 이미지를 다시 열어서 크기 확인
        thumbnail_image = PILImage.open(io.BytesIO(thumbnail_data))
        assert thumbnail_image.size[0] <= 150
        assert thumbnail_image.size[1] <= 150

    @pytest.mark.asyncio
    async def test_upload_image_with_thumbnail_success(self, mock_minio_client, sample_image_file):
        """이미지와 썸네일 업로드 성공 테스트"""
        from app.utils.minio_upload import MinIOUploader
        from PIL import Image as PILImage
        import io

        uploader = MinIOUploader()

        # 실제 이미지 데이터를 Mock 파일에 추가
        test_image = PILImage.new('RGB', (300, 300), color='blue')
        img_buffer = io.BytesIO()
        test_image.save(img_buffer, format='JPEG')
        
        # async read 메서드로 수정
        async def async_read():
            return img_buffer.getvalue()
        
        sample_image_file.read = async_read

        with (
            patch.object(
                uploader,
                "_generate_object_key",
                return_value="images/2024/01/15/test.jpg",
            ),
            patch.object(
                uploader,
                "_generate_thumbnail_object_key", 
                return_value="thumbnails/2024/01/15/test_thumb.jpg",
            ),
            patch.object(
                uploader,
                "_generate_image_url",
                side_effect=[
                    "http://localhost:9000/test/images/2024/01/15/test.jpg",
                    "http://localhost:9000/test/thumbnails/2024/01/15/test_thumb.jpg"
                ]
            ),
        ):
            file_id, original_url, thumbnail_url = await uploader.upload_image_with_thumbnail(sample_image_file)

            # UUID 형식 확인
            assert uuid.UUID(file_id)  # 유효한 UUID인지 확인
            assert original_url == "http://localhost:9000/test/images/2024/01/15/test.jpg"
            assert thumbnail_url == "http://localhost:9000/test/thumbnails/2024/01/15/test_thumb.jpg"

            # MinIO 클라이언트가 두 번 호출되었는지 확인 (원본 + 썸네일)
            assert mock_minio_client.put_object.call_count == 2


class TestConvenienceFunctions:
    """편의 함수들 테스트"""

    @pytest.mark.asyncio
    async def test_upload_image_to_minio(self, sample_image_file):
        """upload_image_to_minio 편의 함수 테스트"""
        with patch("app.utils.minio_upload.get_minio_uploader") as mock_get_uploader:
            from app.utils.minio_upload import upload_image_to_minio

            mock_uploader = MagicMock()
            mock_get_uploader.return_value = mock_uploader

            # async 메서드를 올바르게 Mock
            async def mock_upload(file):
                return ("file-id", "http://test.com/image.jpg")

            mock_uploader.upload_image = mock_upload

            result = await upload_image_to_minio(sample_image_file)

            assert result == ("file-id", "http://test.com/image.jpg")
            # async 함수는 호출 확인이 다름

    @pytest.mark.asyncio
    async def test_upload_image_with_thumbnail_to_minio(self, sample_image_file):
        """upload_image_with_thumbnail_to_minio 편의 함수 테스트"""
        with patch("app.utils.minio_upload.get_minio_uploader") as mock_get_uploader:
            from app.utils.minio_upload import upload_image_with_thumbnail_to_minio

            mock_uploader = MagicMock()
            mock_get_uploader.return_value = mock_uploader

            # async 메서드를 올바르게 Mock
            async def mock_upload_with_thumbnail(file, thumbnail_size=(150, 150)):
                return ("file-id", "http://test.com/image.jpg", "http://test.com/thumbnail.jpg")

            mock_uploader.upload_image_with_thumbnail = mock_upload_with_thumbnail

            result = await upload_image_with_thumbnail_to_minio(sample_image_file)

            assert result == ("file-id", "http://test.com/image.jpg", "http://test.com/thumbnail.jpg")
            assert len(result) == 3  # 파일 ID, 원본 URL, 썸네일 URL

    def test_delete_image_from_minio(self):
        """delete_image_from_minio 편의 함수 테스트"""
        with patch("app.utils.minio_upload.get_minio_uploader") as mock_get_uploader:
            from app.utils.minio_upload import delete_image_from_minio

            mock_uploader = MagicMock()
            mock_get_uploader.return_value = mock_uploader
            mock_uploader.delete_image.return_value = True

            object_key = "test/image.jpg"
            result = delete_image_from_minio(object_key)

            assert result is True
            mock_uploader.delete_image.assert_called_once_with(object_key)

    def test_get_image_url_from_minio(self):
        """get_image_url_from_minio 편의 함수 테스트"""
        with patch("app.utils.minio_upload.get_minio_uploader") as mock_get_uploader:
            from app.utils.minio_upload import get_image_url_from_minio

            mock_uploader = MagicMock()
            mock_get_uploader.return_value = mock_uploader
            mock_uploader.get_image_url.return_value = "http://test.com/image.jpg"

            object_key = "test/image.jpg"
            result = get_image_url_from_minio(object_key)

            assert result == "http://test.com/image.jpg"
            mock_uploader.get_image_url.assert_called_once_with(object_key)


class TestSingletonPattern:
    """싱글톤 패턴 테스트"""

    def test_get_minio_uploader_singleton(self):
        """싱글톤 패턴 확인 테스트"""
        from app.utils.minio_upload import get_minio_uploader

        # 전역 변수 초기화
        import app.utils.minio_upload

        app.utils.minio_upload._minio_uploader = None

        with patch("app.utils.minio_upload.MinIOUploader") as mock_class:
            mock_instance = MagicMock()
            mock_class.return_value = mock_instance

            # 첫 번째 호출
            uploader1 = get_minio_uploader()
            # 두 번째 호출
            uploader2 = get_minio_uploader()

            # 같은 인스턴스여야 함
            assert uploader1 is uploader2
            # 생성자는 한 번만 호출되어야 함
            mock_class.assert_called_once()


class TestEdgeCases:
    """엣지 케이스 테스트"""

    @pytest.fixture
    def mock_minio_client(self):
        """MinIO 클라이언트 Mock"""
        with patch("app.utils.minio_upload.Minio") as mock:
            client = MagicMock()
            mock.return_value = client
            client.bucket_exists.return_value = True
            yield client

    def test_file_without_size(self, mock_minio_client):
        """파일 크기 정보가 없는 경우 테스트"""
        from app.utils.minio_upload import MinIOUploader
        from unittest.mock import Mock
        from fastapi import UploadFile

        uploader = MinIOUploader()

        file = Mock(spec=UploadFile)
        file.size = None
        file.content_type = "image/jpeg"

        # 크기 검증을 건너뛰어야 함 (예외 발생 안함)
        uploader._validate_file(file)

    def test_filename_without_extension(self, mock_minio_client):
        """확장자가 없는 파일명 테스트"""
        from app.utils.minio_upload import MinIOUploader

        uploader = MinIOUploader()
        object_key = uploader._generate_object_key("test-id", "filename_without_ext")

        # 확장자가 없어도 처리되어야 함
        assert "test-id" in object_key
        assert object_key.endswith("test-id")

    def test_uppercase_extension(self, mock_minio_client):
        """대문자 확장자 테스트"""
        from app.utils.minio_upload import MinIOUploader

        uploader = MinIOUploader()
        object_key = uploader._generate_object_key("test-id", "image.PNG")

        # 소문자로 변환되어야 함
        assert object_key.endswith(".png")

    @pytest.mark.asyncio
    async def test_empty_file_content(self, mock_minio_client):
        """빈 파일 내용 테스트"""
        from app.utils.minio_upload import MinIOUploader
        from unittest.mock import Mock
        from fastapi import UploadFile

        uploader = MinIOUploader()

        file = Mock(spec=UploadFile)
        file.filename = "empty.jpg"
        file.content_type = "image/jpeg"
        file.size = 0

        async def empty_read():
            return b""

        file.read = empty_read

        with (
            patch.object(
                uploader,
                "_generate_object_key",
                return_value="images/2024/01/15/empty.jpg",
            ),
            patch.object(
                uploader,
                "_generate_image_url",
                return_value="http://localhost:9000/test/images/2024/01/15/empty.jpg",
            ),
        ):
            file_id, image_url = await uploader.upload_image(file)

            assert file_id
            assert image_url == "http://localhost:9000/test/images/2024/01/15/empty.jpg"

            # 빈 내용도 업로드되어야 함
            mock_minio_client.put_object.assert_called_once()
            call_args = mock_minio_client.put_object.call_args
            assert call_args[1]["length"] == 0


class TestIntegration:
    """통합 테스트"""

    @pytest.mark.asyncio
    async def test_full_upload_flow(self, sample_image_file):
        """전체 업로드 플로우 테스트"""
        from app.utils.minio_upload import upload_image_to_minio

        with (
            patch("app.utils.minio_upload.Minio") as mock_minio,
            patch("app.utils.minio_upload.get_minio_uploader") as mock_get_uploader,
        ):
            # MinIO 클라이언트 Mock
            client = MagicMock()
            mock_minio.return_value = client
            client.bucket_exists.return_value = True

            # 업로더 Mock
            mock_uploader = MagicMock()
            mock_get_uploader.return_value = mock_uploader

            async def mock_upload(file):
                return (
                    str(uuid.uuid4()),
                    f"http://localhost:9000/test/images/2024/01/15/{file.filename}",
                )

            mock_uploader.upload_image = mock_upload

            # 업로드 실행
            file_id, image_url = await upload_image_to_minio(sample_image_file)

            # 결과 검증
            assert uuid.UUID(file_id)  # 유효한 UUID
            assert image_url.startswith("http://localhost:9000/test/images/")
            assert image_url.endswith(".jpg")

            # Mock 업로더를 사용했으므로 실제 MinIO 클라이언트는 호출되지 않음
            # 대신 결과 검증으로 충분함
            assert file_id  # 파일 ID가 생성됨
            assert "test_image.jpg" in image_url  # 파일명이 포함됨

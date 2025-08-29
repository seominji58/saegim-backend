"""
DiaryService 단위 테스트
"""

import uuid
from datetime import UTC, date, datetime, timedelta
from unittest.mock import Mock, patch

import pytest
from sqlalchemy.orm import Session

from app.constants import SortOrder
from app.models.diary import DiaryEntry
from app.schemas.diary import DiaryCreateRequest, DiaryUpdateRequest
from app.services.diary import DiaryService


class TestDiaryService:
    """DiaryService 단위 테스트"""

    @pytest.fixture
    def mock_db(self):
        """Mock 데이터베이스 세션"""
        return Mock(spec=Session)

    @pytest.fixture
    def diary_service(self, mock_db):
        """DiaryService 인스턴스"""
        return DiaryService(mock_db)

    @pytest.fixture
    def sample_user_id(self):
        """테스트용 사용자 ID"""
        return uuid.uuid4()

    @pytest.fixture
    def sample_diary(self, sample_user_id):
        """테스트용 다이어리 엔트리"""
        return DiaryEntry(
            id=uuid.uuid4(),
            title="테스트 다이어리",
            content="테스트 내용입니다.",
            user_emotion="happy",
            ai_emotion="happy",
            ai_emotion_confidence=0.9,
            user_id=sample_user_id,
            ai_generated_text="AI가 생성한 텍스트입니다.",
            is_public=False,
            keywords=["테스트", "다이어리"],
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
            deleted_at=None,
        )

    @pytest.fixture
    def sample_create_request(self):
        """테스트용 다이어리 생성 요청"""
        return DiaryCreateRequest(
            title="새로운 다이어리",
            content="새로운 내용입니다.",
            user_emotion="peaceful",
            ai_emotion="peaceful",
            ai_emotion_confidence=0.8,
            ai_generated_text="AI 생성 텍스트",
            keywords=["새로운", "평온"],
            is_public=True,
        )

    @pytest.fixture
    def sample_update_request(self):
        """테스트용 다이어리 수정 요청"""
        return DiaryUpdateRequest(
            title="수정된 제목",
            content="수정된 내용",
            user_emotion="sad",
            is_public=True,
            keywords=["수정", "슬픔"],
        )

    def test_get_diaries_basic(self, diary_service, mock_db, sample_diary):
        """기본 다이어리 목록 조회 테스트"""
        # Mock 설정
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [sample_diary]
        mock_db.execute.return_value = mock_result

        # 카운트 쿼리용 Mock 설정
        mock_count_result = Mock()
        mock_count_result.scalar_one.return_value = 1
        mock_db.execute.side_effect = [mock_count_result, mock_result]

        # 테스트 실행
        diaries, total_count = diary_service.get_diaries()

        # 검증
        assert len(diaries) == 1
        assert diaries[0] == sample_diary
        assert total_count == 1
        assert mock_db.execute.call_count == 2

    def test_get_diaries_with_user_filter(self, diary_service, mock_db, sample_user_id):
        """사용자 ID 필터링 테스트"""
        # Mock 설정
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        # 카운트 쿼리용 Mock 설정
        mock_count_result = Mock()
        mock_count_result.scalar_one.return_value = 0
        mock_db.execute.side_effect = [mock_count_result, mock_result]

        # 테스트 실행
        diaries, total_count = diary_service.get_diaries(user_id=sample_user_id)

        # 검증
        assert len(diaries) == 0
        assert total_count == 0
        assert mock_db.execute.call_count == 2

    def test_get_diaries_with_pagination(self, diary_service, mock_db):
        """페이지네이션 테스트"""
        # Mock 설정
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        # 카운트 쿼리용 Mock 설정
        mock_count_result = Mock()
        mock_count_result.scalar_one.return_value = 100
        mock_db.execute.side_effect = [mock_count_result, mock_result]

        # 테스트 실행 (2페이지, 페이지 크기 10)
        diaries, total_count = diary_service.get_diaries(page=2, page_size=10)

        # 검증
        assert total_count == 100
        assert mock_db.execute.call_count == 2

    def test_get_diaries_with_filters(self, diary_service, mock_db):
        """필터링 조건 테스트"""
        # Mock 설정
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        # 카운트 쿼리용 Mock 설정
        mock_count_result = Mock()
        mock_count_result.scalar_one.return_value = 0
        mock_db.execute.side_effect = [mock_count_result, mock_result]

        # 테스트 실행 (모든 필터 적용)
        start_date = date.today() - timedelta(days=7)
        end_date = date.today()

        diaries, total_count = diary_service.get_diaries(
            searchTerm="검색어",
            emotion="happy",
            is_public=True,
            start_date=start_date,
            end_date=end_date,
            sort_order=SortOrder.ASC.value,
        )

        # 검증
        assert len(diaries) == 0
        assert total_count == 0

    def test_get_diary_by_id_found(self, diary_service, mock_db, sample_diary):
        """ID로 다이어리 조회 성공 테스트"""
        # Mock 설정
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_diary
        mock_db.execute.return_value = mock_result

        # 테스트 실행
        result = diary_service.get_diary_by_id(str(sample_diary.id))

        # 검증
        assert result == sample_diary
        mock_db.execute.assert_called_once()

    def test_get_diary_by_id_not_found(self, diary_service, mock_db):
        """ID로 다이어리 조회 실패 테스트"""
        # Mock 설정
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        # 테스트 실행
        result = diary_service.get_diary_by_id("nonexistent-id")

        # 검증
        assert result is None
        mock_db.execute.assert_called_once()

    def test_get_diary_by_id_with_user_filter(
        self, diary_service, mock_db, sample_diary, sample_user_id
    ):
        """사용자 ID 필터와 함께 다이어리 조회 테스트"""
        # Mock 설정
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = sample_diary
        mock_db.execute.return_value = mock_result

        # 테스트 실행
        result = diary_service.get_diary_by_id(str(sample_diary.id), sample_user_id)

        # 검증
        assert result == sample_diary
        mock_db.execute.assert_called_once()

    def test_get_diaries_by_date_range(
        self, diary_service, mock_db, sample_user_id, sample_diary
    ):
        """날짜 범위로 다이어리 조회 테스트"""
        # Mock 설정
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = [sample_diary]
        mock_db.execute.return_value = mock_result

        # 테스트 실행
        start_date = date.today() - timedelta(days=7)
        end_date = date.today()
        result = diary_service.get_diaries_by_date_range(
            sample_user_id, start_date, end_date
        )

        # 검증
        assert len(result) == 1
        assert result[0] == sample_diary
        mock_db.execute.assert_called_once()

    def test_create_diary(
        self, diary_service, mock_db, sample_user_id, sample_create_request
    ):
        """다이어리 생성 테스트"""
        # Mock 설정
        created_diary = DiaryEntry(
            id=uuid.uuid4(),
            title=sample_create_request.title,
            content=sample_create_request.content,
            user_emotion=sample_create_request.user_emotion,
            ai_emotion=sample_create_request.ai_emotion,
            ai_emotion_confidence=sample_create_request.ai_emotion_confidence,
            user_id=sample_user_id,
            ai_generated_text=sample_create_request.ai_generated_text,
            is_public=sample_create_request.is_public,
            keywords=sample_create_request.keywords,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        mock_db.add = Mock()
        mock_db.commit = Mock()
        mock_db.refresh = Mock()

        # 테스트 실행
        result = diary_service.create_diary(sample_create_request, sample_user_id)

        # 검증
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

        # 생성된 다이어리의 속성들이 올바르게 설정되었는지 확인
        args = mock_db.add.call_args[0][0]
        assert args.user_id == sample_user_id
        assert args.title == sample_create_request.title
        assert args.content == sample_create_request.content
        assert args.user_emotion == sample_create_request.user_emotion
        assert args.ai_emotion == sample_create_request.ai_emotion
        assert args.is_public == sample_create_request.is_public
        assert args.keywords == sample_create_request.keywords

    def test_update_diary_success(
        self, diary_service, mock_db, sample_diary, sample_update_request
    ):
        """다이어리 수정 성공 테스트"""
        # get_diary_by_id Mock 설정
        with patch.object(diary_service, "get_diary_by_id", return_value=sample_diary):
            # DB Mock 설정
            mock_db.add = Mock()
            mock_db.commit = Mock()
            mock_db.refresh = Mock()

            # 테스트 실행
            result = diary_service.update_diary(
                str(sample_diary.id), sample_update_request
            )

            # 검증
            assert result == sample_diary
            assert sample_diary.title == sample_update_request.title
            assert sample_diary.content == sample_update_request.content
            assert sample_diary.user_emotion == sample_update_request.user_emotion
            assert sample_diary.is_public == sample_update_request.is_public
            assert sample_diary.keywords == sample_update_request.keywords

            mock_db.add.assert_called_once_with(sample_diary)
            mock_db.commit.assert_called_once()
            mock_db.refresh.assert_called_once_with(sample_diary)

    def test_update_diary_not_found(self, diary_service, sample_update_request):
        """다이어리 수정 실패 테스트 (다이어리 없음)"""
        # get_diary_by_id Mock 설정 (None 반환)
        with patch.object(diary_service, "get_diary_by_id", return_value=None):
            # 테스트 실행
            result = diary_service.update_diary("nonexistent-id", sample_update_request)

            # 검증
            assert result is None

    def test_delete_diary_success(
        self, diary_service, mock_db, sample_diary, sample_user_id
    ):
        """다이어리 삭제 성공 테스트"""
        # get_diary_by_id Mock 설정
        with patch.object(diary_service, "get_diary_by_id", return_value=sample_diary):
            # 이미지 쿼리 Mock 설정 (이미지 없는 경우)
            mock_image_result = Mock()
            mock_image_result.scalars.return_value.all.return_value = []
            mock_db.execute.return_value = mock_image_result

            # database_transaction_handler Mock 설정
            with patch(
                "app.services.diary.database_transaction_handler"
            ) as mock_handler:
                mock_handler.__enter__ = Mock(return_value=None)
                mock_handler.__exit__ = Mock(return_value=None)

                # DB Mock 설정
                mock_db.add = Mock()
                mock_db.commit = Mock()

                # 테스트 실행
                result = diary_service.delete_diary(
                    str(sample_diary.id), sample_user_id
                )

                # 검증
                assert result is True
                assert sample_diary.deleted_at is not None
                mock_db.add.assert_called_once_with(sample_diary)
                mock_db.commit.assert_called_once()

    def test_delete_diary_not_found(self, diary_service, sample_user_id):
        """다이어리 삭제 실패 테스트 (다이어리 없음)"""
        # get_diary_by_id Mock 설정 (None 반환)
        with patch.object(diary_service, "get_diary_by_id", return_value=None):
            # 테스트 실행
            result = diary_service.delete_diary("nonexistent-id", sample_user_id)

            # 검증
            assert result is False

    def test_delete_diary_basic_logic(self, diary_service, mock_db, sample_user_id):
        """다이어리 삭제 기본 로직 테스트 (이미지 처리 없이)"""
        # 테스트용 다이어리 생성
        test_diary = DiaryEntry(
            id=uuid.uuid4(),
            title="삭제 테스트 다이어리",
            content="삭제될 다이어리",
            user_id=sample_user_id,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

        # get_diary_by_id Mock 설정
        with patch.object(diary_service, "get_diary_by_id", return_value=test_diary):
            # 이미지 없는 경우 Mock 설정
            mock_image_result = Mock()
            mock_image_result.scalars.return_value.all.return_value = []
            mock_db.execute.return_value = mock_image_result

            # database_transaction_handler를 context manager로 Mock
            class MockTransactionHandler:
                def __enter__(self):
                    return self

                def __exit__(self, exc_type, exc_val, exc_tb):
                    return None

            with patch(
                "app.utils.error_handlers.database_transaction_handler"
            ) as mock_handler:
                mock_handler.return_value = MockTransactionHandler()

                # DB Mock 설정
                mock_db.add = Mock()
                mock_db.commit = Mock()

                # 테스트 실행
                result = diary_service.delete_diary(str(test_diary.id), sample_user_id)

                # 검증
                assert result is True
                assert test_diary.deleted_at is not None
                mock_db.add.assert_called_once_with(test_diary)
                mock_db.commit.assert_called_once()

    def test_get_diaries_search_filter(self, diary_service, mock_db):
        """검색어 필터링 테스트"""
        # Mock 설정
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        # 카운트 쿼리용 Mock 설정
        mock_count_result = Mock()
        mock_count_result.scalar_one.return_value = 0
        mock_db.execute.side_effect = [mock_count_result, mock_result]

        # 테스트 실행
        diaries, total_count = diary_service.get_diaries(searchTerm="테스트")

        # 검증
        assert len(diaries) == 0
        assert total_count == 0

    def test_get_diaries_emotion_filter(self, diary_service, mock_db):
        """감정 필터링 테스트"""
        # Mock 설정
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        # 카운트 쿼리용 Mock 설정
        mock_count_result = Mock()
        mock_count_result.scalar_one.return_value = 0
        mock_db.execute.side_effect = [mock_count_result, mock_result]

        # 테스트 실행
        diaries, total_count = diary_service.get_diaries(emotion="happy")

        # 검증
        assert len(diaries) == 0
        assert total_count == 0

    def test_get_diaries_sort_order(self, diary_service, mock_db):
        """정렬 순서 테스트"""
        # Mock 설정
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        # 카운트 쿼리용 Mock 설정
        mock_count_result = Mock()
        mock_count_result.scalar_one.return_value = 0
        mock_db.execute.side_effect = [mock_count_result, mock_result]

        # ASC 정렬 테스트
        diaries, _ = diary_service.get_diaries(sort_order=SortOrder.ASC.value)
        assert len(diaries) == 0

        # DESC 정렬 테스트 (기본값)
        mock_db.execute.side_effect = [mock_count_result, mock_result]
        diaries, _ = diary_service.get_diaries(sort_order=SortOrder.DESC.value)
        assert len(diaries) == 0

    def test_update_diary_partial_update(self, diary_service, mock_db, sample_diary):
        """부분 업데이트 테스트"""
        # 부분 업데이트 요청 (제목만 수정)
        partial_update = DiaryUpdateRequest(title="새로운 제목만")

        # get_diary_by_id Mock 설정
        with patch.object(diary_service, "get_diary_by_id", return_value=sample_diary):
            # 원본 값들 저장
            original_content = sample_diary.content
            original_emotion = sample_diary.user_emotion

            # DB Mock 설정
            mock_db.add = Mock()
            mock_db.commit = Mock()
            mock_db.refresh = Mock()

            # 테스트 실행
            result = diary_service.update_diary(str(sample_diary.id), partial_update)

            # 검증 - 수정된 필드만 변경되고 나머지는 유지
            assert result == sample_diary
            assert sample_diary.title == "새로운 제목만"  # 변경됨
            assert sample_diary.content == original_content  # 유지됨
            assert sample_diary.user_emotion == original_emotion  # 유지됨

    def test_create_diary_fields_mapping(
        self, diary_service, mock_db, sample_user_id, sample_create_request
    ):
        """다이어리 생성 시 필드 매핑 테스트"""
        # DB Mock 설정
        mock_db.add = Mock()
        mock_db.commit = Mock()
        mock_db.refresh = Mock()

        # 테스트 실행
        result = diary_service.create_diary(sample_create_request, sample_user_id)

        # add 호출에서 전달된 DiaryEntry 검증
        added_diary = mock_db.add.call_args[0][0]
        assert isinstance(added_diary, DiaryEntry)
        assert added_diary.user_id == sample_user_id
        assert added_diary.title == sample_create_request.title
        assert added_diary.content == sample_create_request.content
        assert added_diary.user_emotion == sample_create_request.user_emotion
        assert added_diary.ai_emotion == sample_create_request.ai_emotion
        assert (
            added_diary.ai_emotion_confidence
            == sample_create_request.ai_emotion_confidence
        )
        assert added_diary.ai_generated_text == sample_create_request.ai_generated_text
        assert added_diary.is_public == sample_create_request.is_public
        assert added_diary.keywords == sample_create_request.keywords
        assert added_diary.created_at is not None
        assert added_diary.updated_at is not None


class TestDiaryServiceEdgeCases:
    """DiaryService 엣지 케이스 테스트"""

    @pytest.fixture
    def mock_db(self):
        """Mock 데이터베이스 세션"""
        return Mock(spec=Session)

    @pytest.fixture
    def diary_service(self, mock_db):
        """DiaryService 인스턴스"""
        return DiaryService(mock_db)

    @pytest.fixture
    def sample_user_id(self):
        """테스트용 사용자 ID"""
        return uuid.uuid4()

    def test_get_diaries_empty_search_term(self, diary_service, mock_db):
        """빈 검색어 처리 테스트"""
        # 빈 문자열과 None 모두 테스트
        for search_term in ["", None]:
            # Mock 설정 (각 루프마다 새로 설정)
            mock_result = Mock()
            mock_result.scalars.return_value.all.return_value = []

            # 카운트 쿼리용 Mock 설정
            mock_count_result = Mock()
            mock_count_result.scalar_one.return_value = 0
            mock_db.execute.side_effect = [mock_count_result, mock_result]

            diaries, _ = diary_service.get_diaries(searchTerm=search_term)
            # 빈 검색어는 필터가 적용되지 않아야 함
            assert isinstance(diaries, list)

    def test_get_diaries_invalid_page(self, diary_service, mock_db):
        """잘못된 페이지 번호 처리 테스트"""
        # Mock 설정
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        # 카운트 쿼리용 Mock 설정
        mock_count_result = Mock()
        mock_count_result.scalar_one.return_value = 0
        mock_db.execute.side_effect = [mock_count_result, mock_result]

        # 페이지 0 테스트 (음수 오프셋이 되므로)
        diaries, _ = diary_service.get_diaries(page=0)
        assert isinstance(diaries, list)

    def test_get_diaries_date_range_edge_cases(
        self, diary_service, mock_db, sample_user_id
    ):
        """날짜 범위 엣지 케이스 테스트"""
        # Mock 설정
        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        # 같은 날짜로 범위 설정
        today = date.today()
        result = diary_service.get_diaries_by_date_range(sample_user_id, today, today)

        # 검증
        assert isinstance(result, list)
        mock_db.execute.assert_called_once()

    def test_create_diary_with_none_values(
        self, diary_service, mock_db, sample_user_id
    ):
        """None 값이 포함된 다이어리 생성 테스트"""
        # None 값이 포함된 요청
        create_request = DiaryCreateRequest(
            title=None,
            content="내용만 있는 다이어리",
            user_emotion=None,
            ai_emotion=None,
            ai_emotion_confidence=None,
            ai_generated_text=None,
            keywords=None,
            is_public=False,
        )

        # DB Mock 설정
        mock_db.add = Mock()
        mock_db.commit = Mock()
        mock_db.refresh = Mock()

        # 테스트 실행
        result = diary_service.create_diary(create_request, sample_user_id)

        # 검증 - None 값들이 올바르게 처리되는지 확인
        added_diary = mock_db.add.call_args[0][0]
        assert added_diary.title is None
        assert added_diary.content == "내용만 있는 다이어리"
        assert added_diary.user_emotion is None
        assert added_diary.ai_emotion is None
        assert added_diary.ai_emotion_confidence is None
        assert added_diary.ai_generated_text is None
        assert added_diary.keywords is None
        assert added_diary.is_public is False

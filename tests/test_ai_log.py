"""
AI 텍스트 생성 서비스 테스트
"""

import uuid
from unittest.mock import AsyncMock, Mock, patch

import pytest
from sqlalchemy.orm import Session

from app.schemas.create_diary import CreateDiaryRequest
from app.services.ai_log import AIService, ContentLength, EmotionType, WritingStyle


class TestAIService:
    """AIService 테스트"""

    @pytest.fixture
    def mock_db(self):
        """Mock 데이터베이스 세션"""
        db = Mock(spec=Session)
        db.execute.return_value.scalars.return_value.all.return_value = []
        db.add = Mock()
        db.commit = Mock()
        return db

    @pytest.fixture
    def ai_service(self, mock_db):
        """AIService 인스턴스"""
        return AIService(mock_db)

    @pytest.fixture
    def sample_request(self):
        """테스트용 요청 데이터"""
        return CreateDiaryRequest(
            prompt="오늘 카페에서 좋은 시간을 보냈다",
            style="poem",
            length="medium",
            emotion="행복",
            regeneration_count=1,
            session_id=None,
        )

    @pytest.fixture
    def mock_openai_response(self):
        """Mock OpenAI 응답"""
        return {
            "id": "test-id",
            "content": "테스트 응답 내용",
            "model": "gpt-4",
            "created": 1234567890,
            "usage": {"completion_tokens": 50, "prompt_tokens": 30, "total_tokens": 80},
            "finish_reason": "stop",
            "role": "assistant",
        }

    @pytest.mark.asyncio
    async def test_generate_ai_text_success(
        self, ai_service, mock_db, sample_request, mock_openai_response
    ):
        """AI 텍스트 생성 성공 테스트"""
        user_id = str(uuid.uuid4())

        # Mock OpenAI 클라이언트
        with patch("app.services.ai_log.get_openai_client") as mock_get_client:
            mock_client = Mock()
            mock_get_client.return_value = mock_client

            # 감정 분석 응답
            emotion_response = mock_openai_response.copy()
            emotion_response["content"] = "행복"
            # AsyncMock을 사용하여 async 함수 올바르게 모킹
            mock_client.async_chat_completion = AsyncMock(
                side_effect=[
                    emotion_response,  # 감정 분석
                    {
                        **mock_openai_response,
                        "content": '["카페", "시간", "오늘", "좋은", "순간"]',
                    },  # 키워드 추출
                    {
                        **mock_openai_response,
                        "content": "카페 한 구석 작은 테이블에서\n따뜻한 커피 향이 마음을 적신다\n오늘 같은 평범한 일상이\n얼마나 소중한지 깨닫는다",
                    },  # 글귀 생성
                ]
            )

            # 테스트 실행
            result = await ai_service.generate_ai_text(user_id, sample_request)

            # 결과 검증
            assert "ai_generated_text" in result
            assert "ai_emotion" in result
            assert "ai_emotion_confidence" in result
            assert "keywords" in result
            assert "session_id" in result

            assert result["ai_emotion"] == "행복"
            assert isinstance(result["keywords"], list)
            assert len(result["keywords"]) <= 5

            # 데이터베이스 저장 검증
            assert mock_db.add.call_count == 2  # generate + keywords 로그
            assert mock_db.commit.called

    @pytest.mark.asyncio
    async def test_generate_complete_analysis(self, ai_service, mock_openai_response):
        """통합 AI 분석 테스트"""
        with patch("app.utils.openai_utils.get_openai_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_get_client.return_value = mock_client

            # 올바른 JSON 응답 모킹
            emotion_response = mock_openai_response.copy()
            emotion_response[
                "content"
            ] = '{"emotion": "행복", "keywords": ["좋음", "하루"], "generated_text": "오늘은 정말 좋은 하루였습니다."}'
            mock_client.async_chat_completion = AsyncMock(return_value=emotion_response)

            result = await ai_service._generate_complete_analysis(
                "오늘은 정말 좋은 하루였습니다.", "happy"
            )

            assert result["emotion"] == "행복"
            assert result["confidence"] == 0.9
            assert result["keywords"] == ["좋음", "하루"]
            assert result["generated_text"] == "오늘은 정말 좋은 하루였습니다."
            assert result["tokens_used"] == 80

    @pytest.mark.skip(reason="메서드가 존재하지 않음 - 통합 테스트로 대체")
    async def test_extract_keywords_professional(
        self, ai_service, mock_openai_response
    ):
        """전문적인 키워드 추출 테스트 - 스킵됨"""
        pass

    @pytest.mark.skip(reason="메서드가 존재하지 않음 - 통합 테스트로 대체")
    async def test_extract_keywords_json_parse_error(
        self, ai_service, mock_openai_response
    ):
        """키워드 추출 JSON 파싱 오류 테스트 - 스킵됨"""
        pass

    @pytest.mark.skip(reason="메서드가 존재하지 않음 - 통합 테스트로 대체")
    async def test_generate_quote_professional_poem_style(
        self, ai_service, mock_openai_response
    ):
        """시 스타일 글귀 생성 테스트 - 스킵됨"""
        pass

    @pytest.mark.skip(reason="메서드가 존재하지 않음 - 통합 테스트로 대체")
    async def test_generate_quote_professional_short_story_style(
        self, ai_service, mock_openai_response
    ):
        """단편글 스타일 글귀 생성 테스트 - 스킵됨"""
        pass

    @pytest.mark.skip(reason="메서드가 존재하지 않음")
    def test_extract_keywords_fallback(self, ai_service):
        """폴백 키워드 추출 테스트 - 스킵됨"""
        pass

    @pytest.mark.asyncio
    async def test_openai_api_error_handling(self, ai_service, mock_db, sample_request):
        """OpenAI API 오류 처리 테스트"""
        user_id = str(uuid.uuid4())

        with patch("app.services.ai_log.get_openai_client") as mock_get_client:
            mock_client = Mock()
            mock_get_client.return_value = mock_client
            mock_client.async_chat_completion = AsyncMock(
                side_effect=Exception("API Error")
            )

            # 테스트 실행 - fallback 동작으로 예외가 발생하지 않고 기본값 반환
            result = await ai_service.generate_ai_text(user_id, sample_request)

            # fallback 값들이 반환되는지 확인
            assert result["ai_emotion"] == "평온"  # 기본 감정값
            assert len(result["keywords"]) > 0  # fallback 키워드 추출
            assert (
                "기본" in result["ai_generated_text"]
                or "위로" in result["ai_generated_text"]
            )  # fallback 텍스트

    @pytest.mark.asyncio
    async def test_session_regeneration_count(
        self, ai_service, mock_db, sample_request
    ):
        """세션 재생성 카운트 테스트"""
        user_id = str(uuid.uuid4())
        session_id = str(uuid.uuid4())
        sample_request.session_id = session_id

        # 기존 로그가 2개 있다고 가정
        existing_logs = [Mock(), Mock()]
        mock_db.execute.return_value.scalars.return_value.all.return_value = (
            existing_logs
        )

        with patch("app.services.ai_log.get_openai_client") as mock_get_client:
            mock_client = Mock()
            mock_get_client.return_value = mock_client
            mock_client.async_chat_completion = AsyncMock(
                side_effect=[
                    {"content": "행복", "usage": {"total_tokens": 50}},
                    {"content": '["테스트"]', "usage": {"total_tokens": 30}},
                    {"content": "테스트 글귀", "usage": {"total_tokens": 80}},
                ]
            )

            await ai_service.generate_ai_text(user_id, sample_request)

            # regeneration_count가 3이어야 함 (기존 2개 + 현재 1개)
            call_args = mock_db.add.call_args_list
            request_log = call_args[0][0][0]  # 첫 번째 add 호출의 첫 번째 인자
            assert request_log.regeneration_count == 3

    def test_emotion_type_enum(self):
        """감정 타입 열거형 테스트"""
        assert EmotionType.HAPPINESS == "행복"
        assert EmotionType.SADNESS == "슬픔"
        assert EmotionType.ANGER == "화남"
        assert EmotionType.PEACE == "평온"
        assert EmotionType.UNREST == "불안"

    def test_writing_style_enum(self):
        """글쓰기 스타일 열거형 테스트"""
        assert WritingStyle.POEM == "poem"
        assert WritingStyle.SHORT_STORY == "short_story"

    def test_content_length_enum(self):
        """콘텐츠 길이 열거형 테스트"""
        assert ContentLength.SHORT == "short"
        assert ContentLength.MEDIUM == "medium"
        assert ContentLength.LONG == "long"


class TestAIServiceIntegration:
    """AIService 통합 테스트"""

    @pytest.mark.asyncio
    async def test_complete_ai_generation_flow(self):
        """완전한 AI 생성 플로우 테스트"""
        # Mock 데이터베이스
        mock_db = Mock(spec=Session)
        mock_db.execute.return_value.scalars.return_value.all.return_value = []
        mock_db.add = Mock()
        mock_db.commit = Mock()

        ai_service = AIService(mock_db)
        user_id = str(uuid.uuid4())

        request = CreateDiaryRequest(
            prompt="친구들과 함께한 즐거운 저녁 시간",
            style="short_story",
            length="long",
            emotion="행복",
            regeneration_count=1,
        )

        with patch("app.services.ai_log.get_openai_client") as mock_get_client:
            mock_client = Mock()
            mock_get_client.return_value = mock_client

            # 3단계 응답 시뮬레이션
            mock_client.async_chat_completion = AsyncMock(
                side_effect=[
                    {"content": "행복", "usage": {"total_tokens": 40}},  # 감정 분석
                    {
                        "content": '["친구", "저녁", "시간", "즐거움", "추억"]',
                        "usage": {"total_tokens": 60},
                    },  # 키워드
                    {
                        "content": "친구들과 함께한 저녁 시간은 정말 소중했다. 맛있는 음식을 나누며 이야기꽃을 피웠고, 서로의 근황을 듣는 것만으로도 마음이 따뜻해졌다. 이런 순간들이 모여 인생의 아름다운 추억이 된다는 걸 새삼 깨닫는다. 바쁜 일상 속에서도 소중한 사람들과의 시간을 놓치지 않아야겠다. 오늘 같은 날이 더 많아지기를 바란다.",
                        "usage": {"total_tokens": 150},
                    },  # 글귀 생성
                ]
            )

            result = await ai_service.generate_ai_text(user_id, request)

            # 결과 검증
            assert result["ai_emotion"] == "행복"
            assert len(result["keywords"]) == 5
            assert "친구들과 함께한 저녁 시간" in result["ai_generated_text"]
            assert result["ai_emotion_confidence"] == 0.9

            # 데이터베이스 로깅 검증
            assert mock_db.add.call_count == 2
            assert mock_db.commit.called

            # 로그 데이터 검증
            generate_log = mock_db.add.call_args_list[0][0][0]
            analysis_log = mock_db.add.call_args_list[1][0][0]

            assert generate_log.api_type == "generate"
            assert generate_log.tokens_used == 150
            assert analysis_log.api_type == "keywords"
            assert analysis_log.tokens_used == 90  # 40 + 50

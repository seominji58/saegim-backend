"""
다이어리 AI 서비스 테스트 코드
"""

import pytest
from unittest.mock import Mock, patch

from app.services.diary_ai import (
    DiaryAIService,
    get_diary_ai_service,
    WritingStyle,
    ContentLength,
)


class TestDiaryAIService:
    """다이어리 AI 서비스 테스트 클래스"""

    @pytest.fixture
    def mock_openai_client(self):
        """Mock OpenAI 클라이언트"""
        mock_client = Mock()
        mock_client.chat_completion.return_value = {
            "content": "test response",
            "id": "chatcmpl-123",
            "model": "gpt-5",
            "created": 1234567890,
            "usage": {"completion_tokens": 10, "prompt_tokens": 20, "total_tokens": 30},
            "finish_reason": "stop",
            "role": "assistant",
        }

        # 비동기 메서드는 코루틴을 반환해야 함
        async def mock_async_response():
            return {
                "content": "test async response",
                "id": "chatcmpl-456",
                "model": "gpt-5",
                "created": 1234567890,
                "usage": {
                    "completion_tokens": 10,
                    "prompt_tokens": 20,
                    "total_tokens": 30,
                },
                "finish_reason": "stop",
                "role": "assistant",
            }

        mock_client.async_chat_completion.return_value = mock_async_response()
        return mock_client

    @pytest.fixture
    def diary_ai_service(self, mock_openai_client):
        """Mock된 다이어리 AI 서비스"""
        with patch(
            "app.services.diary_ai.get_openai_client", return_value=mock_openai_client
        ):
            return DiaryAIService()

    def test_service_initialization(self, diary_ai_service):
        """서비스 초기화 테스트"""
        assert isinstance(diary_ai_service, DiaryAIService)
        assert diary_ai_service.client is not None

    def test_get_diary_ai_service(self):
        """전역 서비스 인스턴스 테스트"""
        with patch("app.services.diary_ai.get_openai_client"):
            service1 = get_diary_ai_service()
            service2 = get_diary_ai_service()
            assert service1 is service2  # 싱글톤 확인

    def test_analyze_emotion_success(self, diary_ai_service, mock_openai_client):
        """감정 분석 성공 테스트"""
        # Mock 응답 설정
        mock_openai_client.chat_completion.return_value = {"content": "행복"}

        result = diary_ai_service._analyze_emotion("오늘 정말 좋은 일이 있었어요!")

        assert result == "행복"
        assert mock_openai_client.chat_completion.called
        call_args = mock_openai_client.chat_completion.call_args

        # 호출된 인자 확인
        assert "messages" in call_args.kwargs
        assert call_args.kwargs["temperature"] == 0.3
        assert call_args.kwargs["max_tokens"] == 50

    def test_analyze_emotion_with_image(self, diary_ai_service, mock_openai_client):
        """이미지 설명이 포함된 감정 분석 테스트"""
        mock_openai_client.chat_completion.return_value = {"content": "평온"}

        result = diary_ai_service._analyze_emotion(
            "바다를 보며 휴식을 취했어요", "푸른 바다와 하늘이 보이는 풍경"
        )

        assert result == "평온"
        call_args = mock_openai_client.chat_completion.call_args
        message_content = call_args.kwargs["messages"][1]["content"]
        assert "이미지 설명" in message_content
        assert "푸른 바다와 하늘" in message_content

    def test_extract_keywords_success(self, diary_ai_service, mock_openai_client):
        """키워드 추출 성공 테스트"""
        # JSON 형태의 Mock 응답
        mock_openai_client.chat_completion.return_value = {
            "content": '["카페", "친구", "커피", "대화", "오후"]'
        }

        result = diary_ai_service._extract_keywords(
            "친구와 카페에서 커피를 마시며 즐거운 대화를 나눴어요", emotion="행복"
        )

        assert len(result) == 5
        assert "카페" in result
        assert "친구" in result
        assert mock_openai_client.chat_completion.called

    def test_extract_keywords_json_parse_error(
        self, diary_ai_service, mock_openai_client
    ):
        """키워드 추출 JSON 파싱 실패 처리 테스트"""
        # 잘못된 JSON 형태의 Mock 응답
        mock_openai_client.chat_completion.return_value = {
            "content": "카페, 친구, 커피, 대화, 오후"
        }

        result = diary_ai_service._extract_keywords("테스트 텍스트", emotion="행복")

        assert len(result) <= 5
        assert "카페" in result
        assert "친구" in result

    def test_generate_quote_success(self, diary_ai_service, mock_openai_client):
        """글귀 생성 성공 테스트"""
        expected_quote = "오늘의 행복한 순간들이 마음속에 오래 남기를 바라며..."
        mock_openai_client.chat_completion.return_value = {"content": expected_quote}

        result = diary_ai_service._generate_quote(
            text_input="친구와 좋은 시간을 보냈어요",
            emotion="행복",
            keywords=["친구", "시간", "카페"],
            writing_style=WritingStyle.SHORT_STORY,
            content_length=ContentLength.MEDIUM,
        )

        assert result == expected_quote
        call_args = mock_openai_client.chat_completion.call_args

        # 창의적 글쓰기를 위한 높은 temperature 확인
        assert call_args.kwargs["temperature"] == 0.8
        assert call_args.kwargs["max_tokens"] == 300

    def test_analyze_diary_full_workflow(self, diary_ai_service, mock_openai_client):
        """전체 다이어리 분석 워크플로우 테스트"""
        # 각 단계별 Mock 응답 설정
        mock_responses = [
            {"content": "행복"},  # 감정 분석
            {"content": '["친구", "카페", "시간", "대화"]'},  # 키워드 추출
            {
                "content": "친구와의 소중한 시간, 마음이 따뜻해지는 하루였네요."
            },  # 글귀 생성
        ]

        mock_openai_client.chat_completion.side_effect = mock_responses

        result = diary_ai_service.analyze_diary(
            text_input="친구와 카페에서 즐거운 시간을 보냈어요",
            writing_style=WritingStyle.SHORT_STORY,
            content_length=ContentLength.SHORT,
        )

        # 결과 검증
        assert result["emotion"] == "행복"
        assert len(result["keywords"]) == 4
        assert "친구" in result["keywords"]
        assert result["quote"] == "친구와의 소중한 시간, 마음이 따뜻해지는 하루였네요."
        assert result["writing_style"] == WritingStyle.SHORT_STORY
        assert result["content_length"] == ContentLength.SHORT

        # OpenAI 클라이언트가 3번 호출되었는지 확인 (감정, 키워드, 글귀)
        assert mock_openai_client.chat_completion.call_count == 3

    @pytest.mark.asyncio
    async def test_async_analyze_emotion_success(
        self, diary_ai_service, mock_openai_client
    ):
        """비동기 감정 분석 성공 테스트"""

        async def mock_async_response():
            return {"content": "불안"}

        mock_openai_client.async_chat_completion.return_value = mock_async_response()

        result = await diary_ai_service._async_analyze_emotion("내일 시험이 걱정돼요")

        assert result == "불안"
        assert mock_openai_client.async_chat_completion.called

    @pytest.mark.asyncio
    async def test_async_extract_keywords_success(
        self, diary_ai_service, mock_openai_client
    ):
        """비동기 키워드 추출 성공 테스트"""

        async def mock_async_response():
            return {"content": '["시험", "공부", "걱정", "내일"]'}

        mock_openai_client.async_chat_completion.return_value = mock_async_response()

        result = await diary_ai_service._async_extract_keywords(
            "내일 시험이 걱정돼요", emotion="불안"
        )

        assert len(result) == 4
        assert "시험" in result
        assert "공부" in result

    @pytest.mark.asyncio
    async def test_async_generate_quote_success(
        self, diary_ai_service, mock_openai_client
    ):
        """비동기 글귀 생성 성공 테스트"""
        expected_quote = (
            "걱정되는 마음도 이해해요. 차근차근 준비하다 보면 괜찮을 거예요."
        )

        async def mock_async_response():
            return {"content": expected_quote}

        mock_openai_client.async_chat_completion.return_value = mock_async_response()

        result = await diary_ai_service._async_generate_quote(
            text_input="내일 시험이 걱정돼요",
            emotion="불안",
            keywords=["시험", "걱정"],
            writing_style=WritingStyle.SHORT_STORY,
            content_length=ContentLength.MEDIUM,
        )

        assert result == expected_quote

    @pytest.mark.asyncio
    async def test_async_analyze_diary_full_workflow(
        self, diary_ai_service, mock_openai_client
    ):
        """비동기 전체 워크플로우 테스트"""
        mock_responses = [
            {"content": "슬픔"},
            {"content": '["비", "창문", "혼자", "집"]'},
            {"content": "비 오는 날의 고요함 속에서도 따뜻한 마음을 찾아보세요."},
        ]

        # 비동기 코루틴 생성기
        async def create_async_response(response):
            return response

        mock_openai_client.async_chat_completion.side_effect = [
            create_async_response(mock_responses[0]),
            create_async_response(mock_responses[1]),
            create_async_response(mock_responses[2]),
        ]

        result = await diary_ai_service.async_analyze_diary(
            text_input="비 오는 날 집에 혼자 있으니 외로워요",
            image_description="창문 밖으로 보이는 비",
            writing_style=WritingStyle.POEM,
            content_length=ContentLength.LONG,
        )

        assert result["emotion"] == "슬픔"
        assert len(result["keywords"]) == 4
        assert result["writing_style"] == WritingStyle.POEM
        assert result["content_length"] == ContentLength.LONG
        assert mock_openai_client.async_chat_completion.call_count == 3

    def test_analyze_diary_with_exception(self, diary_ai_service, mock_openai_client):
        """예외 처리 테스트"""
        mock_openai_client.chat_completion.side_effect = Exception("OpenAI API 오류")

        with pytest.raises(Exception) as exc_info:
            diary_ai_service.analyze_diary("테스트 입력")

        assert "OpenAI API 오류" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_async_analyze_diary_with_exception(
        self, diary_ai_service, mock_openai_client
    ):
        """비동기 예외 처리 테스트"""

        async def mock_async_error(*args, **kwargs):
            raise Exception("비동기 API 오류")

        mock_openai_client.async_chat_completion.side_effect = mock_async_error

        with pytest.raises(Exception) as exc_info:
            await diary_ai_service.async_analyze_diary("테스트 입력")

        assert "비동기 API 오류" in str(exc_info.value)

    def test_emotion_validation(self, diary_ai_service, mock_openai_client):
        """감정 분류 유효성 테스트"""
        valid_emotions = ["행복", "슬픔", "화남", "평온", "불안"]

        for emotion in valid_emotions:
            mock_openai_client.chat_completion.return_value = {"content": emotion}
            result = diary_ai_service._analyze_emotion("테스트 입력")
            assert result in valid_emotions

    def test_keyword_limit_validation(self, diary_ai_service, mock_openai_client):
        """키워드 개수 제한 테스트"""
        # 6개 키워드를 반환하도록 Mock 설정
        mock_openai_client.chat_completion.return_value = {
            "content": '["키워드1", "키워드2", "키워드3", "키워드4", "키워드5", "키워드6"]'
        }

        result = diary_ai_service._extract_keywords("테스트 입력")

        # 최대 5개로 제한되어야 함
        assert len(result) == 5

    def test_writing_style_enum_validation(self):
        """글쓰기 스타일 Enum 테스트"""
        assert WritingStyle.POEM == "poem"
        assert WritingStyle.SHORT_STORY == "short_story"

    def test_content_length_enum_validation(self):
        """글 길이 Enum 테스트"""
        assert ContentLength.SHORT == "short"
        assert ContentLength.MEDIUM == "medium"
        assert ContentLength.LONG == "long"


class TestDiaryAIIntegration:
    """다이어리 AI 통합 테스트"""

    @patch("app.services.diary_ai.get_openai_client")
    def test_service_integration_with_real_like_responses(self, mock_get_client):
        """실제와 유사한 응답을 사용한 통합 테스트"""
        # 실제와 유사한 Mock 응답들
        mock_client = Mock()
        mock_responses = [
            {"content": "행복"},
            {"content": '["친구", "카페", "커피", "오후", "대화"]'},
            {
                "content": "친구와 함께한 따뜻한 오후, 작은 행복이 마음에 스며드는 시간이었네요. 이런 소중한 순간들이 쌓여 우리의 일상을 더욱 빛나게 만들어줍니다."
            },
        ]
        mock_client.chat_completion.side_effect = mock_responses
        mock_get_client.return_value = mock_client

        service = DiaryAIService()
        result = service.analyze_diary(
            text_input="오늘 친구와 카페에서 커피를 마시며 즐거운 오후를 보냈어요. 정말 행복한 시간이었습니다.",
            writing_style=WritingStyle.SHORT_STORY,
            content_length=ContentLength.MEDIUM,
        )

        # 통합 결과 검증
        assert result["emotion"] == "행복"
        assert len(result["keywords"]) == 5
        assert all(
            keyword in ["친구", "카페", "커피", "오후", "대화"]
            for keyword in result["keywords"]
        )
        assert len(result["quote"]) > 50  # 중문 길이 확인
        assert "친구" in result["quote"]  # 키워드가 글귀에 반영되었는지 확인

    @patch("app.services.diary_ai.get_openai_client")
    def test_different_writing_styles(self, mock_get_client):
        """다양한 글쓰기 스타일 테스트"""
        mock_client = Mock()
        mock_get_client.return_value = mock_client

        # 시 스타일 테스트
        mock_client.chat_completion.side_effect = [
            {"content": "평온"},
            {"content": '["바다", "파도", "소리", "바람"]'},
            {"content": "파도 소리 따라\n바람이 불어오네\n마음도 고요해"},
        ]

        service = DiaryAIService()
        result = service.analyze_diary(
            text_input="바다에서 파도 소리를 들으며 마음이 편해졌어요",
            writing_style=WritingStyle.POEM,
            content_length=ContentLength.SHORT,
        )

        assert result["writing_style"] == WritingStyle.POEM
        assert "\n" in result["quote"]  # 시 형태의 줄바꿈 확인

    def test_emotion_categories_coverage(self):
        """모든 감정 카테고리 커버리지 테스트"""
        emotions = ["행복", "슬픔", "화남", "평온", "불안"]

        with patch("app.services.diary_ai.get_openai_client") as mock_get_client:
            mock_client = Mock()
            mock_get_client.return_value = mock_client

            service = DiaryAIService()

            for emotion in emotions:
                mock_client.chat_completion.side_effect = [
                    {"content": emotion},
                    {"content": '["테스트", "키워드"]'},
                    {"content": f"{emotion}과 관련된 따뜻한 글귀입니다."},
                ]

                result = service.analyze_diary(f"{emotion}과 관련된 테스트 입력")
                assert result["emotion"] == emotion
                assert emotion in result["quote"] or "따뜻한" in result["quote"]

"""
AI 텍스트 생성 서비스 테스트
"""

import pytest
import json
import uuid
from unittest.mock import AsyncMock, Mock, patch
from sqlalchemy.orm import Session

from app.services.ai_log import AIService, EmotionType, WritingStyle, ContentLength
from app.schemas.create_diary import CreateDiaryRequest
from app.models.ai_usage_log import AIUsageLog


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
            session_id=None
        )
    
    @pytest.fixture
    def mock_openai_response(self):
        """Mock OpenAI 응답"""
        return {
            "id": "test-id",
            "content": "테스트 응답 내용",
            "model": "gpt-4",
            "created": 1234567890,
            "usage": {
                "completion_tokens": 50,
                "prompt_tokens": 30,
                "total_tokens": 80
            },
            "finish_reason": "stop",
            "role": "assistant"
        }
    
    @pytest.mark.asyncio
    async def test_generate_ai_text_success(self, ai_service, mock_db, sample_request, mock_openai_response):
        """AI 텍스트 생성 성공 테스트"""
        user_id = str(uuid.uuid4())
        
        # Mock OpenAI 클라이언트
        with patch('app.services.ai_log.get_openai_client') as mock_get_client:
            mock_client = Mock()
            mock_get_client.return_value = mock_client
            
            # 감정 분석 응답
            emotion_response = mock_openai_response.copy()
            emotion_response["content"] = "행복"
            # AsyncMock을 사용하여 async 함수 올바르게 모킹
            mock_client.async_chat_completion = AsyncMock(side_effect=[
                emotion_response,  # 감정 분석
                {**mock_openai_response, "content": '["카페", "시간", "오늘", "좋은", "순간"]'},  # 키워드 추출
                {**mock_openai_response, "content": "카페 한 구석 작은 테이블에서\n따뜻한 커피 향이 마음을 적신다\n오늘 같은 평범한 일상이\n얼마나 소중한지 깨닫는다"}  # 글귀 생성
            ])
            
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
    async def test_analyze_emotion_professional(self, ai_service, mock_openai_response):
        """전문적인 감정 분석 테스트"""
        with patch('app.services.ai_log.get_openai_client') as mock_get_client:
            mock_client = Mock()
            mock_get_client.return_value = mock_client
            
            emotion_response = mock_openai_response.copy()
            emotion_response["content"] = "행복"
            mock_client.async_chat_completion = AsyncMock(return_value=emotion_response)
            
            result = await ai_service._analyze_emotion_professional("좋은 하루였다")
            
            assert result["emotion"] == "행복"
            assert result["confidence"] == 0.9
            assert result["tokens_used"] == 80
            
            # 시스템 메시지 확인
            call_args = mock_client.async_chat_completion.call_args[1]
            assert "전문 심리 상담사" in call_args["messages"][0]["content"]
    
    @pytest.mark.asyncio
    async def test_extract_keywords_professional(self, ai_service, mock_openai_response):
        """전문적인 키워드 추출 테스트"""
        with patch('app.services.ai_log.get_openai_client') as mock_get_client:
            mock_client = Mock()
            mock_get_client.return_value = mock_client
            
            keywords_response = mock_openai_response.copy()
            keywords_response["content"] = '["카페", "커피", "시간", "여유", "일상"]'
            mock_client.async_chat_completion = AsyncMock(return_value=keywords_response)
            
            result = await ai_service._extract_keywords_professional("카페에서 커피를 마시며 여유로운 시간을 보냈다", "행복")
            
            assert len(result) == 5
            assert "카페" in result
            assert "커피" in result
            
            # 감정 단어 제외 확인
            call_args = mock_client.async_chat_completion.call_args[1]
            system_message = call_args["messages"][0]["content"]
            assert "행복" in system_message
            assert "감정 단어는 제외" in system_message
    
    @pytest.mark.asyncio
    async def test_extract_keywords_json_parse_error(self, ai_service, mock_openai_response):
        """키워드 추출 JSON 파싱 오류 테스트"""
        with patch('app.services.ai_log.get_openai_client') as mock_get_client:
            mock_client = Mock()
            mock_get_client.return_value = mock_client
            
            keywords_response = mock_openai_response.copy()
            keywords_response["content"] = "카페, 커피, 시간, 여유, 일상"  # JSON이 아닌 형태
            mock_client.async_chat_completion = AsyncMock(return_value=keywords_response)
            
            result = await ai_service._extract_keywords_professional("카페에서 커피 한잔", "행복")
            
            assert len(result) <= 5
            assert len(result) >= 1
            # 기본 파싱으로 처리된 결과 확인
    
    @pytest.mark.asyncio
    async def test_generate_quote_professional_poem_style(self, ai_service, mock_openai_response):
        """시 스타일 글귀 생성 테스트"""
        with patch('app.services.ai_log.get_openai_client') as mock_get_client:
            mock_client = Mock()
            mock_get_client.return_value = mock_client
            
            quote_response = mock_openai_response.copy()
            quote_response["content"] = "카페 한 구석 작은 테이블에서\n따뜻한 커피 향이 마음을 적신다"
            mock_client.async_chat_completion = AsyncMock(return_value=quote_response)
            
            result = await ai_service._generate_quote_professional(
                "카페에서 좋은 시간", "행복", ["카페", "커피"], "poem", "short"
            )
            
            assert result["text"] == "카페 한 구석 작은 테이블에서\n따뜻한 커피 향이 마음을 적신다"
            assert result["tokens_used"] == 80
            
            # 시스템 메시지에 시적 표현 포함 확인
            call_args = mock_client.async_chat_completion.call_args[1]
            system_message = call_args["messages"][0]["content"]
            assert "시" in system_message
            assert "은유와 상징" in system_message
    
    @pytest.mark.asyncio
    async def test_generate_quote_professional_short_story_style(self, ai_service, mock_openai_response):
        """단편글 스타일 글귀 생성 테스트"""
        with patch('app.services.ai_log.get_openai_client') as mock_get_client:
            mock_client = Mock()
            mock_get_client.return_value = mock_client
            
            quote_response = mock_openai_response.copy()
            quote_response["content"] = "오늘 카페에서 보낸 시간이 참 소중했다. 따뜻한 커피 한 잔과 함께 여유로운 오후를 즐겼다."
            mock_client.async_chat_completion = AsyncMock(return_value=quote_response)
            
            result = await ai_service._generate_quote_professional(
                "카페에서 좋은 시간", "행복", ["카페", "커피"], "short_story", "medium"
            )
            
            assert "카페에서 보낸 시간" in result["text"]
            assert result["tokens_used"] == 80
            
            # 시스템 메시지에 자연스러운 문체 포함 확인
            call_args = mock_client.async_chat_completion.call_args[1]
            system_message = call_args["messages"][0]["content"]
            assert "단편글" in system_message
            assert "이야기하듯" in system_message
    
    def test_extract_keywords_fallback(self, ai_service):
        """폴백 키워드 추출 테스트"""
        prompt = "카페에서 커피를 마시며, 좋은 책을 읽고 음악을 들었다"
        result = ai_service._extract_keywords_fallback(prompt)
        
        assert len(result) <= 5
        assert len(result) >= 1
        # 2글자 이상만 포함되는지 확인
        for keyword in result:
            assert len(keyword) >= 2
    
    @pytest.mark.asyncio
    async def test_openai_api_error_handling(self, ai_service, mock_db, sample_request):
        """OpenAI API 오류 처리 테스트"""
        user_id = str(uuid.uuid4())
        
        with patch('app.services.ai_log.get_openai_client') as mock_get_client:
            mock_client = Mock()
            mock_get_client.return_value = mock_client
            mock_client.async_chat_completion = AsyncMock(side_effect=Exception("API Error"))
            
            # 테스트 실행 - fallback 동작으로 예외가 발생하지 않고 기본값 반환
            result = await ai_service.generate_ai_text(user_id, sample_request)
            
            # fallback 값들이 반환되는지 확인
            assert result["ai_emotion"] == "평온"  # 기본 감정값
            assert len(result["keywords"]) > 0  # fallback 키워드 추출
            assert "기본" in result["ai_generated_text"] or "위로" in result["ai_generated_text"]  # fallback 텍스트
    
    @pytest.mark.asyncio
    async def test_session_regeneration_count(self, ai_service, mock_db, sample_request):
        """세션 재생성 카운트 테스트"""
        user_id = str(uuid.uuid4())
        session_id = str(uuid.uuid4())
        sample_request.session_id = session_id
        
        # 기존 로그가 2개 있다고 가정
        existing_logs = [Mock(), Mock()]
        mock_db.execute.return_value.scalars.return_value.all.return_value = existing_logs
        
        with patch('app.services.ai_log.get_openai_client') as mock_get_client:
            mock_client = Mock()
            mock_get_client.return_value = mock_client
            mock_client.async_chat_completion = AsyncMock(side_effect=[
                {"content": "행복", "usage": {"total_tokens": 50}},
                {"content": '["테스트"]', "usage": {"total_tokens": 30}},
                {"content": "테스트 글귀", "usage": {"total_tokens": 80}}
            ])
            
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
            regeneration_count=1
        )
        
        with patch('app.services.ai_log.get_openai_client') as mock_get_client:
            mock_client = Mock()
            mock_get_client.return_value = mock_client
            
            # 3단계 응답 시뮬레이션
            mock_client.async_chat_completion = AsyncMock(side_effect=[
                {"content": "행복", "usage": {"total_tokens": 40}},  # 감정 분석
                {"content": '["친구", "저녁", "시간", "즐거움", "추억"]', "usage": {"total_tokens": 60}},  # 키워드
                {"content": "친구들과 함께한 저녁 시간은 정말 소중했다. 맛있는 음식을 나누며 이야기꽃을 피웠고, 서로의 근황을 듣는 것만으로도 마음이 따뜻해졌다. 이런 순간들이 모여 인생의 아름다운 추억이 된다는 걸 새삼 깨닫는다. 바쁜 일상 속에서도 소중한 사람들과의 시간을 놓치지 않아야겠다. 오늘 같은 날이 더 많아지기를 바란다.", "usage": {"total_tokens": 150}}  # 글귀 생성
            ])
            
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
            
            assert generate_log.api_type == 'generate'
            assert generate_log.tokens_used == 150
            assert analysis_log.api_type == 'keywords'
            assert analysis_log.tokens_used == 90  # 40 + 50
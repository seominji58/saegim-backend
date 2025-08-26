"""
다이어리 AI 서비스: OpenAI를 활용한 감정분석, 키워드추출, 글귀생성
"""

import json
import logging
from typing import Dict, List, Optional, Any
from enum import Enum

from ..utils.openai_utils import get_openai_client

logger = logging.getLogger(__name__)


class WritingStyle(str, Enum):
    """글 문체 타입"""
    POEM = "poem"  # 시
    SHORT_STORY = "short_story"  # 단편글


class ContentLength(str, Enum):
    """글귀 길이 타입"""
    SHORT = "short"  # 단문 (1-2문장)
    MEDIUM = "medium"  # 중문 (3-5문장)
    LONG = "long"  # 장문 (6-10문장)


class DiaryAIService:
    """다이어리 AI 분석 및 생성 서비스"""

    def __init__(self):
        self.client = get_openai_client()

    def analyze_diary(
        self,
        text_input: str,
        image_description: Optional[str] = None,
        writing_style: WritingStyle = WritingStyle.SHORT_STORY,
        content_length: ContentLength = ContentLength.MEDIUM,
    ) -> Dict[str, Any]:
        """
        다이어리 전체 분석 및 생성
        
        Args:
            text_input: 사용자 입력 텍스트
            image_description: 이미지 설명 (옵션)
            writing_style: 글 문체
            content_length: 글귀 길이
            
        Returns:
            감정분석, 키워드, 글귀가 포함된 결과
        """
        try:
            # 1단계: 감정 분석
            emotion = self._analyze_emotion(text_input, image_description)
            logger.info(f"감정 분석 완료: {emotion}")
            
            # 2단계: 키워드 추출 (감정 제외)
            keywords = self._extract_keywords(text_input, image_description, emotion)
            logger.info(f"키워드 추출 완료: {keywords}")
            
            # 3단계: 글귀 생성
            quote = self._generate_quote(
                text_input, image_description, emotion, keywords, 
                writing_style, content_length
            )
            logger.info("글귀 생성 완료")
            
            return self._build_result(emotion, keywords, quote, writing_style, content_length)
            
        except Exception as e:
            logger.error(f"다이어리 AI 분석 오류: {str(e)}")
            raise

    def _build_content(self, text_input: str, image_description: Optional[str] = None) -> str:
        """입력 콘텐츠 구성"""
        content = f"사용자 입력: {text_input}"
        if image_description:
            content += f"\n이미지 설명: {image_description}"
        return content

    def _build_result(
        self, 
        emotion: str, 
        keywords: List[str], 
        quote: str, 
        writing_style: WritingStyle, 
        content_length: ContentLength
    ) -> Dict[str, Any]:
        """결과 객체 구성"""
        return {
            "emotion": emotion,
            "keywords": keywords,
            "quote": quote,
            "writing_style": writing_style,
            "content_length": content_length
        }

    def _get_emotion_system_message(self) -> str:
        """감정 분석 시스템 메시지"""
        return """당신은 전문 심리 상담사입니다. 주어진 텍스트와 이미지 설명을 바탕으로 감정을 분석해주세요.

감정은 다음 중 하나로 분류해주세요:
- 행복 (happiness)
- 슬픔 (sadness) 
- 화남 (anger)
- 평온 (peace)
- 불안 (unrest)

응답은 감정 단어 하나만 한국어로 답해주세요."""

    def _get_keyword_system_message(self, emotion: str) -> str:
        """키워드 추출 시스템 메시지"""
        return f"""주어진 텍스트와 이미지 설명에서 핵심 키워드를 추출해주세요.

조건:
- 최대 5개의 키워드
- 감정 단어는 제외 (특히 '{emotion}' 관련 단어 제외)
- 명사 중심으로 추출
- 구체적이고 의미 있는 단어 선택
- 한국어로 응답

응답 형식: ["키워드1", "키워드2", "키워드3", "키워드4", "키워드5"]
JSON 배열 형태로만 답해주세요."""

    def _get_quote_system_message(
        self, 
        emotion: str, 
        writing_style: WritingStyle, 
        content_length: ContentLength
    ) -> str:
        """글귀 생성 시스템 메시지"""
        length_guide = {
            ContentLength.SHORT: "1-2문장",
            ContentLength.MEDIUM: "3-5문장", 
            ContentLength.LONG: "6-10문장"
        }
        
        style_guide = {
            WritingStyle.POEM: "시적이고 운율이 있는 표현으로, 은유와 상징을 사용해주세요.",
            WritingStyle.SHORT_STORY: "자연스럽고 따뜻한 문체로, 이야기하듯 편안하게 써주세요."
        }
        
        return f"""당신은 감성적이고 위로가 되는 글을 쓰는 작가입니다.

주어진 정보를 바탕으로 사용자에게 위로와 공감이 되는 글귀를 써주세요.

조건:
- 문체: {writing_style.value} ({style_guide[writing_style]})
- 길이: {content_length.value} ({length_guide[content_length]})
- 감정 '{emotion}'을 자연스럽게 반영
- 키워드들을 적절히 활용
- 따뜻하고 위로가 되는 톤
- 강요하지 않는 부드러운 조언
- 한국어로 작성

글귀만 작성해주세요."""

    def _analyze_emotion(
        self, 
        text_input: str, 
        image_description: Optional[str] = None
    ) -> str:
        """감정 분석"""
        content = self._build_content(text_input, image_description)
        
        messages = [
            {"role": "system", "content": self._get_emotion_system_message()},
            {"role": "user", "content": content}
        ]
        
        response = self.client.chat_completion(
            messages=messages,
            temperature=0.3,
            max_tokens=50
        )
        
        return response["content"].strip()

    def _parse_keywords(self, response_content: str) -> List[str]:
        """키워드 응답 파싱"""
        try:
            keywords_json = response_content.strip()
            keywords = json.loads(keywords_json)
            return keywords[:5] if isinstance(keywords, list) else []
        except json.JSONDecodeError:
            logger.error(f"키워드 JSON 파싱 실패: {response_content}")
            keywords = [k.strip() for k in response_content.split(",")]
            return keywords[:5]

    def _extract_keywords(
        self, 
        text_input: str, 
        image_description: Optional[str] = None,
        emotion: str = ""
    ) -> List[str]:
        """키워드 추출 (감정 제외, 최대 5개)"""
        content = self._build_content(text_input, image_description)
        
        messages = [
            {"role": "system", "content": self._get_keyword_system_message(emotion)},
            {"role": "user", "content": content}
        ]
        
        response = self.client.chat_completion(
            messages=messages,
            temperature=0.5,
            max_tokens=100
        )
        
        return self._parse_keywords(response["content"])

    def _build_quote_content(
        self, 
        text_input: str, 
        image_description: Optional[str] = None, 
        emotion: str = "", 
        keywords: List[str] = None
    ) -> str:
        """글귀 생성용 콘텐츠 구성"""
        content = self._build_content(text_input, image_description)
        content += f"\n감정: {emotion}"
        if keywords:
            content += f"\n키워드: {', '.join(keywords)}"
        return content

    def _generate_quote(
        self,
        text_input: str,
        image_description: Optional[str] = None,
        emotion: str = "",
        keywords: List[str] = None,
        writing_style: WritingStyle = WritingStyle.SHORT_STORY,
        content_length: ContentLength = ContentLength.MEDIUM,
    ) -> str:
        """글귀 생성"""
        keywords = keywords or []
        content = self._build_quote_content(text_input, image_description, emotion, keywords)
        
        messages = [
            {"role": "system", "content": self._get_quote_system_message(emotion, writing_style, content_length)},
            {"role": "user", "content": content}
        ]
        
        response = self.client.chat_completion(
            messages=messages,
            temperature=0.8,  # 창의적 글쓰기를 위해 높은 temperature
            max_tokens=300
        )
        
        return response["content"].strip()

    async def async_analyze_diary(
        self,
        text_input: str,
        image_description: Optional[str] = None,
        writing_style: WritingStyle = WritingStyle.SHORT_STORY,
        content_length: ContentLength = ContentLength.MEDIUM,
    ) -> Dict[str, Any]:
        """비동기 다이어리 분석"""
        
        try:
            # 1단계: 감정 분석
            emotion = await self._async_analyze_emotion(text_input, image_description)
            logger.info(f"감정 분석 완료: {emotion}")
            
            # 2단계: 키워드 추출
            keywords = await self._async_extract_keywords(text_input, image_description, emotion)
            logger.info(f"키워드 추출 완료: {keywords}")
            
            # 3단계: 글귀 생성
            quote = await self._async_generate_quote(
                text_input, image_description, emotion, keywords, 
                writing_style, content_length
            )
            logger.info("글귀 생성 완료")
            
            return self._build_result(emotion, keywords, quote, writing_style, content_length)
            
        except Exception as e:
            logger.error(f"다이어리 AI 비동기 분석 오류: {str(e)}")
            raise

    async def _async_analyze_emotion(
        self, 
        text_input: str, 
        image_description: Optional[str] = None
    ) -> str:
        """비동기 감정 분석"""
        content = self._build_content(text_input, image_description)
        
        messages = [
            {"role": "system", "content": self._get_emotion_system_message()},
            {"role": "user", "content": content}
        ]
        
        response = await self.client.async_chat_completion(
            messages=messages,
            temperature=0.3,
            max_tokens=50
        )
        
        return response["content"].strip()

    async def _async_extract_keywords(
        self, 
        text_input: str, 
        image_description: Optional[str] = None,
        emotion: str = ""
    ) -> List[str]:
        """비동기 키워드 추출"""
        content = self._build_content(text_input, image_description)
        
        messages = [
            {"role": "system", "content": self._get_keyword_system_message(emotion)},
            {"role": "user", "content": content}
        ]
        
        response = await self.client.async_chat_completion(
            messages=messages,
            temperature=0.5,
            max_tokens=100
        )
        
        return self._parse_keywords(response["content"])

    async def _async_generate_quote(
        self,
        text_input: str,
        image_description: Optional[str] = None,
        emotion: str = "",
        keywords: List[str] = None,
        writing_style: WritingStyle = WritingStyle.SHORT_STORY,
        content_length: ContentLength = ContentLength.MEDIUM,
    ) -> str:
        """비동기 글귀 생성"""
        keywords = keywords or []
        content = self._build_quote_content(text_input, image_description, emotion, keywords)
        
        messages = [
            {"role": "system", "content": self._get_quote_system_message(emotion, writing_style, content_length)},
            {"role": "user", "content": content}
        ]
        
        response = await self.client.async_chat_completion(
            messages=messages,
            temperature=0.8,
            max_tokens=300
        )
        
        return response["content"].strip()


# 전역 서비스 인스턴스
_global_service: Optional[DiaryAIService] = None


def get_diary_ai_service() -> DiaryAIService:
    """전역 다이어리 AI 서비스 인스턴스 반환"""
    global _global_service
    if _global_service is None:
        _global_service = DiaryAIService()
    return _global_service
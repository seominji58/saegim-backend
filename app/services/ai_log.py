"""
AI 텍스트 생성 서비스 (OpenAI API 사용)
"""

import time
from typing import Dict, Any, Optional, Tuple, List
from fastapi import HTTPException
import logging
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.schemas.create_diary import CreateDiaryRequest
from app.models.ai_usage_log import AIUsageLog
from app.utils.openai_utils import get_openai_client
import uuid
import json
import re
from enum import Enum

logger = logging.getLogger(__name__)


class EmotionType(str, Enum):
    """감정 타입 (diary_ai.py에서 가져옴)"""
    HAPPINESS = "행복"
    SADNESS = "슬픔" 
    ANGER = "화남"
    PEACE = "평온"
    UNREST = "불안"


class WritingStyle(str, Enum):
    """글 문체 타입"""
    POEM = "poem"  # 시
    SHORT_STORY = "short_story"  # 단편글


class ContentLength(str, Enum):
    """글귀 길이 타입"""
    SHORT = "short"  # 단문 (1-2문장)
    MEDIUM = "medium"  # 중문 (3-5문장)
    LONG = "long"  # 장문 (6-10문장)


class AIService:
    def __init__(self, db):
        self.db = db
    
    async def generate_ai_text(
        self,
        user_id: str,
        data: CreateDiaryRequest,
    ) -> Dict[str, Any]:
    
        try:
            logger.info(f"AI 텍스트 생성 시작: {data.prompt[:50]}...")
            
            # 1단계: 전문적인 감정 분석
            emotion_result = await self._analyze_emotion_professional(data.prompt)
            logger.info(f"감정 분석 완료: {emotion_result}")
            
            # 2단계: 감정 기반 키워드 추출
            keywords = await self._extract_keywords_professional(data.prompt, emotion_result["emotion"])
            logger.info(f"키워드 추출 완료: {keywords}")
            
            # 3단계: 전문적인 글귀 생성
            ai_response = await self._generate_quote_professional(
                data.prompt, emotion_result["emotion"], keywords, data.style, data.length
            )
            logger.info("전문적인 글귀 생성 완료")
            
            # 통합된 감정 분석 결과
            emotion_analysis = {
                "emotion": emotion_result["emotion"],
                "confidence": emotion_result.get("confidence", 0.85),
                "details": f"전문 감정 분석: {emotion_result['emotion']}"
            }

            # 세션 ID 처리 및 재생성 카운트 계산
            session_id = data.session_id or str(uuid.uuid4())
            logger.info(f'세션 ID: {session_id}')
            
            # 기존 세션 로그 조회
            statement = (
                select(AIUsageLog)
                .where(AIUsageLog.session_id == session_id)
                .where(AIUsageLog.api_type == 'generate')
            )
            existing_logs = self.db.execute(statement).scalars().all()
            regeneration_count = len(existing_logs) + 1
            
            # 1. 요청 로그 저장 (글 생성)
            request_log = AIUsageLog(
                user_id=user_id,
                api_type='generate',
                session_id=session_id,
                request_data=data.model_dump(),
                response_data=ai_response,
                tokens_used=ai_response.get("tokens_used", 0),
                regeneration_count=regeneration_count
            )
            self.db.add(request_log)
            
            # 2. 키워드/감정 분석 로그 저장
            analysis_log = AIUsageLog(
                user_id=user_id,
                api_type='keywords',  # 키워드 추출용
                session_id=session_id,
                request_data={
                    "prompt": data.prompt,
                    "generated_text": ai_response["text"][:200]  # 분석용 텍스트 일부만
                },
                response_data={
                    "keywords": keywords,
                    "emotion_analysis": emotion_analysis
                },
                tokens_used=emotion_result.get("tokens_used", 0) + 50,  # 감정+키워드 분석 토큰
                regeneration_count=regeneration_count
            )
            self.db.add(analysis_log)
            
            # 데이터베이스 커밋
            self.db.commit()
            logger.info(f"AI 사용 로그 저장 완료 - 생성: {request_log.id}, 분석: {analysis_log.id}")

            # 실제 프론트에 필요한 응답 생성
            result = {
                "ai_generated_text": ai_response["text"],
                "ai_emotion": emotion_analysis.get("emotion", data.emotion or "neutral"),
                "ai_emotion_confidence": emotion_analysis.get("confidence", 0.85),
                "keywords": keywords,
                "session_id": session_id,
            }
            # 응답
            return result
            
        except Exception as e:
            logger.error(f"AI 텍스트 생성 실패: {str(e)}")
            raise HTTPException(status_code=500, detail=f"AI 텍스트 생성 중 오류: {str(e)}")
    
    
    def _extract_keywords_fallback(self, prompt: str) -> list:
        """기본 키워드 추출 (AI 분석 실패시 사용)"""
        # 쉼표, 공백으로 분리하고 2글자 이상만 필터링
        words = re.split(r'[,\s]+', prompt)
        keywords = [word.strip() for word in words if len(word.strip()) >= 2]
        
        # 상위 5개 키워드 반환
        return keywords[:5]
    
    async def _analyze_emotion_professional(self, prompt: str) -> Dict[str, Any]:
        """
        diary_ai.py의 전문적인 감정 분석 로직
        """
        try:
            client = get_openai_client()
            
            system_message = """당신은 전문 심리 상담사입니다. 주어진 텍스트를 바탕으로 감정을 분석해주세요.

감정은 다음 중 하나로 분류해주세요:
- 행복 (happiness)
- 슬픔 (sadness) 
- 화남 (anger)
- 평온 (peace)
- 불안 (unrest)

응답은 감정 단어 하나만 한국어로 답해주세요."""
            
            messages = [
                {"role": "system", "content": system_message},
                {"role": "user", "content": f"사용자 입력: {prompt}"}
            ]
            
            response = await client.async_chat_completion(
                messages=messages,
                temperature=0.3,
                max_tokens=50
            )
            
            emotion = response["content"].strip()
            
            return {
                "emotion": emotion,
                "confidence": 0.9,  # 전문적인 분석이므로 높은 신뢰도
                "tokens_used": response["usage"]["total_tokens"]
            }
            
        except Exception as e:
            logger.error(f"전문 감정 분석 실패: {str(e)}")
            return {
                "emotion": "평온",
                "confidence": 0.5,
                "tokens_used": 0
            }
    
    async def _extract_keywords_professional(self, prompt: str, emotion: str) -> List[str]:
        """
        diary_ai.py의 전문적인 키워드 추출 로직 (감정 제외)
        """
        try:
            client = get_openai_client()
            
            system_message = f"""주어진 텍스트에서 핵심 키워드를 추출해주세요.

조건:
- 최대 5개의 키워드
- 감정 단어는 제외 (특히 '{emotion}' 관련 단어 제외)
- 명사 중심으로 추출
- 구체적이고 의미 있는 단어 선택
- 한국어로 응답

응답 형식: ["키워드1", "키워드2", "키워드3", "키워드4", "키워드5"]
JSON 배열 형태로만 답해주세요."""
            
            messages = [
                {"role": "system", "content": system_message},
                {"role": "user", "content": f"사용자 입력: {prompt}"}
            ]
            
            response = await client.async_chat_completion(
                messages=messages,
                temperature=0.5,
                max_tokens=100
            )
            
            # JSON 파싱
            try:
                keywords_json = response["content"].strip()
                keywords = json.loads(keywords_json)
                return keywords[:5] if isinstance(keywords, list) else []
            except json.JSONDecodeError:
                logger.warning(f"키워드 JSON 파싱 실패: {response['content']}")
                # 기본 파싱 시도
                keywords = [k.strip() for k in response["content"].replace('"', '').replace('[', '').replace(']', '').split(",")]
                return [k for k in keywords if k and len(k) >= 2][:5]
                
        except Exception as e:
            logger.error(f"전문 키워드 추출 실패: {str(e)}")
            return self._extract_keywords_fallback(prompt)
    
    async def _generate_quote_professional(
        self, 
        prompt: str, 
        emotion: str,
        keywords: List[str],
        style: str, 
        length: str
    ) -> Dict[str, Any]:
        """
        diary_ai.py의 전문적인 글귀 생성 로직
        """
        try:
            client = get_openai_client()
            
            # 스타일 매핑
            writing_style = {
                "poem": "시적이고 운율이 있는 표현으로, 은유와 상징을 사용해주세요.",
                "short_story": "자연스럽고 따뜻한 문체로, 이야기하듯 편안하게 써주세요."
            }
            
            # 길이 가이드
            length_guide = {
                "short": "1-2문장",
                "medium": "3-5문장", 
                "long": "6-10문장"
            }
            
            style_instruction = writing_style.get(style, "자연스럽고 따뜻한 문체로 써주세요.")
            length_instruction = length_guide.get(length, "3-5문장")
            
            # 스타일명을 한글로 표시
            style_korean = "시" if style == "poem" else "단편글"
            length_korean = {"short": "단문", "medium": "중문", "long": "장문"}.get(length, "중문")
            
            system_message = f"""당신은 감성적이고 위로가 되는 글을 쓰는 작가입니다.

주어진 정보를 바탕으로 사용자에게 위로와 공감이 되는 글귀를 써주세요.

조건:
- 문체: {style_korean} ({style_instruction})
- 길이: {length_korean} ({length_instruction})
- 감정 '{emotion}'을 자연스럽게 반영
- 키워드들을 적절히 활용: {', '.join(keywords)}
- 따뜻하고 위로가 되는 톤
- 강요하지 않는 부드러운 조언
- 한국어로 작성

글귀만 작성해주세요."""
            
            content = f"""사용자 입력: {prompt}
감정: {emotion}
키워드: {', '.join(keywords)}"""
            
            messages = [
                {"role": "system", "content": system_message},
                {"role": "user", "content": content}
            ]
            
            response = await client.async_chat_completion(
                messages=messages,
                temperature=0.8,  # 창의적 글쓰기를 위해 높은 온도
                max_tokens=300
            )
            
            return {
                "text": response["content"].strip(),
                "tokens_used": response["usage"]["total_tokens"]
            }
            
        except Exception as e:
            logger.error(f"전문 글귀 생성 실패: {str(e)}")
            # 실패 시 기본 응답
            return {
                "text": f"{prompt}에 대한 {style} 형태의 글귀입니다. {emotion}한 감정이 담긴 따뜻한 위로를 전합니다.",
                "tokens_used": 0
            }
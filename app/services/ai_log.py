"""
AI 텍스트 생성 서비스 (Mock 응답 사용)
"""

import time
from typing import Dict, Any, Optional
from fastapi import HTTPException
import logging
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.schemas.create_diary import CreateDiaryRequest
from app.models.ai_usage_log import AIUsageLog
import uuid

logger = logging.getLogger(__name__)

class AIService:
    def __init__(self, db):
        self.db = db
    
    async def generate_ai_text(
        self,
        user_id: str,
        data: CreateDiaryRequest,
    ) -> Dict[str, Any]:
    
        try:
            logger.info(f"Mock AI 텍스트 생성 시작: {data.prompt[:50]}...")
            
            # 1. Mock AI 모델 호출
            ai_response = self._generate_mock_response(data.prompt, data.style, data.length, data.emotion)
            
            # 2. 키워드 추출
            keywords = self._extract_keywords(data.prompt)

            # 재생성 시 session_id 을 같이 전달 받음
            # openai 요청 생성(최초 요청은 session_id 생성 및 regeneration_count 1)
            logger.info('data.session_id')
            session_id = data.session_id or str(uuid.uuid4())
            statement = (
                select(AIUsageLog)
                .where(AIUsageLog.session_id == session_id)
            )
            ai_usage_log = AIUsageLog(
                user_id=user_id,
                api_type='generate',
                session_id=session_id,
                request_data=data.dict(),
                response_data=ai_response,
                tokens_used=ai_response.get("tokens_used", 0),

            )
            session_log = self.db.execute(statement).scalars().all()
            if session_log:
                ai_usage_log.regeneration_count = len(session_log) + 1
            else:
                ai_usage_log.regeneration_count = 1

            # 저장(request_data)

            self.db.add(ai_usage_log)
            self.db.commit()
            logger.info(f"AI 사용 로그 저장 완료: {ai_usage_log}")

            
            # 요청 후 응답 받음
            openai_response = {
                "ai_generated_text": ai_response["text"],
                "tokens_used": ai_response.get("tokens_used", 0),
            }
            logger.info(f"Mock AI 텍스트 생성 완료: {len(openai_response['ai_generated_text'])}자")
            # 응답 저장(response_data)
            

            # 데이터베이스에 저장(session_id, request_data, response_data)

            # 실제 프론트에 필요한 응답 생성
            result = {
                "ai_generated_text": ai_response["text"],
                "ai_emotion": data.emotion or "neutral",
                "ai_emotion_confidence": 0.85,
                "keywords": keywords,
                "session_id": session_id,
            }
            # 응답
            return result
            
        except Exception as e:
            logger.error(f"Mock AI 텍스트 생성 실패: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Mock AI 텍스트 생성 중 오류: {str(e)}")
    
    def _generate_mock_response(
        self, 
        prompt: str, 
        style: str, 
        length: str, 
        emotion: str = None
    ) -> Dict[str, Any]:
        """
        Mock AI 응답 생성
        """
        if style == "시":
            lines = {
                "단문": 3,
                "중문": 5,
                "장문": 7
            }.get(length, 3)
            
            text = "\n".join([
                f"{prompt}에 대한 {emotion or '감성적인'} {style}",
                f"{'감정이 스며든 ' * (lines-2)}",
                f"오늘의 나를 새긴다"
            ])
        else:
            sentences = {
                "단문": 2,
                "중문": 3,
                "장문": 4
            }.get(length, 2)
            
            text = f"{prompt}에 대해 생각해본다. {emotion or '자연스러운'} 감정이 배어나온다. " * sentences
        
        return {
            "text": text,
            "tokens_used": len(text.split())
        }
    
    def _extract_keywords(self, prompt: str) -> list:
        """프롬프트에서 키워드 추출"""
        import re
        
        # 쉼표, 공백으로 분리하고 2글자 이상만 필터링
        words = re.split(r'[,\s]+', prompt)
        keywords = [word.strip() for word in words if len(word.strip()) >= 2]
        
        # 상위 5개 키워드 반환
        return keywords[:5]
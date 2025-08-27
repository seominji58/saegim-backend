"""
AI 텍스트 생성 서비스 (OpenAI API 사용)
"""

import json
import logging
import re
import time
import uuid
from enum import Enum
from typing import Any, Dict

from sqlalchemy import func, select

from app.exceptions.ai import (
    AIGenerationFailedException,
    InvalidRequestException,
    RegenerationLimitExceededException,
    SessionNotFoundException,
)
from app.models.ai_usage_log import AIUsageLog
from app.schemas.create_diary import CreateDiaryRequest
from app.services.notification_service import NotificationService
from app.utils.openai_utils import get_openai_client

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

            start_time = time.time()
            # 통합된 AI 분석 및 글귀 생성 (한 번의 API 호출)
            ai_result = await self._generate_complete_analysis(
                data.prompt, data.style, data.length
            )
            logger.info("통합 AI 분석 및 글귀 생성 완료")

            # 결과 파싱
            emotion_analysis = {
                "emotion": ai_result["emotion"],
                "confidence": ai_result.get("confidence", 0.9),
                "details": f"통합 분석: {ai_result['emotion']}",
            }
            keywords = ai_result["keywords"]
            ai_response = {
                "text": ai_result["generated_text"],
                "tokens_used": ai_result["tokens_used"],
            }

            # 재생성 시 session_id 을 같이 전달 받음
            # openai 요청 생성(최초 요청은 session_id 생성 및 regeneration_count 1)
            logger.info(f"data.session_id: {data.session_id}")
            session_id = data.session_id or str(uuid.uuid4())
            logger.info(f"세션 ID: {session_id}")

            # 기존 세션 로그 조회 (통합 분석 타입으로)
            statement = (
                select(AIUsageLog)
                .where(AIUsageLog.session_id == session_id)
                .where(AIUsageLog.api_type == "integrated_analysis")
            )
            existing_logs = self.db.execute(statement).scalars().all()
            regeneration_count = len(existing_logs) + 1

            # 재생성 횟수 제한 체크 (5회까지만 허용)
            if regeneration_count > 5:
                logger.warning(
                    f"재생성 횟수 초과: 사용자 {user_id}, 세션 {session_id}, 시도 횟수: {regeneration_count}"
                )
                raise RegenerationLimitExceededException(
                    current_count=regeneration_count, max_count=5, session_id=session_id
                )

            # 통합 AI 분석 로그 저장 (감정분석 + 키워드추출 + 글귀생성)
            ai_usage_log = AIUsageLog(
                user_id=user_id,
                api_type="integrated_analysis",  # 새로운 통합 분석 타입
                session_id=session_id,
                request_data=data.model_dump(),
                response_data={
                    "ai_generated_text": ai_response["text"],
                    "emotion": emotion_analysis["emotion"],
                    "emotion_confidence": emotion_analysis["confidence"],
                    "keywords": keywords,
                    "style": data.style,
                    "length": data.length,
                },
                tokens_used=ai_response.get("tokens_used", 0),
                regeneration_count=regeneration_count,
            )
            self.db.add(ai_usage_log)

            # 데이터베이스 커밋
            self.db.commit()
            logger.info(
                f"통합 AI 분석 로그 저장 완료 - ID: {ai_usage_log.id}, 토큰 사용량: {ai_response.get('tokens_used', 0)}"
            )

            # 처리 시간 계산 및 조건부 알림 발송
            processing_time = time.time() - start_time
            NOTIFICATION_THRESHOLD_SECONDS = 3.0  # 3초 이상 걸린 경우에만 알림 발송

            if processing_time >= NOTIFICATION_THRESHOLD_SECONDS:
                logger.info(
                    f"AI 텍스트 생성 시간이 {processing_time:.2f}초로 임계값({NOTIFICATION_THRESHOLD_SECONDS}초) 초과, 알림 발송"
                )
                try:
                    notification_result = (
                        await NotificationService.send_ai_content_ready(
                            user_id, session_id, self.db
                        )
                    )
                    if notification_result.success_count > 0:
                        logger.info(
                            f"AI 텍스트 생성 후 콘텐츠 완료 알림 발송 성공: session_id={session_id}, user_id={user_id}, 처리시간={processing_time:.2f}초"
                        )
                    else:
                        logger.warning(
                            f"AI 텍스트 생성 후 콘텐츠 완료 알림 발송 실패: session_id={session_id}, user_id={user_id}"
                        )
                except Exception as e:
                    # 알림 발송 실패가 AI 텍스트 생성을 방해하지 않도록 함
                    logger.error(
                        f"AI 텍스트 생성 후 콘텐츠 완료 알림 발송 중 오류: session_id={session_id}, user_id={user_id}, error={str(e)}"
                    )
            else:
                logger.info(f"AI 텍스트 생성 시간이 {processing_time:.2f}초로 빠름, 알림 발송 생략")

            # 실제 프론트에 필요한 응답 생성
            result = {
                "ai_generated_text": ai_response["text"],
                "ai_emotion": emotion_analysis.get(
                    "emotion", data.emotion or "neutral"
                ),
                "ai_emotion_confidence": emotion_analysis.get("confidence", 0.85),
                "keywords": keywords,
                "session_id": session_id,
                "regeneration_info": {
                    "current_count": regeneration_count,
                    "max_count": 5,
                    "remaining_count": 5 - regeneration_count,
                    "can_regenerate": regeneration_count < 5,
                },
            }
            # 응답
            return result
        except RegenerationLimitExceededException:
            # 재생성 제한 예외는 그대로 전파
            raise
        except Exception as e:
            logger.error(f"AI 텍스트 생성 실패: {str(e)}")
            raise AIGenerationFailedException(
                detail=f"AI 텍스트 생성 중 오류가 발생했습니다: {str(e)}",
                error_type="GENERATION_ERROR",
            )

    def get_regeneration_status(self, session_id: str) -> Dict[str, Any]:
        """
        특정 세션의 재생성 횟수 정보 조회

        Args:
            session_id: 세션 ID

        Returns:
            Dict: 재생성 횟수 정보
        """
        try:
            statement = (
                select(AIUsageLog)
                .where(AIUsageLog.session_id == session_id)
                .where(AIUsageLog.api_type == "integrated_analysis")
            )
            existing_logs = self.db.execute(statement).scalars().all()
            current_count = len(existing_logs)

            return {
                "session_id": session_id,
                "current_count": current_count,
                "max_count": 5,
                "remaining_count": max(0, 5 - current_count),
                "can_regenerate": current_count < 5,
                "is_limit_reached": current_count >= 5,
            }

        except Exception as e:
            logger.error(f"재생성 상태 조회 실패: {str(e)}")
            raise SessionNotFoundException(session_id=session_id)

    def get_user_daily_stats(self, user_id: str) -> Dict[str, Any]:
        """
        사용자의 일일 AI 사용 통계 조회

        Args:
            user_id: 사용자 ID

        Returns:
            Dict: 일일 AI 사용 통계
        """
        try:
            from datetime import datetime, timezone

            # 오늘 날짜 기준으로 조회
            today = datetime.now(timezone.utc).date()

            statement = (
                select(AIUsageLog)
                .where(AIUsageLog.user_id == user_id)
                .where(AIUsageLog.api_type == "integrated_analysis")
                .where(func.date(AIUsageLog.created_at) == today)
            )

            logs = self.db.execute(statement).scalars().all()

            # 세션별 통계
            session_stats = {}
            total_tokens = 0
            total_requests = len(logs)

            for log in logs:
                session_id = str(log.session_id)
                if session_id not in session_stats:
                    session_stats[session_id] = {
                        "session_id": session_id,
                        "request_count": 0,
                        "tokens_used": 0,
                        "first_request": log.created_at,
                        "last_request": log.created_at,
                    }

                session_stats[session_id]["request_count"] += 1
                session_stats[session_id]["tokens_used"] += log.tokens_used or 0
                session_stats[session_id]["last_request"] = max(
                    session_stats[session_id]["last_request"], log.created_at
                )

                total_tokens += log.tokens_used or 0

            return {
                "user_id": user_id,
                "date": today.isoformat(),
                "total_sessions": len(session_stats),
                "total_requests": total_requests,
                "total_tokens_used": total_tokens,
                "average_tokens_per_request": round(total_tokens / total_requests, 2)
                if total_requests > 0
                else 0,
                "sessions": list(session_stats.values()),
            }

        except Exception as e:
            logger.error(f"사용자 일일 통계 조회 실패: {str(e)}")
            raise InvalidRequestException(
                detail=f"사용자 통계 조회 중 오류가 발생했습니다: {str(e)}",
                field="user_id",
            )

    # validate_request 메소드 제거됨 - Pydantic 모델에서 자동 검증 처리

    async def _generate_complete_analysis(
        self, prompt: str, style: str, length: str
    ) -> Dict[str, Any]:
        """
        한 번의 API 호출로 감정 분석, 키워드 추출, 글귀 생성을 모두 처리
        """
        try:
            client = get_openai_client()

            # 스타일 및 길이 매핑
            style_info = {
                "poem": {
                    "name": "시",
                    "desc": "시적이고 운율이 있는 표현으로, 은유와 상징을 사용",
                },
                "short_story": {
                    "name": "단편글",
                    "desc": "자연스럽고 따뜻한 문체로, 이야기하듯 편안하게",
                },
            }

            length_info = {
                "short": {"name": "단문", "desc": "1-2문장"},
                "medium": {"name": "중문", "desc": "3-5문장"},
                "long": {"name": "장문", "desc": "6-10문장"},
            }

            style_guide = style_info.get(
                style, {"name": "단편글", "desc": "자연스럽고 따뜻한 문체로"}
            )
            length_guide = length_info.get(length, {"name": "중문", "desc": "3-5문장"})

            system_message = f"""당신은 감성적이고 위로가 되는 글을 쓰는 전문 작가이자 심리 상담사입니다.

주어진 텍스트를 분석하여 다음 작업을 한 번에 수행해주세요:

1. 감정 분석: 다음 중 하나로 분류
   - 행복, 슬픔, 화남, 평온, 불안

2. 키워드 추출: 감정 단어를 제외한 핵심 키워드 최대 5개 (명사 중심)

3. 글귀 생성:
   - 문체: {style_guide["name"]} ({style_guide["desc"]})
   - 길이: {length_guide["name"]} ({length_guide["desc"]})
   - 따뜻하고 위로가 되는 톤
   - 분석된 감정과 키워드를 자연스럽게 반영

응답 형식 (JSON):
{{
    "emotion": "감정",
    "keywords": ["키워드1", "키워드2", "키워드3", "키워드4", "키워드5"],
    "generated_text": "생성된 글귀"
}}

JSON 형식으로만 답해주세요."""

            messages = [
                {"role": "system", "content": system_message},
                {"role": "user", "content": f"사용자 입력: {prompt}"},
            ]

            response = await client.async_chat_completion(
                messages=messages, temperature=0.7, max_tokens=500
            )
            logger.info(f"OpenAI API 응답: {response}")

            # JSON 파싱
            try:
                result_json = response["content"].strip()
                result = json.loads(result_json)

                return {
                    "emotion": result.get("emotion", "평온"),
                    "keywords": result.get("keywords", [])[:5],
                    "generated_text": result.get("generated_text", ""),
                    "confidence": 0.9,
                    "tokens_used": response["usage"]["total_tokens"],
                }

            except json.JSONDecodeError as e:
                logger.error(f"JSON 파싱 실패: {result_json}, 오류: {str(e)}")
                # 파싱 실패 시 fallback 처리
                return await self._fallback_analysis(prompt, style, length)

        except Exception as e:
            logger.error(f"통합 AI 분석 실패: {str(e)}")

            # OpenAI API 관련 예외 타입별 처리
            error_str = str(e).lower()

            if "rate limit" in error_str or "quota" in error_str:
                # API 호출 한도 초과
                logger.warning(f"OpenAI API 호출 한도 초과, fallback 사용: {str(e)}")
            elif "service unavailable" in error_str or "timeout" in error_str:
                # 서비스 일시적 불가
                logger.warning(f"OpenAI 서비스 일시적 불가, fallback 사용: {str(e)}")
            elif "token" in error_str and "limit" in error_str:
                # 토큰 한도 초과
                logger.warning(f"토큰 한도 초과, fallback 사용: {str(e)}")
            else:
                # 기타 AI 생성 오류
                logger.warning(f"AI 생성 오류, fallback 사용: {str(e)}")

            return await self._fallback_analysis(prompt, style, length)

    async def _fallback_analysis(
        self, prompt: str, style: str, length: str
    ) -> Dict[str, Any]:
        """API 호출 실패 시 대체 분석"""
        # 스타일별 문체 적용
        style_prefix = {
            "poem": "시처럼 부드럽게 흘러가는",
            "short_story": "이야기처럼 따뜻한",
        }

        prefix = style_prefix.get(style, "")

        # 길이별 기본 응답 생성
        length_mapping = {
            "short": f"{prefix} {prompt[:10]}...에 대한 생각이 마음을 따뜻하게 합니다.".strip(),
            "medium": f"오늘의 하루를 돌아보며, {prefix} {prompt[:20]}...에 대한 생각이 마음을 따뜻하게 합니다. 이런 순간들이 소중합니다.".strip(),
            "long": f"오늘의 하루를 돌아보며, {prefix} {prompt[:20]}...에 대한 생각이 마음을 따뜻하게 합니다. 이런 순간들이 소중하며, 우리의 일상 속에서 찾아가는 작은 행복들이 모여 큰 의미를 만들어갑니다.".strip(),
        }

        return {
            "emotion": "평온",
            "keywords": self._extract_keywords_fallback(prompt),
            "generated_text": length_mapping.get(length, length_mapping["medium"]),
            "confidence": 0.5,
            "tokens_used": 0,
        }

    def _extract_keywords_fallback(self, prompt: str) -> list:
        """기본 키워드 추출 (AI 분석 실패시 사용)"""
        # 쉼표, 공백으로 분리하고 2글자 이상만 필터링
        words = re.split(r"[,\s]+", prompt)
        keywords = [word.strip() for word in words if len(word.strip()) >= 2]

        # 상위 5개 키워드 반환
        return keywords[:5]

"""
AI 텍스트 생성 서비스 (OpenAI API 사용)
"""

import json
import logging
import time
import uuid
from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.exceptions.ai import (
    AIGenerationFailedException,
    InvalidRequestException,
    RegenerationLimitExceededException,
    SessionNotFoundException,
)
from app.models.ai_usage_log import AIUsageLog
from app.schemas.create_diary import CreateDiaryRequest
from app.services.base import BaseService
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


class AIService(BaseService):
    def __init__(self, db: Session):
        super().__init__(db)
        if not self.db:
            raise ValueError("Database session is required for AIService")
        # 타입 체커를 위한 명시적 어서션
        assert isinstance(self.db, Session), "AIService requires a Session instance"

    @property
    def session(self) -> Session:
        """타입 안전한 세션 접근"""
        if not self.db or not isinstance(self.db, Session):
            raise ValueError("Database session is required for AIService")
        return self.db

    async def generate_ai_text(
        self,
        user_id: UUID,
        data: CreateDiaryRequest,
    ) -> dict[str, Any]:
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

            # 재생성 시 session_id 또는 sessionId를 같이 전달 받음
            # openai 요청 생성(최초 요청은 session_id 생성 및 regeneration_count 1)
            session_id = (
                getattr(data, "sessionId", None) or data.session_id or str(uuid.uuid4())
            )

            # 기존 세션 로그 조회 (통합 분석 타입으로)
            statement = (
                select(AIUsageLog)
                .where(AIUsageLog.session_id == session_id)
                .where(AIUsageLog.api_type == "integrated_analysis")
            )

            existing_logs = self.session.execute(statement).scalars().all()
            regeneration_count = len(existing_logs) + 1

            # 재생성 횟수 제한 체크 (5회까지만 허용)
            if regeneration_count > 5:
                logger.warning(
                    f"⚠️ 재생성 횟수 초과: 사용자 {user_id}, 세션 {session_id}, 시도 횟수: {regeneration_count}"
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
            self.session.add(ai_usage_log)

            # 데이터베이스 커밋
            self.session.commit()
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
                    notification_service = NotificationService(self.session)
                    notification_result = (
                        await notification_service.send_ai_content_ready(
                            user_id, session_id
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
                logger.info(
                    f"AI 텍스트 생성 시간이 {processing_time:.2f}초로 빠름, 알림 발송 생략"
                )

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
            ) from e

    async def stream_ai_text(
        self,
        user_id: UUID,
        data: CreateDiaryRequest,
    ):
        """AI 텍스트 실시간 스트리밍 생성"""
        try:
            logger.info(f"AI 텍스트 스트리밍 시작: {data.prompt[:50]}...")

            # 세션 ID 생성/확인
            session_id = (
                getattr(data, "sessionId", None) or data.session_id or str(uuid.uuid4())
            )

            # 재생성 횟수 확인
            statement = (
                select(AIUsageLog)
                .where(AIUsageLog.session_id == session_id)
                .where(AIUsageLog.api_type == "integrated_analysis")
            )
            existing_logs = self.session.execute(statement).scalars().all()
            regeneration_count = len(existing_logs) + 1

            if regeneration_count > 5:
                error_data = {
                    "error": "재생성 횟수가 5회를 초과했습니다.",
                    "session_id": session_id,
                    "current_count": regeneration_count,
                }
                yield json.dumps(error_data, ensure_ascii=False)
                return

            # 초기 메타데이터 전송
            initial_data = {
                "type": "start",
                "session_id": session_id,
                "regeneration_count": regeneration_count,
            }
            yield json.dumps(initial_data, ensure_ascii=False)

            # 스트리밍으로 텍스트 생성
            collected_text = ""
            total_tokens = 0
            chunk_index = 0

            async for text_chunk in self._stream_complete_analysis(
                data.prompt, data.style, data.length
            ):
                if isinstance(text_chunk, dict) and "tokens_used" in text_chunk:
                    total_tokens = text_chunk["tokens_used"]
                    continue

                collected_text += text_chunk
                chunk_data = {
                    "type": "content",
                    "content": text_chunk,
                    "accumulated": collected_text,
                    "timestamp": int(time.time() * 1000),  # 서버 타임스탬프 추가
                    "chunk_index": chunk_index,  # 청크 순서 보장
                }
                chunk_index += 1
                yield json.dumps(chunk_data, ensure_ascii=False)
                # 실시간 스트리밍을 위한 강제 flush
                import asyncio

                await asyncio.sleep(0)  # 이벤트 루프에 제어권 양보하여 즉시 전송

            # 완료 후 분석 결과 처리 (평문 텍스트)
            generated_text = collected_text.strip()

            # 생성된 텍스트에 대해 별도로 감정 분석과 키워드 추출
            try:
                # 간단한 감정 분석 (기본값 사용)
                emotion = "평온"  # 기본 감정으로 설정
                # 간단한 키워드 추출 (원본 프롬프트에서)
                keywords = data.prompt.split()[:5] if data.prompt else []

            except Exception as e:
                logger.warning(f"스트리밍 후 분석 실패: {str(e)}")
                emotion = "평온"
                keywords = []

            # 스트리밍 로그 저장
            ai_usage_log = AIUsageLog(
                user_id=user_id,
                api_type="integrated_analysis",
                session_id=session_id,
                request_data=data.model_dump(),
                response_data={
                    "ai_generated_text": generated_text,
                    "emotion": emotion,
                    "keywords": keywords,
                    "style": data.style,
                    "length": data.length,
                },
                tokens_used=total_tokens,
                regeneration_count=regeneration_count,
            )
            self.session.add(ai_usage_log)
            self.session.commit()

            # 완료 메타데이터 전송
            final_data = {
                "type": "complete",
                "emotion": emotion,
                "keywords": keywords,
                "generated_text": generated_text,
                "tokens_used": total_tokens,
                "session_id": session_id,
            }
            yield json.dumps(final_data, ensure_ascii=False)

        except Exception as e:
            logger.error(f"AI 텍스트 스트리밍 실패: {str(e)}")
            error_data = {
                "type": "error",
                "error": f"AI 텍스트 생성 중 오류가 발생했습니다: {str(e)}",
            }
            yield json.dumps(error_data, ensure_ascii=False)

    async def _stream_complete_analysis(self, prompt: str, style: str, length: str):
        """스트리밍으로 통합 분석 수행"""
        try:
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
                "short": {"name": "단문", "desc": "1-2문장, 최대 50자 이내"},
                "medium": {"name": "중문", "desc": "3-5문장, 최대 150자 이내"},
                "long": {"name": "장문", "desc": "6-10문장, 최대 300자 이내"},
            }

            style_guide = style_info.get(
                style, {"name": "단편글", "desc": "자연스럽고 따뜻한 문체로"}
            )
            length_guide = length_info.get(length, {"name": "중문", "desc": "3-5문장"})

            system_message = f"""당신은 감성적이고 위로가 되는 글을 쓰는 전문 작가입니다.

주어진 키워드나 텍스트를 바탕으로 감성적인 글귀를 생성해주세요:

- 문체: {style_guide["name"]} ({style_guide["desc"]})
- 길이: {length_guide["name"]} ({length_guide["desc"]}) - 반드시 이 길이를 지켜주세요
- 따뜻하고 위로가 되는 톤
- 중요: 글귀는 반드시 요청된 길이 제한 내에서 생성해야 합니다

생성된 글귀만 답해주세요. 다른 설명이나 JSON 형식은 사용하지 마세요."""

            messages = [
                {"role": "system", "content": system_message},
                {"role": "user", "content": f"사용자 입력: {prompt}"},
            ]

            # 스트리밍으로 응답 생성 (OpenAI stream=True 사용)
            import os

            from openai import AsyncOpenAI

            openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

            stream = await openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                max_completion_tokens=500,
                stream=True,
            )

            chunk_count = 0
            total_content = ""

            async for chunk in stream:
                chunk_count += 1
                if chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    total_content += content
                    logger.info(
                        f"📦 OpenAI 청크 #{chunk_count}: '{content[:50]}...' (길이: {len(content)})"
                    )

                    # 더 작은 단위로 나누어 전송 (실시간 스트리밍 효과)
                    for char in content:
                        yield char
                        # 실시간 스트리밍을 위한 강제 flush
                        import asyncio

                        await asyncio.sleep(0.05)  # 50ms 지연으로 더 확실한 실시간 효과
                else:
                    logger.debug(f"⚪ OpenAI 빈 청크 #{chunk_count}")

            logger.info(
                f"🏁 OpenAI 스트리밍 완료: 총 {chunk_count}개 청크, {len(total_content)}자"
            )

        except Exception as e:
            logger.error(f"스트리밍 AI 분석 실패: {str(e)}")
            raise

    def get_regeneration_status(self, session_id: str) -> dict[str, Any]:
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

            existing_logs = self.session.execute(statement).scalars().all()
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
            raise SessionNotFoundException(session_id=session_id) from e

    async def get_original_user_input(
        self, user_id: UUID, session_id: str
    ) -> str | None:
        """세션ID로 원본 사용자 입력 조회"""
        try:
            statement = (
                select(AIUsageLog)
                .where(AIUsageLog.session_id == session_id)
                .where(AIUsageLog.user_id == user_id)
                .where(AIUsageLog.api_type == "integrated_analysis")
                .order_by(AIUsageLog.created_at.asc())
                .limit(1)
            )

            result = self.session.execute(statement).scalar_one_or_none()
            if result and result.request_data:
                import json

                request_data = json.loads(result.request_data)
                return request_data.get("prompt")

            return None

        except Exception as e:
            logger.error(f"원본 사용자 입력 조회 실패: {str(e)}")
            return None

    async def regenerate_by_session_id(
        self, user_id: UUID, session_id: str
    ) -> dict[str, Any]:
        """세션 ID로 이전 요청 정보를 가져와서 재생성"""
        try:
            # 해당 세션의 가장 최근 로그 조회
            statement = (
                select(AIUsageLog)
                .where(AIUsageLog.session_id == session_id)
                .where(AIUsageLog.user_id == user_id)
                .where(AIUsageLog.api_type == "integrated_analysis")
                .order_by(AIUsageLog.created_at.desc())
                .limit(1)
            )

            result = self.session.execute(statement)
            last_log = result.scalar_one_or_none()

            if not last_log:
                raise SessionNotFoundException(session_id=session_id)

            # 현재 세션의 총 재생성 횟수 확인 (5회 제한)
            session_logs_count = self.session.execute(
                select(func.count(AIUsageLog.id))
                .where(AIUsageLog.session_id == session_id)
                .where(AIUsageLog.api_type == "integrated_analysis")
            ).scalar()

            if session_logs_count >= 5:
                raise RegenerationLimitExceededException(
                    current_count=session_logs_count, max_count=5, session_id=session_id
                )

            # 이전 요청 데이터 복원
            original_request = CreateDiaryRequest(**last_log.request_data)

            # 재생성 횟수 증가
            original_request.regeneration_count = session_logs_count + 1
            original_request.session_id = session_id

            # AI 텍스트 재생성
            return await self.generate_ai_text(user_id, original_request)

        except Exception as e:
            logger.error(f"세션 기반 재생성 실패: {str(e)}")
            raise

    def test_db_connection(self) -> dict[str, Any]:
        """
        DB 연결 상태 테스트

        Returns:
            Dict: DB 연결 상태 정보
        """
        try:
            # 간단한 쿼리 실행
            statement = select(func.count()).select_from(AIUsageLog)
            result = self.session.execute(statement).scalar()

            return {
                "status": "success",
                "message": "DB 연결 정상",
                "total_logs": result,
                "db_session": str(type(self.session)),
                "timestamp": str(datetime.now()),
            }

        except Exception as e:
            logger.error(f"DB 연결 테스트 실패: {str(e)}")

            return {
                "status": "error",
                "message": f"DB 연결 실패: {str(e)}",
                "error_type": type(e).__name__,
                "timestamp": str(datetime.now()),
            }

    def get_user_daily_stats(self, user_id: UUID) -> dict[str, Any]:
        """
        사용자의 일일 AI 사용 통계 조회

        Args:
            user_id: 사용자 ID

        Returns:
            Dict: 일일 AI 사용 통계
        """
        try:
            from datetime import datetime

            # 오늘 날짜 기준으로 조회
            today = datetime.now(UTC).date()

            statement = (
                select(AIUsageLog)
                .where(AIUsageLog.user_id == user_id)
                .where(AIUsageLog.api_type == "integrated_analysis")
                .where(func.date(AIUsageLog.created_at) == today)
            )

            logs = self.session.execute(statement).scalars().all()

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
            ) from e

    # validate_request 메소드 제거됨 - Pydantic 모델에서 자동 검증 처리

    async def _generate_complete_analysis(
        self, prompt: str, style: str, length: str
    ) -> dict[str, Any]:
        """
        한 번의 API 호출로 감정 분석, 키워드 추출, 글귀 생성을 모두 처리
        """
        try:
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
                "short": {"name": "단문", "desc": "1-2문장, 최대 50자 이내"},
                "medium": {"name": "중문", "desc": "3-5문장, 최대 150자 이내"},
                "long": {"name": "장문", "desc": "6-10문장, 최대 300자 이내"},
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
   - 길이: {length_guide["name"]} ({length_guide["desc"]}) - 반드시 이 길이를 지켜주세요
   - 따뜻하고 위로가 되는 톤
   - 분석된 감정과 키워드를 자연스럽게 반영
   - 중요: 글귀는 반드시 요청된 길이 제한 내에서 생성해야 합니다

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

            client = get_openai_client()
            response = await client.async_chat_completion(
                messages=messages, max_completion_tokens=500
            )
            logger.info(f"OpenAI API 응답: {response}")

            # JSON 파싱 (json_repair 라이브러리 사용으로 LLM 응답 특화 처리)
            try:
                result_json = response["content"].strip()
                result = None

                try:
                    # json_repair를 사용한 견고한 파싱
                    from json_repair import repair_json

                    result = repair_json(result_json, return_objects=True)
                except ImportError:
                    # json_repair가 없는 경우 기존 방식 사용
                    logger.warning(
                        "json_repair 라이브러리를 찾을 수 없어 기본 방식을 사용합니다"
                    )
                    import re

                    result_json = re.sub(
                        r"[\x00-\x1f\x7f-\x9f\u200b-\u200d\ufeff\u00a0\u2000-\u200a\u2028\u2029]",
                        "",
                        result_json,
                    )
                    result = json.loads(result_json)

                # result가 성공적으로 파싱되었는지 확인
                if result is None or not isinstance(result, dict):
                    raise ValueError("파싱된 결과가 유효한 딕셔너리가 아닙니다")

                return {
                    "emotion": result.get("emotion", "평온"),
                    "keywords": result.get("keywords", [])[:5],
                    "generated_text": result.get("generated_text", ""),
                    "confidence": 0.9,
                    "tokens_used": response["usage"]["total_tokens"],
                }

            except (json.JSONDecodeError, ValueError) as e:
                logger.error(f"JSON 파싱 실패: {result_json}, 오류: {str(e)}")
                # 파싱 실패 시 예외 발생
                raise AIGenerationFailedException(
                    detail=f"AI 응답 파싱 실패: {str(e)}",
                    error_type="PARSING_ERROR",
                ) from e

        except Exception as e:
            logger.error(f"통합 AI 분석 실패: {str(e)}")

            # OpenAI API 관련 예외 타입별 처리 및 예외 발생
            error_str = str(e).lower()

            if "rate limit" in error_str or "quota" in error_str:
                # API 호출 한도 초과
                logger.error(f"OpenAI API 호출 한도 초과: {str(e)}")
                raise AIGenerationFailedException(
                    detail="OpenAI API 호출 한도를 초과했습니다. 잠시 후 다시 시도해주세요.",
                    error_type="RATE_LIMIT_ERROR",
                ) from e
            elif "service unavailable" in error_str or "timeout" in error_str:
                # 서비스 일시적 불가
                logger.error(f"OpenAI 서비스 일시적 불가: {str(e)}")
                raise AIGenerationFailedException(
                    detail="AI 서비스가 일시적으로 사용할 수 없습니다. 잠시 후 다시 시도해주세요.",
                    error_type="SERVICE_UNAVAILABLE",
                ) from e
            elif "token" in error_str and "limit" in error_str:
                # 토큰 한도 초과
                logger.error(f"토큰 한도 초과: {str(e)}")
                raise AIGenerationFailedException(
                    detail="입력 텍스트가 너무 깁니다. 더 짧은 내용으로 다시 시도해주세요.",
                    error_type="TOKEN_LIMIT_ERROR",
                ) from e
            else:
                # 기타 AI 생성 오류
                logger.error(f"AI 생성 오류: {str(e)}")
                raise AIGenerationFailedException(
                    detail=f"AI 텍스트 생성 중 오류가 발생했습니다: {str(e)}",
                    error_type="GENERATION_ERROR",
                ) from e

    async def stream_regenerate_by_session_id(self, user_id: UUID, session_id: str):
        """세션 ID로 이전 요청 정보를 가져와서 스트리밍 재생성"""
        try:
            logger.info(
                f"재생성 스트리밍 시작: session_id={session_id}, user_id={user_id}"
            )

            # 해당 세션의 가장 최근 로그 조회
            statement = (
                select(AIUsageLog)
                .where(AIUsageLog.session_id == session_id)
                .where(AIUsageLog.user_id == user_id)
                .where(AIUsageLog.api_type == "integrated_analysis")
                .order_by(AIUsageLog.created_at.desc())
                .limit(1)
            )

            result = self.session.execute(statement)
            last_log = result.scalar_one_or_none()

            if not last_log:
                error_data = {
                    "type": "error",
                    "error": f"세션 ID {session_id}에 해당하는 로그를 찾을 수 없습니다.",
                }
                yield json.dumps(error_data, ensure_ascii=False)
                return

            # 현재 세션의 총 재생성 횟수 확인 (5회 제한)
            session_logs_count = self.session.execute(
                select(func.count(AIUsageLog.id))
                .where(AIUsageLog.session_id == session_id)
                .where(AIUsageLog.api_type == "integrated_analysis")
            ).scalar()

            if session_logs_count >= 5:
                error_data = {
                    "type": "error",
                    "error": "재생성 횟수가 5회를 초과했습니다.",
                    "session_id": session_id,
                    "current_count": session_logs_count,
                }
                yield json.dumps(error_data, ensure_ascii=False)
                return

            # 이전 요청 데이터 복원
            import json as json_lib

            original_request_data = (
                json_lib.loads(last_log.request_data)
                if isinstance(last_log.request_data, str)
                else last_log.request_data
            )
            original_request = CreateDiaryRequest(**original_request_data)

            # 새로운 재생성 횟수로 설정
            new_regeneration_count = session_logs_count + 1

            # 초기 메타데이터 전송
            initial_data = {
                "type": "start",
                "session_id": session_id,
                "regeneration_count": new_regeneration_count,
            }
            yield json.dumps(initial_data, ensure_ascii=False)

            # 스트리밍으로 텍스트 생성 (기존 stream_ai_text와 동일한 로직)
            collected_text = ""
            total_tokens = 0
            chunk_index = 0

            async for text_chunk in self._stream_complete_analysis(
                original_request.prompt, original_request.style, original_request.length
            ):
                if isinstance(text_chunk, dict) and "tokens_used" in text_chunk:
                    total_tokens = text_chunk["tokens_used"]
                    continue

                collected_text += text_chunk
                chunk_data = {
                    "type": "content",
                    "content": text_chunk,
                    "accumulated": collected_text,
                    "timestamp": int(time.time() * 1000),
                    "chunk_index": chunk_index,
                }
                chunk_index += 1
                yield json.dumps(chunk_data, ensure_ascii=False)

            # 완료 후 분석 결과 처리
            generated_text = collected_text.strip()

            # 생성된 텍스트에 대해 별도로 감정 분석과 키워드 추출
            try:
                # 간단한 감정 분석 (기본값 사용)
                emotion = "평온"
                # 간단한 키워드 추출 (원본 프롬프트에서)
                keywords = (
                    original_request.prompt.split()[:5]
                    if original_request.prompt
                    else []
                )
            except Exception as e:
                logger.warning(f"재생성 스트리밍 후 분석 실패: {str(e)}")
                emotion = "평온"
                keywords = []

            # 재생성 스트리밍 로그 저장
            ai_usage_log = AIUsageLog(
                user_id=user_id,
                api_type="integrated_analysis",
                session_id=session_id,
                request_data=original_request_data,
                response_data={
                    "ai_generated_text": generated_text,
                    "emotion": emotion,
                    "keywords": keywords,
                    "style": original_request.style,
                    "length": original_request.length,
                },
                tokens_used=total_tokens,
                regeneration_count=new_regeneration_count,
            )
            self.session.add(ai_usage_log)
            self.session.commit()

            # 완료 메타데이터 전송
            final_data = {
                "type": "complete",
                "emotion": emotion,
                "keywords": keywords,
                "generated_text": generated_text,
                "tokens_used": total_tokens,
                "session_id": session_id,
                "regeneration_count": new_regeneration_count,
            }
            yield json.dumps(final_data, ensure_ascii=False)

            logger.info(
                f"재생성 스트리밍 완료: session_id={session_id}, tokens={total_tokens}"
            )

        except Exception as e:
            logger.error(
                f"재생성 스트리밍 실패: session_id={session_id}, error={str(e)}"
            )
            error_data = {
                "type": "error",
                "error": f"재생성 중 오류가 발생했습니다: {str(e)}",
            }
            yield json.dumps(error_data, ensure_ascii=False)

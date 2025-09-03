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
import asyncio

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

        import os

        from openai import AsyncOpenAI

        self._openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

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

            # 완료 후 분석 결과 처리 (평문 텍스트)
            generated_text = collected_text.strip()

            # 생성된 텍스트에 대해 별도로 감정 분석과 키워드 추출
            try:
                # 통합 분석을 통한 감정 분석 및 키워드 추출
                analysis_result = await self._integrated_analysis(
                    data.prompt, data.style, data.length
                )
                emotion = analysis_result["emotion"]
                keywords = analysis_result["keywords"]
                logger.info(f"스트리밍 후 감정 분석 완료: emotion='{emotion}', keywords={keywords}")

            except Exception as e:
                logger.warning(f"스트리밍 후 분석 실패: {str(e)}")
                # Fallback: 키워드 기반 감정 분석
                emotion = self._analyze_emotion_from_keywords(data.prompt)
                keywords = self._extract_emotion_keywords_fallback(data.prompt)
                logger.info(f"Fallback 감정 분석: emotion='{emotion}', keywords={keywords}")

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
                style, {"name": "단편글", "desc": "자연스럽고 따뜻한 문체로 사용자의 감정을 잘 표현해주세요."}
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

            # 재시도 로직 추가
            max_retries = 3
            retry_delay = 1  # 초기 지연 시간 (초)

            for attempt in range(max_retries):
                try:
                    stream = await self._openai_client.chat.completions.create(
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

                            yield content

                    # 성공적으로 완료되면 루프 종료
                    break

                except Exception as e:
                    error_message = str(e)
                    logger.warning(f"OpenAI API 호출 실패 (시도 {attempt + 1}/{max_retries}): {error_message}")

                    # 마지막 시도이거나 재시도할 수 없는 오류인 경우
                    if attempt == max_retries - 1 or "rate limit" not in error_message.lower():
                        logger.error(f"스트리밍 AI 분석 실패: {error_message}")
                        raise

                    # 재시도 가능한 오류인 경우 지연 후 재시도
                    await asyncio.sleep(retry_delay * (2 ** attempt))  # 지수 백오프
                    logger.info(f"재시도 중... ({retry_delay * (2 ** attempt)}초 후)")

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

            system_message = f"""당신은 감정 분석 전문가입니다. 주어진 텍스트의 감정을 정확히 분석하세요.

**감정 분류 (반드시 다음 중 하나만 선택):**
- 행복: 기쁨, 만족, 희망, 긍정적
- 슬픔: 우울, 절망, 아쉬움, 상실감, 눈물
- 화남: 분노, 짜증, 불만, 억울함, 격분
- 불안: 걱정, 두려움, 긴장, 초조함, 불안정함
- 평온: 차분함, 안정감, 편안함 (감정이 불분명할 때만)

**강제 분류 규칙:**
- "화가 난다" 또는 "짜증" → 반드시 "화남"
- "슬프다" 또는 "우울" → 반드시 "슬픔"
- "걱정" 또는 "불안" → 반드시 "불안"
- "기쁘다" 또는 "행복" → 반드시 "행복"

**키워드 추출 우선순위 (감정 분석 가능한 키워드 우선):**
1. **감정 관련 키워드**: 감정을 유발하거나 표현하는 단어/구절 (예: "스트레스", "기대", "실망", "만족", "걱정거리")
2. **상황/경험 키워드**: 구체적인 상황이나 경험을 나타내는 단어 (예: "시험", "면접", "여행", "이별", "취업")
3. **인물/관계 키워드**: 사람이나 관계를 나타내는 단어 (예: "가족", "친구", "상사", "연인")
4. **장소/환경 키워드**: 장소나 환경을 나타내는 단어 (예: "회사", "학교", "집", "카페")
5. **시간/시점 키워드**: 시간이나 시점을 나타내는 단어 (예: "아침", "저녁", "주말", "휴가")

**작업:**
1. 감정 분석 (위 규칙 적용)
2. 키워드 추출 (위 우선순위에 따라 감정 분석 가능한 키워드 5개 추출)
3. 글귀 생성 ({style_guide["name"]} 문체, {length_guide["name"]} 길이)

**응답 형식 (JSON만):**
{{
    "emotion": "감정명",
    "keywords": ["키워드1", "키워드2", "키워드3", "키워드4", "키워드5"],
    "generated_text": "생성된 글귀"
}}"""

            messages = [
                {"role": "system", "content": system_message},
                {"role": "user", "content": f"사용자 입력: {prompt}"},
            ]

            # 재시도 로직 추가
            max_retries = 3
            retry_delay = 1  # 초기 지연 시간 (초)

            for attempt in range(max_retries):
                try:
                    client = get_openai_client()
                    response = await client.async_chat_completion(
                        messages=messages, max_completion_tokens=500
                    )
                    logger.info(f"OpenAI API 응답: {response}")
                    logger.info(f"원본 프롬프트: {prompt}")
                    logger.info(f"AI 응답 내용: {response.get('content', '')}")

                    # 성공적으로 완료되면 루프 종료
                    break

                except Exception as e:
                    error_message = str(e)
                    logger.warning(f"OpenAI API 호출 실패 (시도 {attempt + 1}/{max_retries}): {error_message}")

                    # 마지막 시도이거나 재시도할 수 없는 오류인 경우
                    if attempt == max_retries - 1:
                        logger.error(f"통합 AI 분석 실패: {error_message}")
                        raise

                    # 재시도 가능한 오류인 경우 지연 후 재시도
                    await asyncio.sleep(retry_delay * (2 ** attempt))  # 지수 백오프
                    logger.info(f"재시도 중... ({retry_delay * (2 ** attempt)}초 후)")

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

                                # 감정 분석 결과 검증 및 수정
                emotion = result.get("emotion", "").strip()
                logger.info(f"AI 원본 감정 응답: '{emotion}' (타입: {type(emotion)})")
                logger.info(f"원본 프롬프트: '{prompt}'")

                # AI가 잘못된 감정을 반환한 경우 키워드 기반으로 재분석
                if emotion not in ["행복", "슬픔", "화남", "불안", "평온"]:
                    logger.warning(f"AI가 잘못된 감정을 반환: '{emotion}', 키워드 기반 재분석 시도")
                    emotion = self._analyze_emotion_from_keywords(prompt)
                    logger.info(f"키워드 기반 재분석 결과: '{emotion}'")
                # AI가 "평온"을 반환했지만 명확한 감정 키워드가 있는 경우 재분석
                elif emotion == "평온" and self._has_strong_emotion_keywords(prompt):
                    logger.warning(f"AI가 '평온'을 반환했지만 강한 감정 키워드 감지, 키워드 기반 재분석 시도")
                    emotion = self._analyze_emotion_from_keywords(prompt)
                    logger.info(f"키워드 기반 재분석 결과: '{emotion}'")
                else:
                    logger.info(f"AI 감정 분석 유효: '{emotion}'")

                return {
                    "emotion": emotion,
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
                # 통합 분석을 통한 감정 분석 및 키워드 추출
                analysis_result = await self._integrated_analysis(
                    original_request.prompt, original_request.style, original_request.length
                )
                emotion = analysis_result["emotion"]
                keywords = analysis_result["keywords"]
                logger.info(f"재생성 후 감정 분석 완료: emotion='{emotion}', keywords={keywords}")

            except Exception as e:
                logger.warning(f"재생성 스트리밍 후 분석 실패: {str(e)}")
                # Fallback: 키워드 기반 감정 분석
                emotion = self._analyze_emotion_from_keywords(original_request.prompt)
                keywords = self._extract_emotion_keywords_fallback(original_request.prompt)
                logger.info(f"재생성 Fallback 감정 분석: emotion='{emotion}', keywords={keywords}")

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

    def _analyze_emotion_from_keywords(self, text: str) -> str:
        """키워드 기반 감정 분석 (AI 실패 시 fallback)"""
        text_lower = text.lower()
        logger.info(f"키워드 기반 분석 시작: '{text}' -> '{text_lower}'")

        # 화남 키워드
        anger_keywords = ["화가 난다", "짜증", "분노", "억울", "격분", "열받다", "빡친다", "화나다", "화남"]
        anger_matches = [keyword for keyword in anger_keywords if keyword in text_lower]
        if anger_matches:
            logger.info(f"화남 키워드 매칭: {anger_matches}")
            return "화남"

                # 슬픔 키워드
        sadness_keywords = ["슬프다", "우울", "눈물", "아쉽다", "서운", "울고 싶다", "힘들다", "슬픔"]
        sadness_matches = [keyword for keyword in sadness_keywords if keyword in text_lower]
        if sadness_matches:
            logger.info(f"슬픔 키워드 매칭: {sadness_matches}")
            return "슬픔"

        # 불안 키워드
        anxiety_keywords = ["걱정", "불안", "두렵다", "초조", "긴장", "무서워", "떨린다", "조마조마", "불안정"]
        anxiety_matches = [keyword for keyword in anxiety_keywords if keyword in text_lower]
        if anxiety_matches:
            logger.info(f"불안 키워드 매칭: {anxiety_matches}")
            return "불안"

        # 행복 키워드
        happiness_keywords = ["기쁘다", "행복", "좋다", "즐겁다", "즐거웠다", "신나다", "뿌듯하다", "웃음", "행복하다"]
        happiness_matches = [keyword for keyword in happiness_keywords if keyword in text_lower]
        if happiness_matches:
            logger.info(f"행복 키워드 매칭: {happiness_matches}")
            return "행복"

        # 평온 키워드
        peaceful_keywords = ["편안하다", "차분하다", "안정적", "조용하다", "평화롭다", "고요하다", "만족"]
        peaceful_matches = [keyword for keyword in peaceful_keywords if keyword in text_lower]
        if peaceful_matches:
            logger.info(f"평온 키워드 매칭: {peaceful_matches}")
            return "평온"

        # 기본값: 평온
        logger.info("키워드 매칭 없음, 기본값 평온 반환")
        return "평온"

    def _has_strong_emotion_keywords(self, text: str) -> bool:
        """강한 감정 키워드가 있는지 확인"""
        text_lower = text.lower()

        # 모든 강한 감정 키워드 수집
        strong_keywords = [
            "화가 난다", "짜증", "분노", "억울", "격분", "열받다", "빡친다", "화나다", "화남",
            "슬프다", "우울", "눈물", "아쉽다", "서운", "울고 싶다", "힘들다", "슬픔",
            "걱정", "불안", "두렵다", "초조", "긴장", "무서워", "떨린다", "조마조마", "불안정",
            "기쁘다", "행복", "좋다", "즐겁다", "즐거웠다", "신나다", "뿌듯하다", "웃음", "행복하다"
        ]

        has_strong_keyword = any(keyword in text_lower for keyword in strong_keywords)
        logger.info(f"강한 감정 키워드 감지: {has_strong_keyword}")
        return has_strong_keyword

    def _extract_emotion_keywords_fallback(self, text: str) -> list[str]:
        """감정 분석 가능한 키워드를 우선적으로 추출하는 fallback 메서드"""
        if not text:
            return []
        
        # 감정 관련 키워드 사전
        emotion_keywords = {
            "감정_긍정": ["기쁨", "행복", "만족", "뿌듯", "신남", "즐거움", "희망", "기대", "설렘", "웃음"],
            "감정_부정": ["슬픔", "우울", "실망", "아쉬움", "서운", "힘듦", "절망", "눈물", "울음", "상실감"],
            "감정_화남": ["화남", "분노", "짜증", "억울", "격분", "열받음", "불만", "빡침", "화가남"],
            "감정_불안": ["걱정", "불안", "두려움", "초조", "긴장", "무서움", "떨림", "조마조마", "불안정"],
            "감정_평온": ["편안", "차분", "안정", "조용", "평화", "고요", "만족", "평온"],
        }
        
        # 상황/경험 키워드
        situation_keywords = [
            "시험", "면접", "취업", "이별", "만남", "여행", "휴가", "출장", "회의", "프로젝트",
            "결혼", "이사", "전학", "졸업", "입학", "취직", "퇴사", "승진", "해고", "사직",
            "병원", "치료", "수술", "회복", "건강", "운동", "다이어트", "요리", "쇼핑", "영화"
        ]
        
        # 인물/관계 키워드
        relationship_keywords = [
            "가족", "부모", "어머니", "아버지", "형제", "자매", "친구", "동료", "상사", "부하",
            "연인", "남자친구", "여자친구", "남편", "아내", "선생님", "학생", "의사", "간호사"
        ]
        
        # 장소/환경 키워드
        place_keywords = [
            "회사", "학교", "집", "카페", "식당", "병원", "공원", "도서관", "영화관", "쇼핑몰",
            "지하철", "버스", "택시", "차", "비행기", "기차", "호텔", "펜션", "해변", "산"
        ]
        
        # 시간/시점 키워드
        time_keywords = [
            "아침", "점심", "저녁", "밤", "새벽", "주말", "평일", "휴일", "휴가", "방학",
            "봄", "여름", "가을", "겨울", "월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"
        ]
        
        # 모든 키워드를 하나의 리스트로 통합 (우선순위 순)
        all_keywords = []
        for category in emotion_keywords.values():
            all_keywords.extend(category)
        all_keywords.extend(situation_keywords)
        all_keywords.extend(relationship_keywords)
        all_keywords.extend(place_keywords)
        all_keywords.extend(time_keywords)
        
        # 텍스트에서 키워드 찾기
        found_keywords = []
        text_lower = text.lower()
        
        # 우선순위에 따라 키워드 검색
        for keyword in all_keywords:
            if keyword in text_lower and keyword not in found_keywords:
                found_keywords.append(keyword)
                if len(found_keywords) >= 5:  # 최대 5개
                    break
        
        # 키워드가 5개 미만인 경우, 나머지는 일반 명사로 채움
        if len(found_keywords) < 5:
            # 간단한 명사 추출 (띄어쓰기로 분리된 단어 중 2글자 이상)
            words = text.split()
            for word in words:
                if len(word) >= 2 and word not in found_keywords and len(found_keywords) < 5:
                    found_keywords.append(word)
        
        logger.info(f"Fallback 키워드 추출 결과: {found_keywords}")
        return found_keywords[:5]

    async def _integrated_analysis(
        self, prompt: str, style: str, length: str
    ) -> dict[str, Any]:
        """
        통합 분석을 통한 감정 분석 및 키워드 추출 (스트리밍 후 분석용)
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

            system_message = f"""당신은 감정 분석 전문가입니다. 주어진 텍스트의 감정을 정확히 분석하세요.

**감정 분류 (반드시 다음 중 하나만 선택):**
- 행복: 기쁨, 만족, 희망, 긍정적
- 슬픔: 우울, 절망, 아쉬움, 상실감, 눈물
- 화남: 분노, 짜증, 불만, 억울함, 격분
- 불안: 걱정, 두려움, 긴장, 초조함, 불안정함
- 평온: 차분함, 안정감, 편안함 (감정이 불분명할 때만)

**강제 분류 규칙:**
- "화가 난다" 또는 "짜증" → 반드시 "화남"
- "슬프다" 또는 "우울" → 반드시 "슬픔"
- "걱정" 또는 "불안" → 반드시 "불안"
- "기쁘다" 또는 "행복" → 반드시 "행복"

**키워드 추출 우선순위 (감정 분석 가능한 키워드 우선):**
1. **감정 관련 키워드**: 감정을 유발하거나 표현하는 단어/구절 (예: "스트레스", "기대", "실망", "만족", "걱정거리")
2. **상황/경험 키워드**: 구체적인 상황이나 경험을 나타내는 단어 (예: "시험", "면접", "여행", "이별", "취업")
3. **인물/관계 키워드**: 사람이나 관계를 나타내는 단어 (예: "가족", "친구", "상사", "연인")
4. **장소/환경 키워드**: 장소나 환경을 나타내는 단어 (예: "회사", "학교", "집", "카페")
5. **시간/시점 키워드**: 시간이나 시점을 나타내는 단어 (예: "아침", "저녁", "주말", "휴가")

**작업:**
1. 감정 분석 (위 규칙 적용)
2. 키워드 추출 (위 우선순위에 따라 감정 분석 가능한 키워드 5개 추출)

**응답 형식 (JSON만):**
{{
    "emotion": "감정명",
    "keywords": ["키워드1", "키워드2", "키워드3", "키워드4", "키워드5"]
}}"""

            messages = [
                {"role": "system", "content": system_message},
                {"role": "user", "content": f"사용자 입력: {prompt}"},
            ]

            # 재시도 로직 추가
            max_retries = 3
            retry_delay = 1  # 초기 지연 시간 (초)

            for attempt in range(max_retries):
                try:
                    client = get_openai_client()
                    response = await client.async_chat_completion(
                        messages=messages, max_completion_tokens=200
                    )
                    logger.info(f"통합 분석 OpenAI API 응답: {response}")

                    # 성공적으로 완료되면 루프 종료
                    break

                except Exception as e:
                    error_message = str(e)
                    logger.warning(f"통합 분석 OpenAI API 호출 실패 (시도 {attempt + 1}/{max_retries}): {error_message}")

                    # 마지막 시도이거나 재시도할 수 없는 오류인 경우
                    if attempt == max_retries - 1:
                        logger.error(f"통합 분석 실패: {error_message}")
                        raise

                    # 재시도 가능한 오류인 경우 지연 후 재시도
                    await asyncio.sleep(retry_delay * (2 ** attempt))  # 지수 백오프
                    logger.info(f"재시도 중... ({retry_delay * (2 ** attempt)}초 후)")

            # JSON 파싱
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

                # 감정 분석 결과 검증 및 수정
                emotion = result.get("emotion", "").strip()
                logger.info(f"통합 분석 AI 원본 감정 응답: '{emotion}' (타입: {type(emotion)})")

                # AI가 잘못된 감정을 반환한 경우 키워드 기반으로 재분석
                if emotion not in ["행복", "슬픔", "화남", "불안", "평온"]:
                    logger.warning(f"통합 분석 AI가 잘못된 감정을 반환: '{emotion}', 키워드 기반 재분석 시도")
                    emotion = self._analyze_emotion_from_keywords(prompt)
                    logger.info(f"통합 분석 키워드 기반 재분석 결과: '{emotion}'")
                # AI가 "평온"을 반환했지만 명확한 감정 키워드가 있는 경우 재분석
                elif emotion == "평온" and self._has_strong_emotion_keywords(prompt):
                    logger.warning(f"통합 분석 AI가 '평온'을 반환했지만 강한 감정 키워드 감지, 키워드 기반 재분석 시도")
                    emotion = self._analyze_emotion_from_keywords(prompt)
                    logger.info(f"통합 분석 키워드 기반 재분석 결과: '{emotion}'")
                else:
                    logger.info(f"통합 분석 AI 감정 분석 유효: '{emotion}'")

                return {
                    "emotion": emotion,
                    "keywords": result.get("keywords", [])[:5],
                }

            except (json.JSONDecodeError, ValueError) as e:
                logger.error(f"통합 분석 JSON 파싱 실패: {result_json}, 오류: {str(e)}")
                # 파싱 실패 시 fallback
                emotion = self._analyze_emotion_from_keywords(prompt)
                keywords = self._extract_emotion_keywords_fallback(prompt)
                return {
                    "emotion": emotion,
                    "keywords": keywords,
                }

        except Exception as e:
            logger.error(f"통합 분석 실패: {str(e)}")
            # 최종 fallback
            emotion = self._analyze_emotion_from_keywords(prompt)
            keywords = self._extract_emotion_keywords_fallback(prompt)
            return {
                "emotion": emotion,
                "keywords": keywords,
            }

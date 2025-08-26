"""
애플리케이션 스케줄러 설정
백그라운드 작업 및 주기적 작업을 관리하는 중앙 스케줄러 설정
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class AppScheduler:
    """애플리케이션 스케줄러 관리 클래스"""

    _instance: Optional["AppScheduler"] = None
    _scheduler = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, "initialized"):
            self.initialized = True
            self._scheduler = None

    @property
    def scheduler(self):
        """스케줄러 인스턴스 반환"""
        return self._scheduler

    def setup_scheduler(self, scheduler_type: str = "apscheduler"):
        """
        스케줄러 설정 및 초기화

        Args:
            scheduler_type: 스케줄러 타입 ("apscheduler", "celery")
        """
        try:
            if scheduler_type == "apscheduler":
                self._setup_apscheduler()
            elif scheduler_type == "celery":
                self._setup_celery()
            else:
                logger.warning(f"지원하지 않는 스케줄러 타입: {scheduler_type}")

        except Exception as e:
            logger.error(f"스케줄러 설정 실패: {str(e)}")

    def _setup_apscheduler(self):
        """APScheduler 설정"""
        try:
            from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED
            from apscheduler.executors.asyncio import AsyncIOExecutor
            from apscheduler.jobstores.memory import MemoryJobStore
            from apscheduler.schedulers.asyncio import AsyncIOScheduler

            # 스케줄러 설정
            jobstores = {
                "default": MemoryJobStore(),
            }
            executors = {
                "default": AsyncIOExecutor(),
            }
            job_defaults = {"coalesce": True, "max_instances": 1}

            self._scheduler = AsyncIOScheduler(
                jobstores=jobstores,
                executors=executors,
                job_defaults=job_defaults,
                timezone="UTC",
            )

            # 이벤트 리스너 추가
            self._scheduler.add_listener(
                self._job_listener, EVENT_JOB_EXECUTED | EVENT_JOB_ERROR
            )

            # 다이어리 리마인더 작업 추가
            self._add_diary_reminder_job()

            logger.info("APScheduler가 성공적으로 설정되었습니다.")

        except ImportError:
            logger.error("APScheduler가 설치되지 않았습니다. pip install apscheduler 를 실행해주세요.")
        except Exception as e:
            logger.error(f"APScheduler 설정 실패: {str(e)}")

    def _setup_celery(self):
        """Celery 설정 (향후 구현)"""
        logger.info("Celery 스케줄러는 아직 구현되지 않았습니다.")

    def _add_diary_reminder_job(self):
        """다이어리 리마인더 작업 추가"""
        try:
            from apscheduler.triggers.cron import CronTrigger

            from app.services.diary_reminder_scheduler import DiaryReminderScheduler

            self._scheduler.add_job(
                DiaryReminderScheduler.process_diary_reminders,
                trigger=CronTrigger(minute="*/10"),  # 매 10분마다 실행
                id="diary_reminder_job",
                name="개인화된 다이어리 리마인더 발송",
                replace_existing=True,
            )

            logger.info("다이어리 리마인더 작업이 스케줄러에 추가되었습니다.")

        except Exception as e:
            logger.error(f"다이어리 리마인더 작업 추가 실패: {str(e)}")

    def _job_listener(self, event):
        """작업 실행 결과를 로깅하는 이벤트 리스너"""
        if event.exception:
            logger.error(f"작업 실행 실패 - {event.job_id}: {event.exception}")
        else:
            logger.debug(f"작업 실행 완료 - {event.job_id}")

    def start(self):
        """스케줄러 시작"""
        if self._scheduler is None:
            logger.warning("스케줄러가 설정되지 않았습니다.")
            return

        try:
            if not self._scheduler.running:
                self._scheduler.start()
                logger.info("스케줄러가 시작되었습니다.")
            else:
                logger.warning("스케줄러가 이미 실행 중입니다.")
        except Exception as e:
            logger.error(f"스케줄러 시작 실패: {str(e)}")

    def shutdown(self):
        """스케줄러 종료"""
        if self._scheduler is None:
            return

        try:
            if self._scheduler.running:
                self._scheduler.shutdown(wait=False)
                logger.info("스케줄러가 종료되었습니다.")
        except Exception as e:
            logger.error(f"스케줄러 종료 실패: {str(e)}")

    def get_jobs(self):
        """현재 등록된 작업 목록 반환"""
        if self._scheduler is None:
            return []

        return self._scheduler.get_jobs()

    def add_job(self, func, trigger, job_id, **kwargs):
        """새 작업 추가"""
        if self._scheduler is None:
            logger.warning("스케줄러가 설정되지 않았습니다.")
            return None

        try:
            job = self._scheduler.add_job(
                func, trigger=trigger, id=job_id, replace_existing=True, **kwargs
            )
            logger.info(f"작업 추가됨: {job_id}")
            return job
        except Exception as e:
            logger.error(f"작업 추가 실패 ({job_id}): {str(e)}")
            return None

    def remove_job(self, job_id):
        """작업 제거"""
        if self._scheduler is None:
            logger.warning("스케줄러가 설정되지 않았습니다.")
            return

        try:
            self._scheduler.remove_job(job_id)
            logger.info(f"작업 제거됨: {job_id}")
        except Exception as e:
            logger.error(f"작업 제거 실패 ({job_id}): {str(e)}")


# 전역 스케줄러 인스턴스
app_scheduler = AppScheduler()


def get_scheduler() -> AppScheduler:
    """스케줄러 인스턴스 반환"""
    return app_scheduler


def setup_scheduler(scheduler_type: str = "apscheduler"):
    """스케줄러 설정 함수"""
    app_scheduler.setup_scheduler(scheduler_type)


def start_scheduler():
    """스케줄러 시작 함수"""
    app_scheduler.start()


def shutdown_scheduler():
    """스케줄러 종료 함수"""
    app_scheduler.shutdown()

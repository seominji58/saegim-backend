# 스케줄러 통합 안내

개인화된 다이어리 리마인더 스케줄러를 애플리케이션에 통합하는 방법입니다.

## 1. 의존성 설치

```bash
pip install apscheduler
```

## 2. 애플리케이션 시작 시 스케줄러 설정

### main.py에 추가할 코드

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.core.scheduler import setup_scheduler, start_scheduler, shutdown_scheduler

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 애플리케이션 시작 시
    try:
        # 스케줄러 설정 및 시작
        setup_scheduler("apscheduler")
        start_scheduler()
        print("✅ 다이어리 리마인더 스케줄러가 시작되었습니다.")
    except Exception as e:
        print(f"⚠️ 스케줄러 시작 실패: {e}")

    yield

    # 애플리케이션 종료 시
    try:
        shutdown_scheduler()
        print("✅ 스케줄러가 정상적으로 종료되었습니다.")
    except Exception as e:
        print(f"⚠️ 스케줄러 종료 실패: {e}")

# FastAPI 앱 생성 시 lifespan 설정
app = FastAPI(
    title="Saegim Backend API",
    version="1.0.0",
    lifespan=lifespan  # 이 부분 추가
)
```

### 기존 앱 설정이 있는 경우

기존 `main.py`나 `app.py`에서 스케줄러만 추가하는 방법:

```python
from app.core.scheduler import setup_scheduler, start_scheduler

# 애플리케이션 초기화 후 어디선가 호출
def initialize_scheduler():
    """스케줄러 초기화"""
    setup_scheduler("apscheduler")
    start_scheduler()

# 애플리케이션 시작 시 호출
initialize_scheduler()
```

## 3. 스케줄러 작동 확인

### 로그 확인
애플리케이션 로그에서 다음과 같은 메시지를 확인하세요:

```
INFO:app.core.scheduler:APScheduler가 성공적으로 설정되었습니다.
INFO:app.core.scheduler:다이어리 리마인더 작업이 스케줄러에 추가되었습니다.
INFO:app.core.scheduler:스케줄러가 시작되었습니다.
```

### 작업 실행 로그
매 10분마다 다음과 같은 로그가 출력됩니다:

```
INFO:app.services.diary_reminder_scheduler:다이어리 리마인더 처리 시작: 21:00 (mon)
INFO:app.services.diary_reminder_scheduler:시간 21:00, 요일 mon에 알림받을 사용자 3명 조회됨
INFO:app.services.diary_reminder_scheduler:다이어리 리마인더 처리 완료: 성공 2명, 스킵 1명, 실패 0명
```

## 4. 스케줄러 상태 모니터링

### 현재 등록된 작업 확인
```python
from app.core.scheduler import get_scheduler

# 현재 등록된 작업 목록
scheduler = get_scheduler()
jobs = scheduler.get_jobs()
for job in jobs:
    print(f"작업 ID: {job.id}, 다음 실행: {job.next_run_time}")
```

### 새 작업 추가
```python
from apscheduler.triggers.cron import CronTrigger

scheduler = get_scheduler()
scheduler.add_job(
    my_function,
    trigger=CronTrigger(hour=9, minute=0),  # 매일 오전 9시
    job_id="my_daily_job"
)
```

## 5. 트러블슈팅

### 문제 1: ModuleNotFoundError: No module named 'apscheduler'
```bash
pip install apscheduler==3.10.4
```

### 문제 2: 스케줄러 시작 실패
로그에서 구체적인 오류 메시지를 확인하세요. 주로 다음과 같은 이유입니다:
- DB 연결 실패: 데이터베이스가 준비되기 전에 스케줄러 시작
- 권한 문제: 파일 시스템 접근 권한 확인

### 문제 3: 중복 실행
애플리케이션이 여러 프로세스/인스턴스로 실행되는 경우, 각각에서 스케줄러가 시작됩니다.
- 해결책: 분산 환경에서는 하나의 인스턴스에서만 스케줄러 실행
- 또는 Redis/PostgreSQL 기반 JobStore 사용

## 6. 프로덕션 고려사항

### 분산 환경
여러 서버에서 애플리케이션이 실행되는 경우:

```python
# PostgreSQL JobStore 사용
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore

jobstores = {
    'default': SQLAlchemyJobStore(url='postgresql://user:pass@host/dbname')
}
```

### 성능 최적화
- 작업 실행 시간이 긴 경우 별도 워커 프로세스 사용
- 대용량 사용자의 경우 배치 처리 크기 조정

### 모니터링
- 스케줄러 상태를 모니터링하는 헬스 체크 엔드포인트 추가
- 작업 실패 시 알림 시스템 연동

## 7. 테스트

### 수동 테스트
기존 다이어리 리마인더 엔드포인트를 사용하여 테스트:

```bash
curl -X POST "http://localhost:8000/notifications/diary-reminder" \
  -H "Content-Type: application/json" \
  -H "Cookie: your-auth-cookie"
```

### 자동 테스트
스케줄러가 정상 작동하는지 확인하는 테스트 코드:

```python
import pytest
from app.services.diary_reminder_scheduler import DiaryReminderScheduler

@pytest.mark.asyncio
async def test_get_users_for_reminder_time(db_session):
    # 테스트용 사용자와 설정 생성
    # ...

    users = await DiaryReminderScheduler.get_users_for_reminder_time(
        "21:00", "mon", db_session
    )
    assert len(users) > 0
```

## 8. 마이그레이션 가이드

기존 시스템에서 새 스케줄러로 전환:

1. **점진적 전환**: 기존 엔드포인트 유지하며 스케줄러 병행 실행
2. **모니터링**: 두 시스템의 알림 발송 현황 비교
3. **완전 전환**: 기존 시스템 비활성화 후 스케줄러만 사용
4. **롤백 계획**: 문제 발생 시 기존 시스템으로 빠른 복구

---

## 추가 정보

- 스케줄러 설정: `app/core/scheduler.py`
- 리마인더 로직: `app/services/diary_reminder_scheduler.py`
- API 엔드포인트: `app/api/notification.py` (테스트용 수동 발송)
- 사용자 설정: `app/models/fcm.py` (NotificationSettings)

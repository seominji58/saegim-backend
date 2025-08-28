"""
로깅 설정
"""

import contextlib
import locale
import logging
import sys


def setup_logging():
    """로깅 설정"""
    # Windows 환경에서 한글 로그 메시지 처리를 위한 인코딩 설정

    # 시스템 로케일 설정 (Windows에서 한글 지원)
    if sys.platform == "win32":
        with contextlib.suppress(locale.Error):
            # Windows에서 UTF-8 로케일 설정
            locale.setlocale(locale.LC_ALL, "ko_KR.UTF-8")
        with contextlib.suppress(locale.Error):
            # 대안 로케일 시도
            locale.setlocale(locale.LC_ALL, "Korean_Korea.UTF-8")

    # 로깅 핸들러 설정 (기본 stdout 사용)
    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)

    # UTF-8 인코딩을 명시적으로 설정한 포매터
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)

    # 루트 로거 설정
    logging.basicConfig(level=logging.DEBUG, handlers=[handler])

    # 데이터베이스 관련 로거
    db_logger = logging.getLogger("app.db")
    db_logger.setLevel(logging.DEBUG)

    # API 관련 로거
    api_logger = logging.getLogger("app.api")
    api_logger.setLevel(logging.DEBUG)

    # SQLAlchemy 로거
    sql_logger = logging.getLogger("sqlalchemy.engine")
    sql_logger.setLevel(logging.INFO)

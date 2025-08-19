"""
로깅 설정
"""
import logging
import sys

def setup_logging():
    """로깅 설정"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

    # 데이터베이스 관련 로거
    db_logger = logging.getLogger("app.db")
    db_logger.setLevel(logging.DEBUG)

    # API 관련 로거
    api_logger = logging.getLogger("app.api")
    api_logger.setLevel(logging.DEBUG)

    # SQLAlchemy 로거
    sql_logger = logging.getLogger("sqlalchemy.engine")
    sql_logger.setLevel(logging.INFO)

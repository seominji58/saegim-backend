import os
import logging
from typing import Tuple
from sqlmodel import SQLModel, create_engine, Session, text
from sqlalchemy.exc import SQLAlchemyError, OperationalError
from dotenv import load_dotenv

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# .env 파일 로드
load_dotenv()

# 환경 변수에서 데이터베이스 URL 가져오기
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("환경 변수 DATABASE_URL이 설정되지 않았습니다.")

def test_connection() -> Tuple[bool, str]:
    """
    데이터베이스 연결을 테스트합니다.

    Returns:
        Tuple[bool, str]: (성공 여부, 메시지)
    """
    engine = None
    try:
        # 엔진 생성 (SQLModel 사용)
        engine = create_engine(
            DATABASE_URL,
            pool_pre_ping=True,  # 연결이 살아있는지 확인
            pool_recycle=3600    # 1시간마다 연결 재생성
        )
        
        # SQLModel 메타데이터 생성 테스트
        SQLModel.metadata.create_all(engine)
        
        # 연결 테스트
        with Session(engine) as session:
            # 데이터베이스 정보 확인
            result = session.exec(text("SELECT current_database(), current_schema")).first()
            logger.info(f"연결된 데이터베이스: {result[0]}, 스키마: {result[1]}")
            
            # 모든 데이터베이스 목록 확인
            dbs = session.exec(text("SELECT datname FROM pg_database;")).all()
            logger.info("사용 가능한 데이터베이스 목록:")
            for db in dbs:
                logger.info(f"- {db[0]}")
            
            # 테이블 목록 조회
            tables = session.exec(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_type = 'BASE TABLE'
                ORDER BY table_name;
            """)).all()
            logger.info("현재 테이블 목록:")
            for table in tables:
                logger.info(f"- {table[0]}")
            
            # 연결 테스트
            test = session.exec(text("SELECT 1")).first()
            if test is None:
                return False, "데이터베이스 응답이 올바르지 않습니다."
            
            logger.info("데이터베이스 연결 성공!")
            return True, "데이터베이스 연결 성공"
            
    except OperationalError as e:
        error_msg = f"데이터베이스 연결 실패 (연결 오류): {str(e)}"
        logger.error(error_msg)
        return False, error_msg
        
    except SQLAlchemyError as e:
        error_msg = f"데이터베이스 연결 실패 (SQL 오류): {str(e)}"
        logger.error(error_msg)
        return False, error_msg
        
    except Exception as e:
        error_msg = f"데이터베이스 연결 실패 (예상치 못한 오류): {str(e)}"
        logger.error(error_msg)
        return False, error_msg
        
    finally:
        if engine:
            engine.dispose()  # 엔진과 연결된 모든 연결 정리

if __name__ == "__main__":
    print("데이터베이스 연결 테스트를 시작합니다...")
    success, message = test_connection()
    print(f"\n결과: {message}")
    print(f"연결 상태: {'성공' if success else '실패'}\n")
    exit(0 if success else 1)  # 성공 시 0, 실패 시 1 반환

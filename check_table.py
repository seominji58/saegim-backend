#!/usr/bin/env python3
"""
email_verifications 테이블 구조 확인 스크립트
"""

from sqlalchemy import text

from app.db.database import engine


def check_table_structure():
    try:
        with engine.connect() as connection:
            # 테이블 컬럼 확인
            result = connection.execute(
                text(
                    """
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_name = 'email_verifications'
                ORDER BY ordinal_position
            """
                )
            )

            print("📋 email_verifications 테이블 구조:")
            print("-" * 50)
            for row in result:
                print(f"- {row[0]}: {row[1]} (nullable: {row[2]}, default: {row[3]})")

    except Exception as e:
        print(f"❌ 오류 발생: {e}")


if __name__ == "__main__":
    check_table_structure()

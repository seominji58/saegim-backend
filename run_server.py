#!/usr/bin/env python3
"""
한글 인코딩을 위한 환경 변수 설정과 함께 서버 실행
"""

import contextlib
import os
import platform
import subprocess
import sys


def setup_korean_environment():
    """한글 인코딩을 위한 환경 변수 설정"""

    # Windows 환경에서 한글 인코딩 설정
    if platform.system() == "Windows":
        # 시스템 인코딩을 UTF-8로 설정
        os.environ["PYTHONIOENCODING"] = "utf-8"
        os.environ["PYTHONUTF8"] = "1"

        # 콘솔 인코딩 설정
        os.environ["PYTHONLEGACYWINDOWSSTDIO"] = "utf-8"

        # 로케일 설정
        try:
            import locale

            locale.setlocale(locale.LC_ALL, "ko_KR.UTF-8")
        except locale.Error:
            with contextlib.suppress(Exception):
                locale.setlocale(locale.LC_ALL, "Korean_Korea.UTF-8")

    # Unix/Linux 환경에서 한글 인코딩 설정
    else:
        os.environ["LANG"] = "ko_KR.UTF-8"
        os.environ["LC_ALL"] = "ko_KR.UTF-8"
        os.environ["PYTHONIOENCODING"] = "utf-8"

    # FastAPI 관련 인코딩 설정
    os.environ["PYTHONPATH"] = os.path.dirname(os.path.abspath(__file__))

    print("🌐 한글 인코딩 환경 설정 완료")
    print(f"   - PYTHONIOENCODING: {os.environ.get('PYTHONIOENCODING', 'Not set')}")
    print(f"   - PYTHONUTF8: {os.environ.get('PYTHONUTF8', 'Not set')}")
    print(f"   - LANG: {os.environ.get('LANG', 'Not set')}")
    print(f"   - LC_ALL: {os.environ.get('LC_ALL', 'Not set')}")


def run_server():
    """서버 실행"""
    try:
        # uvicorn 명령어 구성
        cmd = [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "0.0.0.0",
            "--port",
            "8000",
            "--reload",
            "--log-level",
            "info",
        ]

        print("🚀 서버 시작 중...")
        print(f"   명령어: {' '.join(cmd)}")

        # 서버 실행
        subprocess.run(cmd, env=os.environ.copy())

    except KeyboardInterrupt:
        print("\n🛑 서버가 중지되었습니다.")
    except Exception as e:
        print(f"❌ 서버 실행 중 오류 발생: {e}")
        sys.exit(1)


if __name__ == "__main__":
    setup_korean_environment()
    run_server()

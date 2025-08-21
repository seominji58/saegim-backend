@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo 🌐 한글 인코딩 환경 설정 중...

:: Python 환경 변수 설정
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
set PYTHONLEGACYWINDOWSSTDIO=utf-8

:: 로케일 설정 (Windows)
set LANG=ko_KR.UTF-8
set LC_ALL=ko_KR.UTF-8

:: FastAPI 관련 설정
set PYTHONPATH=%~dp0

echo ✅ 환경 변수 설정 완료:
echo    - PYTHONIOENCODING: %PYTHONIOENCODING%
echo    - PYTHONUTF8: %PYTHONUTF8%
echo    - LANG: %LANG%
echo    - LC_ALL: %LC_ALL%

echo.
echo 🚀 서버 시작 중...
echo.

:: 가상환경 활성화 (있는 경우)
if exist "venv\Scripts\activate.bat" (
    echo 📦 가상환경 활성화 중...
    call venv\Scripts\activate.bat
)

:: 서버 실행
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --log-level info

pause

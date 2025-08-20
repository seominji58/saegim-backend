"""
환경 변수 설정 헬퍼
"""
import os
from pathlib import Path

def load_env_file():
    """
    .env 파일을 UTF-8로 읽어서 환경 변수로 설정
    """
    env_path = Path('.env')
    if env_path.exists():
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()

# 환경 변수 로드
load_env_file()

"""
새김 백엔드 애플리케이션 패키지
"""

# utils 모듈을 models.utils로 리다이렉트
import sys
from .models import utils
sys.modules['app.utils'] = utils
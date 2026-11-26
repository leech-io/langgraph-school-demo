"""Local configuration and secret-safe messages."""
from dataclasses import dataclass, field
from pathlib import Path
import os
import re
from urllib.parse import unquote
from dotenv import dotenv_values
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[2]

@dataclass(frozen=True)
class Settings:
    database_url: str = field(default='', repr=False)
    model_api_key: str = field(default='', repr=False)
    model_base_url: str = 'https://dashscope.aliyuncs.com/compatible-mode/v1'
    model_name: str = 'qwen3.8-max'
    max_rows: int = 200
    max_queries: int = 10
    max_repairs: int = 2
    timeout_seconds: int = 5

    @classmethod
    def load(cls):
        values = {**dotenv_values(ROOT / '.env'), **os.environ}
        return cls(database_url=values.get('DATABASE_URL',''), model_api_key=values.get('MODEL_API_KEY',''),
                   model_base_url=values.get('MODEL_BASE_URL', cls.model_base_url), model_name=values.get('MODEL_NAME',cls.model_name))

def redact(message, settings):
    result = str(message)
    secrets = [settings.model_api_key, settings.database_url]
    try:
        password = make_url(settings.database_url).password
        if password: secrets.extend([password, unquote(password)])
    except Exception:
        pass
    for secret in sorted((s for s in secrets if s), key=len, reverse=True):
        result = result.replace(secret, '[已隐藏]')
    result = re.sub(r'\b\w+(?:\+\w+)?://[^\s\x22\x27<>]+', '[连接地址已隐藏]', result)
    return re.sub(r'\bsk-[A-Za-z0-9_.-]+', '[API Key已隐藏]', result)

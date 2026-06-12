import os
from pathlib import Path

from dotenv import load_dotenv

from .base import *  # noqa: F403

BASE_DIR = Path(__file__).resolve().parent.parent.parent

load_dotenv(BASE_DIR / '.env')

DEBUG = True

SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', SECRET_KEY)  # noqa: F405

CORS_ALLOWED_ORIGINS = [
    'http://localhost:5173',
]

import os
from pathlib import Path

from dotenv import load_dotenv

from .base import *  # noqa: F403

BASE_DIR = Path(__file__).resolve().parent.parent.parent

load_dotenv(BASE_DIR / '.env')

DEBUG = True

SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', SECRET_KEY)  # noqa: F405

DATABASES = {  # noqa: F405
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': os.getenv('DB_NAME', 'echargesys'),
        'USER': os.getenv('DB_USER', 'root'),
        'PASSWORD': os.getenv('DB_PASSWORD', '123456'),
        'HOST': os.getenv('DB_HOST', '127.0.0.1'),
        'PORT': os.getenv('DB_PORT', '3306'),
        'OPTIONS': {
            'charset': 'utf8mb4',
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
        },
    }
}

CORS_ALLOWED_ORIGINS = [
    'http://localhost:5173',
]

CORS_ALLOW_CREDENTIALS = True

from datetime import datetime, timedelta, timezone

import jwt
from django.conf import settings

from .enums import TokenRole


def create_token(subject_id, role: str, extra=None):
    payload = {
        'sub': str(subject_id),
        'role': role,
        'exp': datetime.now(timezone.utc) + timedelta(seconds=settings.JWT_EXPIRE_SECONDS),
        'iat': datetime.now(timezone.utc),
    }
    if extra:
        payload.update(extra)
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm='HS256')
    if isinstance(token, bytes):
        token = token.decode('utf-8')
    return token


def decode_token(token: str):
    return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=['HS256'])

from .base import *  # noqa: F403

DEBUG = False

SECRET_KEY = 'test-secret-key-not-for-production'  # noqa: F405

DATABASES = {  # noqa: F405
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

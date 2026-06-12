from functools import wraps

from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .auth import decode_token
from .enums import ErrorCode, TokenRole
from .exceptions import AppException
from .responses import error_response


def _extract_bearer_token(request):
    auth_header = request.META.get('HTTP_AUTHORIZATION', '')
    if not auth_header.startswith('Bearer '):
        return None
    return auth_header[7:].strip()


def api_view(methods=None):
    method_list = methods or ['GET']

    def decorator(view_func):
        @csrf_exempt
        @require_http_methods(method_list)
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            try:
                return view_func(request, *args, **kwargs)
            except AppException as exc:
                return error_response(exc.code, exc.message)
            except Exception:
                return error_response(ErrorCode.VALIDATION_ERROR, '服务器内部错误')
        return wrapper
    return decorator


def require_auth(roles=None):
    allowed_roles = set(roles or [])

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            token = _extract_bearer_token(request)
            if not token:
                return error_response(ErrorCode.AUTH_ERROR, '未登录或 token 无效')
            try:
                payload = decode_token(token)
            except Exception:
                return error_response(ErrorCode.AUTH_ERROR, '未登录或 token 已过期')
            role = payload.get('role')
            if allowed_roles and role not in allowed_roles:
                return error_response(ErrorCode.PERMISSION_ERROR, '权限不足')
            request.auth_payload = payload
            request.auth_role = role
            request.auth_subject_id = payload.get('sub')
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def require_user(view_func):
    return require_auth([TokenRole.USER])(view_func)


def require_admin(view_func):
    return require_auth([TokenRole.ADMIN])(view_func)

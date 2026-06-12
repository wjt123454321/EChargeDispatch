import json

from django.http import JsonResponse

from .enums import ErrorCode


def success_response(data=None, message='success'):
    return JsonResponse({'code': ErrorCode.SUCCESS, 'message': message, 'data': data})


def error_response(code: int, message: str, status=200):
    return JsonResponse({'code': code, 'message': message, 'data': None}, status=status)


def parse_json_body(request):
    if not request.body:
        return {}
    try:
        return json.loads(request.body.decode('utf-8'))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None

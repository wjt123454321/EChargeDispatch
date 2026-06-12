from apps.common.decorators import api_view
from apps.common.enums import ErrorCode
from apps.common.exceptions import AppException
from apps.common.responses import parse_json_body, success_response

from .services import AuthService


@api_view(['POST'])
def register(request):
    body = parse_json_body(request)
    if body is None:
        raise AppException(ErrorCode.VALIDATION_ERROR, '参数校验失败')
    data = AuthService.register(
        car_id=body.get('car_id', '').strip(),
        user_name=body.get('user_name', '').strip(),
        car_capacity=body.get('car_capacity'),
        password=body.get('password', ''),
    )
    return success_response(data)


@api_view(['POST'])
def login(request):
    body = parse_json_body(request)
    if body is None:
        raise AppException(ErrorCode.VALIDATION_ERROR, '参数校验失败')
    data = AuthService.login(
        car_id=body.get('car_id', '').strip(),
        password=body.get('password', ''),
    )
    return success_response(data)

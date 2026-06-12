from apps.accounts.services import VehicleService
from apps.common.decorators import api_view, require_admin, require_user
from apps.common.enums import ErrorCode
from apps.common.exceptions import AppException
from apps.common.responses import parse_json_body, success_response

from .services import (
    ChargingRequestService,
    ChargingSessionService,
)


def _get_user_vehicle(request):
    vehicle_id = request.auth_payload.get('vehicle_id')
    vehicle = VehicleService.get_vehicle_for_user(request.auth_subject_id, vehicle_id)
    if not vehicle:
        raise AppException(ErrorCode.USER_NOT_FOUND, '用户不存在')
    return vehicle


@api_view(['POST'])
@require_user
def submit_request(request):
    body = parse_json_body(request) or {}
    vehicle = _get_user_vehicle(request)
    data = ChargingRequestService.submit_request(
        vehicle,
        body.get('request_mode', '').strip(),
        body.get('request_amount'),
    )
    return success_response(data)


@api_view(['PUT'])
@require_user
def update_amount(request):
    body = parse_json_body(request) or {}
    vehicle = _get_user_vehicle(request)
    data = ChargingRequestService.update_amount(vehicle, body.get('amount'))
    return success_response(data)


@api_view(['PUT'])
@require_user
def update_mode(request):
    body = parse_json_body(request) or {}
    vehicle = _get_user_vehicle(request)
    data = ChargingRequestService.update_mode(vehicle, body.get('mode', '').strip())
    return success_response(data)


@api_view(['GET'])
@require_user
def queue_status(request):
    vehicle = _get_user_vehicle(request)
    data = ChargingRequestService.get_queue_status(vehicle)
    return success_response(data)


@api_view(['POST'])
@require_user
def start_charging(request):
    body = parse_json_body(request) or {}
    vehicle = _get_user_vehicle(request)
    pile_id = body.get('pile_id')
    if not pile_id:
        raise AppException(ErrorCode.VALIDATION_ERROR, '参数校验失败')
    data = ChargingSessionService.start_charging(vehicle, int(pile_id))
    return success_response(data)


@api_view(['GET'])
@require_user
def charging_status(request):
    vehicle = _get_user_vehicle(request)
    data = ChargingSessionService.get_charging_status(vehicle)
    return success_response(data)


@api_view(['POST'])
@require_user
def end_charging(request):
    vehicle = _get_user_vehicle(request)
    data = ChargingSessionService.end_charging(vehicle)
    return success_response(data)


@api_view(['DELETE'])
@require_user
def cancel_charging(request):
    vehicle = _get_user_vehicle(request)
    data = ChargingSessionService.cancel_charging(vehicle)
    return success_response(data)


@api_view(['GET'])
@require_admin
def pile_queue(request, pile_id):
    data = ChargingSessionService.pile_queue_detail(int(pile_id))
    return success_response(data)

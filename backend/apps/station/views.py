from apps.common.decorators import api_view, require_admin
from apps.common.responses import parse_json_body, success_response
from apps.operations.services import OperationLogService

from .services import ChargingPileService, StationConfigService


@api_view(['GET', 'PUT'])
@require_admin
def system_config(request):
    if request.method == 'GET':
        config = StationConfigService.get_active_config()
        return success_response(StationConfigService.to_dict(config))
    body = parse_json_body(request) or {}
    data = StationConfigService.update_config(body)
    OperationLogService.log(
        request.auth_subject_id, 'update_config', 'system_config', 'active', str(body)
    )
    return success_response(data)


@api_view(['GET'])
@require_admin
def pile_status(request):
    data = ChargingPileService.list_piles_status()
    return success_response(data)


@api_view(['POST'])
@require_admin
def pile_poweron(request, pile_id):
    data = ChargingPileService.power_on(int(pile_id))
    OperationLogService.log(request.auth_subject_id, 'poweron', 'pile', pile_id, '启动充电桩')
    return success_response(data)


@api_view(['POST'])
@require_admin
def pile_start(request, pile_id):
    data = ChargingPileService.start_pile(int(pile_id))
    OperationLogService.log(request.auth_subject_id, 'start', 'pile', pile_id, '投入运行')
    return success_response(data)


@api_view(['POST'])
@require_admin
def pile_poweroff(request, pile_id):
    data = ChargingPileService.power_off(int(pile_id))
    OperationLogService.log(request.auth_subject_id, 'poweroff', 'pile', pile_id, '关闭充电桩')
    return success_response(data)

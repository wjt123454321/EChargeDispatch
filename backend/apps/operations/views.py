from apps.common.decorators import api_view, require_admin
from apps.common.enums import ErrorCode
from apps.common.exceptions import AppException
from apps.common.responses import parse_json_body, success_response

from .acceptance_service import AcceptanceService
from .services import FaultService, ReportService


@api_view(['POST'])
@require_admin
def fault_report(request):
    body = parse_json_body(request) or {}
    pile_id = body.get('pile_id')
    if not pile_id:
        raise AppException(ErrorCode.VALIDATION_ERROR, '参数校验失败')
    data = FaultService.report_fault(int(pile_id), admin_id=int(request.auth_subject_id))
    return success_response(data)


@api_view(['POST'])
@require_admin
def fault_recover(request):
    body = parse_json_body(request) or {}
    pile_id = body.get('pile_id')
    if not pile_id:
        raise AppException(ErrorCode.VALIDATION_ERROR, '参数校验失败')
    data = FaultService.recover_fault(int(pile_id), admin_id=int(request.auth_subject_id))
    return success_response(data)


@api_view(['GET'])
@require_admin
def fault_list(request):
    data = FaultService.list_faults()
    return success_response(data)


@api_view(['GET'])
@require_admin
def report_stats(request):
    period = request.GET.get('period', 'day')
    date_str = request.GET.get('date')
    if not date_str:
        raise AppException(ErrorCode.VALIDATION_ERROR, '参数校验失败')
    data = ReportService.generate_stats(period, date_str)
    return success_response(data)


@api_view(['GET'])
@require_admin
def acceptance_snapshot(request):
    """验收填表快照：各桩 (车号,已充电量,当前费用) 与等候区列表。"""
    case_time = request.GET.get('case_time')
    data = AcceptanceService.build_snapshot(case_time)
    return success_response(data)

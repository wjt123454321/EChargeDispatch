from apps.common.decorators import api_view, require_user
from apps.common.responses import success_response

from .services import BillingService


@api_view(['GET'])
@require_user
def bill_list(request):
    data = BillingService.list_bills(int(request.auth_subject_id))
    return success_response(data)


@api_view(['GET'])
@require_user
def bill_detail(request, bill_id):
    data = BillingService.get_bill_detail(int(request.auth_subject_id), int(bill_id))
    return success_response(data)


@api_view(['POST'])
@require_user
def bill_pay(request, bill_id):
    data = BillingService.pay_bill(int(request.auth_subject_id), int(bill_id))
    return success_response(data)

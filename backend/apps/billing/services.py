from datetime import date
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.common.enums import ErrorCode, PayStatus, SERVICE_FEE_RATE
from apps.common.exceptions import AppException
from apps.common.utils import calculate_cross_period_fee, generate_no

from .models import Bill, ChargeDetail, TariffPolicy


class BillingService:
    @staticmethod
    def get_active_policy():
        return TariffPolicy.objects.filter(is_active=True).first()

    @staticmethod
    @transaction.atomic
    def create_detail_and_bill(session, request):
        policy = BillingService.get_active_policy()
        charge_amount = session.charged_amount
        charge_fee, _ = calculate_cross_period_fee(session.start_time, session.end_time, charge_amount)
        service_fee = (charge_amount * Decimal(str(SERVICE_FEE_RATE))).quantize(Decimal('0.01'))
        total_fee = (charge_fee + service_fee).quantize(Decimal('0.01'))

        detail = ChargeDetail.objects.create(
            detail_no=generate_no('DET'),
            session=session,
            request=request,
            vehicle=session.vehicle,
            pile=session.pile,
            tariff_policy=policy,
            charge_amount=charge_amount,
            charge_duration=session.charged_duration,
            start_time=session.start_time,
            end_time=session.end_time,
            charge_fee=charge_fee,
            service_fee=service_fee,
            total_fee=total_fee,
        )

        bill = Bill.objects.create(
            bill_no=generate_no('BILL'),
            user=request.user,
            bill_date=date.today(),
            total_charge_amount=charge_amount,
            total_charge_duration=session.charged_duration,
            total_charge_fee=charge_fee,
            total_service_fee=service_fee,
            total_fee=total_fee,
            pay_status=PayStatus.UNPAID,
        )
        detail.bill = bill
        detail.save(update_fields=['bill'])
        return {'bill_id': bill.id, 'detail_id': detail.id, 'total_fee': float(total_fee)}

    @staticmethod
    def list_bills(user_id):
        bills = Bill.objects.filter(user_id=user_id).order_by('-created_at')
        return [
            {
                'bill_id': b.id,
                'bill_no': b.bill_no,
                'bill_date': b.bill_date.isoformat(),
                'total_fee': float(b.total_fee),
                'pay_status': b.pay_status,
                'created_at': b.created_at.isoformat(),
            }
            for b in bills
        ]

    @staticmethod
    def get_bill_detail(user_id, bill_id):
        bill = Bill.objects.filter(id=bill_id, user_id=user_id).first()
        if not bill:
            raise AppException(ErrorCode.BILL_NOT_FOUND, '账单不存在')
        details = ChargeDetail.objects.filter(bill=bill).select_related('pile', 'vehicle', 'session')
        detail_list = []
        for d in details:
            detail_list.append({
                'detail_no': d.detail_no,
                'generated_at': d.generated_at.isoformat(),
                'pile_no': d.pile.pile_no,
                'charge_amount': float(d.charge_amount),
                'charge_duration': float(d.charge_duration),
                'start_time': d.start_time.isoformat(),
                'end_time': d.end_time.isoformat(),
                'charge_fee': float(d.charge_fee),
                'service_fee': float(d.service_fee),
                'total_fee': float(d.total_fee),
            })
        return {
            'bill_id': bill.id,
            'bill_no': bill.bill_no,
            'bill_date': bill.bill_date.isoformat(),
            'total_charge_amount': float(bill.total_charge_amount),
            'total_charge_duration': float(bill.total_charge_duration),
            'total_charge_fee': float(bill.total_charge_fee),
            'total_service_fee': float(bill.total_service_fee),
            'total_fee': float(bill.total_fee),
            'pay_status': bill.pay_status,
            'details': detail_list,
        }

    @staticmethod
    def pay_bill(user_id, bill_id):
        bill = Bill.objects.filter(id=bill_id, user_id=user_id).first()
        if not bill:
            raise AppException(ErrorCode.BILL_NOT_FOUND, '账单不存在')
        if bill.pay_status == PayStatus.PAID:
            return {'bill_id': bill.id, 'pay_status': bill.pay_status}
        bill.pay_status = PayStatus.PAID
        bill.paid_at = timezone.now()
        bill.save(update_fields=['pay_status', 'paid_at'])
        return {'bill_id': bill.id, 'pay_status': bill.pay_status, 'paid_at': bill.paid_at.isoformat()}

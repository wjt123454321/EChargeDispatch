from datetime import datetime, timedelta
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from apps.common.sim_clock import system_now

from apps.accounts.models import AdminAccount
from apps.billing.models import ChargeDetail
from apps.billing.services import BillingService
from apps.charging.models import ChargingRequest, ChargingSession, QueueTicket
from apps.charging.services import ChargingSessionService, DispatchService, QueueService
from apps.common.enums import (
    ErrorCode,
    FaultStrategy,
    PileStatus,
    QueueType,
    RequestStatus,
    SessionStatus,
)
from apps.common.exceptions import AppException
from apps.station.models import ChargingPile
from apps.station.services import ChargingPileService, StationConfigService

from .models import FaultRecord, OperationLog, ReportSnapshot, RescheduleRecord


class OperationLogService:
    @staticmethod
    def log(admin_id, operation_type, target_type, target_id, content):
        OperationLog.objects.create(
            admin_id=admin_id,
            operation_type=operation_type,
            target_type=target_type,
            target_id=str(target_id),
            content=content,
        )


class FaultService:
    @staticmethod
    def list_faults():
        records = FaultRecord.objects.select_related('pile').order_by('-occurred_at')
        return [
            {
                'fault_id': r.id,
                'pile_id': r.pile_id,
                'pile_no': r.pile.pile_no,
                'fault_type': r.fault_type,
                'fault_status': r.fault_status,
                'occurred_at': r.occurred_at.isoformat(),
                'recovered_at': r.recovered_at.isoformat() if r.recovered_at else None,
                'description': r.description,
            }
            for r in records
        ]

    @staticmethod
    @transaction.atomic
    def report_fault(pile_id, admin_id=None):
        pile = ChargingPileService.get_pile(pile_id)
        if pile.status == PileStatus.FAULT:
            raise AppException(ErrorCode.PILE_STATUS_ERROR, '充电桩状态不允许操作')

        config = StationConfigService.get_active_config()
        config.waiting_dispatch_paused = True
        config.save(update_fields=['waiting_dispatch_paused'])

        fault = FaultRecord.objects.create(
            pile=pile,
            fault_type='hardware',
            fault_status='open',
            description=f'充电桩 {pile.pile_no} 故障',
        )
        pile.status = PileStatus.FAULT
        pile.save(update_fields=['status', 'updated_at'])

        active_session = ChargingSession.objects.filter(
            pile=pile, session_status=SessionStatus.ACTIVE, end_time__isnull=True
        ).select_related('request', 'vehicle').first()
        if active_session:
            ChargingSessionService._finalize_session(
                active_session, active_session.request, 'fault', complete_request=False
            )
            active_session.request.status = RequestStatus.PENDING_RESCHEDULE
            active_session.request.current_pile = pile
            active_session.request.save(update_fields=['status', 'current_pile'])

        affected = list(
            ChargingRequest.objects.filter(
                current_pile=pile, status=RequestStatus.DISPATCHED
            ).select_related('vehicle')
        )
        for req in affected:
            req.status = RequestStatus.PENDING_RESCHEDULE
            req.save(update_fields=['status'])
            ticket = QueueService.get_active_ticket(req)
            if ticket:
                QueueService.deactivate_ticket(ticket)

        RescheduleService.handle_fault_reschedule(fault, config)
        if admin_id:
            OperationLogService.log(admin_id, 'fault_report', 'pile', pile_id, f'上报故障 pile={pile_id}')
        return {'fault_id': fault.id, 'pile_id': pile.id, 'affected_count': len(affected)}

    @staticmethod
    @transaction.atomic
    def recover_fault(pile_id, admin_id=None):
        pile = ChargingPileService.get_pile(pile_id)
        if pile.status != PileStatus.FAULT:
            raise AppException(ErrorCode.PILE_STATUS_ERROR, '充电桩状态不允许操作')

        fault = FaultRecord.objects.filter(pile=pile, fault_status='open').order_by('-occurred_at').first()
        if fault:
            fault.fault_status = 'recovered'
            fault.recovered_at = system_now()
            fault.save(update_fields=['fault_status', 'recovered_at'])

        pile.status = PileStatus.AVAILABLE if pile.is_enabled else PileStatus.STANDBY
        pile.save(update_fields=['status', 'updated_at'])

        config = StationConfigService.get_active_config()
        RescheduleService.handle_recovery_reschedule(pile, config)
        config.waiting_dispatch_paused = False
        config.save(update_fields=['waiting_dispatch_paused'])
        DispatchService.try_dispatch_all()

        if admin_id:
            OperationLogService.log(admin_id, 'fault_recover', 'pile', pile_id, f'恢复故障 pile={pile_id}')
        return {'pile_id': pile.id, 'status': pile.status}


class RescheduleService:
    @staticmethod
    def _queue_num_order_key(queue_num: str):
        prefix = queue_num[0] if queue_num else 'Z'
        try:
            num = int(queue_num[1:])
        except (ValueError, IndexError):
            num = 0
        return (prefix, num)

    @staticmethod
    def handle_fault_reschedule(fault: FaultRecord, config):
        """故障桩队列车辆优先重调度；无空位则留在故障桩队列，不停入等候区。"""
        pending = list(
            ChargingRequest.objects.filter(
                status=RequestStatus.PENDING_RESCHEDULE,
                current_pile=fault.pile,
            ).select_related('vehicle')
        )
        if not pending:
            config.waiting_dispatch_paused = False
            config.save(update_fields=['waiting_dispatch_paused'])
            DispatchService.try_dispatch_all()
            return

        if config.fault_strategy == FaultStrategy.TIME_ORDER:
            pending.sort(key=lambda r: RescheduleService._queue_num_order_key(r.queue_num))

        for request in pending:
            target = RescheduleService._best_reschedule_pile(request, config, fault.pile_id)
            if not target:
                continue
            request.status = RequestStatus.DISPATCHED
            request.current_pile = target
            request.queued_at = system_now()
            request.save(update_fields=['status', 'current_pile', 'queued_at'])
            position = DispatchService._pile_queue_count(target) + 1
            QueueService.create_pile_ticket(request, target, request.queue_num, position)
            RescheduleRecord.objects.create(
                fault_record=fault,
                request=request,
                source_pile=fault.pile,
                target_pile=target,
                strategy_type=config.fault_strategy,
            )

        RescheduleService.sync_waiting_dispatch_pause(config)
        DispatchService.try_dispatch_all()

    @staticmethod
    def _best_reschedule_pile(request, config, exclude_pile_id):
        piles = [
            p for p in DispatchService._available_piles(request.request_mode, config)
            if p.id != exclude_pile_id and DispatchService._pile_has_slot(p, config)
        ]
        if not piles:
            return None
        return min(piles, key=lambda p: DispatchService._estimate_pile_completion_time(p))

    @staticmethod
    def sync_waiting_dispatch_pause(config):
        """故障桩队列未清空时保持暂停等候区叫号。"""
        has_fault_queue = ChargingRequest.objects.filter(
            status=RequestStatus.PENDING_RESCHEDULE,
            current_pile__status=PileStatus.FAULT,
        ).exists()
        config.waiting_dispatch_paused = has_fault_queue
        config.save(update_fields=['waiting_dispatch_paused'])

    @staticmethod
    def _same_type_active_piles(mode: str):
        return ChargingPile.objects.filter(
            pile_type=mode,
            is_enabled=True,
            status__in={PileStatus.AVAILABLE, PileStatus.CHARGING},
        )

    @staticmethod
    def _collect_not_charging_requests(piles):
        """收集同类型桩上尚未充电的车辆（含故障桩待重调度队列）。"""
        collected = []
        seen_ids = set()
        for pile in piles:
            for req in QueueService.pile_queue_requests(pile):
                if req.id not in seen_ids:
                    collected.append(req)
                    seen_ids.add(req.id)
            for req in ChargingRequest.objects.filter(
                current_pile=pile,
                status=RequestStatus.PENDING_RESCHEDULE,
            ):
                if req.id not in seen_ids:
                    collected.append(req)
                    seen_ids.add(req.id)
        return collected

    @staticmethod
    def _detach_for_reschedule(requests):
        for req in requests:
            req.status = RequestStatus.PENDING_RESCHEDULE
            req.current_pile = None
            req.save(update_fields=['status', 'current_pile'])
            ticket = QueueService.get_active_ticket(req)
            if ticket:
                QueueService.deactivate_ticket(ticket)

    @staticmethod
    def _assign_rescheduled_request(request, config):
        pile = DispatchService._best_pile_for_request(request, config)
        if not pile or not DispatchService._pile_has_slot(pile, config):
            return False
        request.status = RequestStatus.DISPATCHED
        request.current_pile = pile
        request.queued_at = system_now()
        request.save(update_fields=['status', 'current_pile', 'queued_at'])
        position = DispatchService._pile_queue_count(pile) + 1
        QueueService.create_pile_ticket(request, pile, request.queue_num, position)
        return True

    @staticmethod
    def handle_recovery_reschedule(recovered_pile: ChargingPile, config):
        """
        故障恢复（§5.3）：合并同类型所有桩上尚未充电的车辆，按排队号整体重调度。
        正常派桩仍用最短完成时间；仅恢复时先合并再按号依次分配。
        """
        mode = recovered_pile.pile_type
        same_type_piles = RescheduleService._same_type_active_piles(mode)
        other_piles = same_type_piles.exclude(id=recovered_pile.id)

        has_other_queue = ChargingRequest.objects.filter(
            current_pile__in=other_piles,
            status=RequestStatus.DISPATCHED,
        ).exists()
        has_recovered_pending = ChargingRequest.objects.filter(
            current_pile=recovered_pile,
            status=RequestStatus.PENDING_RESCHEDULE,
        ).exists()
        if not has_other_queue and not has_recovered_pending:
            return

        to_merge = RescheduleService._collect_not_charging_requests(same_type_piles)
        if not to_merge:
            return

        config.waiting_dispatch_paused = True
        config.save(update_fields=['waiting_dispatch_paused'])

        RescheduleService._detach_for_reschedule(to_merge)
        to_merge.sort(key=lambda r: RescheduleService._queue_num_order_key(r.queue_num))

        for request in to_merge:
            if not RescheduleService._assign_rescheduled_request(request, config):
                request.status = RequestStatus.PENDING_RESCHEDULE
                request.current_pile = recovered_pile
                request.save(update_fields=['status', 'current_pile'])

        RescheduleService.sync_waiting_dispatch_pause(config)
        if not config.waiting_dispatch_paused:
            DispatchService.try_dispatch_all()


class ReportService:
    @staticmethod
    def generate_stats(period: str, date_str: str):
        if period == 'day':
            report_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            start = timezone.make_aware(datetime.combine(report_date, datetime.min.time()))
            end = start + timedelta(days=1)
        elif period == 'week':
            report_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            start = timezone.make_aware(datetime.combine(report_date - timedelta(days=report_date.weekday()), datetime.min.time()))
            end = start + timedelta(days=7)
        elif period == 'month':
            report_date = datetime.strptime(date_str + '-01', '%Y-%m-%d').date()
            start = timezone.make_aware(datetime.combine(report_date.replace(day=1), datetime.min.time()))
            if report_date.month == 12:
                next_month = report_date.replace(year=report_date.year + 1, month=1, day=1)
            else:
                next_month = report_date.replace(month=report_date.month + 1, day=1)
            end = timezone.make_aware(datetime.combine(next_month, datetime.min.time()))
        else:
            raise AppException(ErrorCode.VALIDATION_ERROR, '参数校验失败')

        piles = ChargingPile.objects.all().order_by('pile_no')
        results = []
        for pile in piles:
            details = ChargeDetail.objects.filter(
                pile=pile, generated_at__gte=start, generated_at__lt=end
            )
            agg = details.aggregate(
                total_charge_amount=Sum('charge_amount'),
                total_charge_fee=Sum('charge_fee'),
                total_service_fee=Sum('service_fee'),
                total_fee=Sum('total_fee'),
                total_duration=Sum('charge_duration'),
            )
            count = details.count()
            item = {
                'pile_id': pile.id,
                'pile_no': pile.pile_no,
                'period': period,
                'date': date_str,
                'total_charge_num': count,
                'total_charge_time': float(agg['total_duration'] or 0),
                'total_charge_capacity': float(agg['total_charge_amount'] or 0),
                'total_charge_fee': float(agg['total_charge_fee'] or 0),
                'total_service_fee': float(agg['total_service_fee'] or 0),
                'total_fee': float(agg['total_fee'] or 0),
            }
            results.append(item)
            ReportSnapshot.objects.update_or_create(
                period_type=period,
                report_date=report_date if period != 'month' else report_date.replace(day=1),
                pile=pile,
                defaults={
                    'total_charge_num': count,
                    'total_charge_time': Decimal(str(item['total_charge_time'])),
                    'total_charge_capacity': Decimal(str(item['total_charge_capacity'])),
                    'total_charge_fee': Decimal(str(item['total_charge_fee'])),
                    'total_service_fee': Decimal(str(item['total_service_fee'])),
                    'total_fee': Decimal(str(item['total_fee'])),
                },
            )
        return {'period': period, 'date': date_str, 'items': results}

from decimal import Decimal

from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone

from apps.common.sim_clock import system_now

from apps.accounts.models import Vehicle
from apps.accounts.services import VehicleService
from apps.billing.services import BillingService
from apps.common.enums import (
    ChargeMode,
    DispatchMode,
    ErrorCode,
    PileStatus,
    QueueType,
    RequestStatus,
    SessionStatus,
    VehicleStatus,
)
from apps.common.exceptions import AppException
from apps.common.utils import estimate_charge_hours, generate_no
from apps.station.models import ChargingPile, SystemConfig
from apps.station.services import StationConfigService

from .models import ChargingRequest, ChargingSession, DispatchRecord, QueueTicket


class QueueService:
    @staticmethod
    def get_active_ticket(request: ChargingRequest):
        return QueueTicket.objects.filter(request=request, is_active=True).first()

    @staticmethod
    def deactivate_ticket(ticket: QueueTicket):
        ticket.is_active = False
        ticket.save(update_fields=['is_active'])

    @staticmethod
    def waiting_count(mode: str):
        return ChargingRequest.objects.filter(status=RequestStatus.QUEUING, request_mode=mode).count()

    @staticmethod
    def waiting_area_used():
        return ChargingRequest.objects.filter(status=RequestStatus.QUEUING).count()

    @staticmethod
    def pile_occupancy_count(pile: ChargingPile):
        """桩队列占用数：正在充电 + 排队等待（含故障重调度）"""
        return ChargingRequest.objects.filter(
            current_pile=pile,
            status__in={
                RequestStatus.CHARGING,
                RequestStatus.DISPATCHED,
                RequestStatus.PENDING_RESCHEDULE,
            },
        ).count()

    @staticmethod
    def pile_queue_requests(pile: ChargingPile):
        return ChargingRequest.objects.filter(
            current_pile=pile,
            status=RequestStatus.DISPATCHED,
        ).select_related('vehicle', 'user').order_by('queued_at', 'id')

    @staticmethod
    def next_queue_num(config: SystemConfig, mode: str) -> str:
        if mode == ChargeMode.FAST:
            config.fast_queue_seq += 1
            num = config.fast_queue_seq
            config.save(update_fields=['fast_queue_seq'])
            return f'F{num}'
        config.slow_queue_seq += 1
        num = config.slow_queue_seq
        config.save(update_fields=['slow_queue_seq'])
        return f'T{num}'

    @staticmethod
    def create_waiting_ticket(request: ChargingRequest, queue_num: str):
        QueueTicket.objects.filter(request=request, is_active=True).update(is_active=False)
        return QueueTicket.objects.create(
            request=request,
            queue_num=queue_num,
            queue_type=QueueType.WAITING_AREA,
            queue_position=QueueService.waiting_count(request.request_mode),
            is_active=True,
        )

    @staticmethod
    def create_pile_ticket(request: ChargingRequest, pile: ChargingPile, queue_num: str, position: int):
        QueueTicket.objects.filter(request=request, is_active=True).update(is_active=False)
        ticket = QueueTicket.objects.create(
            request=request,
            queue_num=queue_num,
            queue_type=QueueType.PILE_QUEUE,
            pile=pile,
            queue_position=position,
            is_active=True,
        )
        pile.current_queue_length = QueueService.pile_occupancy_count(pile)
        pile.save(update_fields=['current_queue_length', 'updated_at'])
        return ticket

    @staticmethod
    def position_info(request: ChargingRequest):
        if request.status in {RequestStatus.COMPLETED, RequestStatus.CANCELLED}:
            return None
        if request.status == RequestStatus.QUEUING:
            ahead = ChargingRequest.objects.filter(
                status=RequestStatus.QUEUING,
                request_mode=request.request_mode,
                request_time__lt=request.request_time,
            ).count()
            return {
                'position': '等候区',
                'queue_num': request.queue_num,
                'ahead_count': ahead,
            }
        if request.status in {RequestStatus.DISPATCHED, RequestStatus.CHARGING, RequestStatus.PENDING_RESCHEDULE}:
            ahead = 0
            if request.current_pile_id and request.status == RequestStatus.DISPATCHED:
                ahead = ChargingRequest.objects.filter(
                    current_pile_id=request.current_pile_id,
                    status=RequestStatus.DISPATCHED,
                    queued_at__lt=request.queued_at,
                ).count()
            return {
                'position': '充电区',
                'queue_num': request.queue_num,
                'ahead_count': ahead,
                'pile_id': request.current_pile_id,
            }
        return None


class DispatchService:
    @staticmethod
    def _available_piles(mode: str, config: SystemConfig):
        return ChargingPile.objects.filter(
            pile_type=mode,
            is_enabled=True,
            status__in={PileStatus.AVAILABLE, PileStatus.CHARGING},
        )

    @staticmethod
    def _pile_queue_count(pile: ChargingPile):
        return QueueService.pile_occupancy_count(pile)

    @staticmethod
    def _pile_has_slot(pile: ChargingPile, config: SystemConfig):
        return DispatchService._pile_queue_count(pile) < config.charging_queue_len

    @staticmethod
    def _estimate_pile_completion_time(pile: ChargingPile) -> Decimal:
        total = Decimal('0')
        requests = QueueService.pile_queue_requests(pile)
        for req in requests:
            total += estimate_charge_hours(req.request_amount, req.request_mode)
        session = ChargingSession.objects.filter(
            pile=pile, session_status=SessionStatus.ACTIVE, end_time__isnull=True
        ).select_related('request').first()
        if session:
            from apps.common.utils import compute_charged_amount
            charged = compute_charged_amount(session)
            remaining = max(session.request.request_amount - charged, Decimal('0'))
            total += estimate_charge_hours(remaining, session.request.request_mode)
        return total

    @staticmethod
    def _best_pile_for_request(request: ChargingRequest, config: SystemConfig):
        candidates = []
        for pile in DispatchService._available_piles(request.request_mode, config):
            if not DispatchService._pile_has_slot(pile, config):
                continue
            wait_time = DispatchService._estimate_pile_completion_time(pile)
            self_time = estimate_charge_hours(request.request_amount, request.request_mode)
            candidates.append((wait_time + self_time, pile))
        if not candidates:
            return None
        candidates.sort(key=lambda x: (x[0], x[1].id))
        return candidates[0][1]

    @staticmethod
    def _dispatch_request_to_pile(request: ChargingRequest, pile: ChargingPile, config: SystemConfig):
        before = request.status
        position = DispatchService._pile_queue_count(pile) + 1
        request.status = RequestStatus.DISPATCHED
        request.current_pile = pile
        request.queued_at = system_now()
        request.save(update_fields=['status', 'current_pile', 'queued_at'])
        QueueService.create_pile_ticket(request, pile, request.queue_num, position)
        VehicleService.sync_vehicle_status(request.vehicle, VehicleStatus.QUEUING, False)
        DispatchRecord.objects.create(
            request=request,
            source_type=QueueType.WAITING_AREA,
            target_pile=pile,
            dispatch_strategy=config.dispatch_mode,
            before_status=before,
            after_status=request.status,
        )

    @staticmethod
    def try_dispatch_mode(config: SystemConfig, mode: str):
        if config.waiting_dispatch_paused:
            return
        waiting = ChargingRequest.objects.filter(
            status=RequestStatus.QUEUING, request_mode=mode
        ).order_by('request_time', 'id')
        if not waiting.exists():
            return

        if config.dispatch_mode == DispatchMode.BATCH_MIN_TOTAL:
            DispatchService._try_batch_dispatch(config)
            return

        if config.dispatch_mode == DispatchMode.SINGLE_MIN_TOTAL:
            DispatchService._try_single_min_total(config, mode)
            return

        for request in list(waiting):
            has_slot = any(
                DispatchService._pile_has_slot(p, config)
                for p in DispatchService._available_piles(mode, config)
            )
            if not has_slot:
                break
            pile = DispatchService._best_pile_for_request(request, config)
            if not pile:
                break
            DispatchService._dispatch_request_to_pile(request, pile, config)

    @staticmethod
    def _try_single_min_total(config: SystemConfig, mode: str):
        available_slots = 0
        piles = list(DispatchService._available_piles(mode, config))
        for pile in piles:
            available_slots += max(config.charging_queue_len - DispatchService._pile_queue_count(pile), 0)
        if available_slots <= 0:
            return
        waiting = list(
            ChargingRequest.objects.filter(status=RequestStatus.QUEUING, request_mode=mode)
            .order_by('request_time', 'id')[:available_slots]
        )
        for request in waiting:
            pile = DispatchService._best_pile_for_request(request, config)
            if pile:
                DispatchService._dispatch_request_to_pile(request, pile, config)

    @staticmethod
    def _try_batch_dispatch(config: SystemConfig):
        total_capacity = config.waiting_area_size + config.charging_queue_len * (
            config.fast_pile_num + config.slow_pile_num
        )
        active_count = ChargingRequest.objects.filter(status__in=RequestStatus.ACTIVE).count()
        if active_count < total_capacity:
            return
        waiting = list(
            ChargingRequest.objects.filter(status=RequestStatus.QUEUING).order_by('request_time', 'id')
        )
        piles = list(
            ChargingPile.objects.filter(
                is_enabled=True, status__in={PileStatus.AVAILABLE, PileStatus.CHARGING}
            )
        )
        for request in waiting:
            best_pile = None
            best_score = None
            for pile in piles:
                if not DispatchService._pile_has_slot(pile, config):
                    continue
                score = DispatchService._estimate_pile_completion_time(pile) + estimate_charge_hours(
                    request.request_amount, pile.pile_type
                )
                if best_score is None or score < best_score:
                    best_score = score
                    best_pile = pile
            if best_pile:
                DispatchService._dispatch_request_to_pile(request, best_pile, config)

    @staticmethod
    def try_dispatch_all():
        config = StationConfigService.get_active_config()
        DispatchService.try_dispatch_mode(config, ChargeMode.FAST)
        DispatchService.try_dispatch_mode(config, ChargeMode.SLOW)


class ChargingRequestService:
    @staticmethod
    def get_active_request(vehicle: Vehicle):
        return ChargingRequest.objects.filter(
            vehicle=vehicle, status__in=RequestStatus.ACTIVE
        ).select_related('vehicle', 'current_pile', 'user').first()

    @staticmethod
    def get_request_by_id(request_id):
        req = ChargingRequest.objects.filter(id=request_id).select_related('vehicle', 'current_pile').first()
        if not req:
            raise AppException(ErrorCode.REQUEST_NOT_FOUND, '请求不存在')
        return req

    @staticmethod
    def request_to_dict(request: ChargingRequest, include_fault=False):
        data = {
            'request_id': request.id,
            'request_no': request.request_no,
            'queue_num': request.queue_num,
            'status': request.status,
            'request_mode': request.request_mode,
            'request_amount': float(request.request_amount),
            'pile_id': request.current_pile_id,
            'position': QueueService.position_info(request),
            'request_time': request.request_time.isoformat() if request.request_time else None,
        }
        if include_fault:
            data['fault_notice'] = request.status == RequestStatus.PENDING_RESCHEDULE
        return data

    @staticmethod
    @transaction.atomic
    def submit_request(vehicle: Vehicle, request_mode: str, request_amount):
        if request_mode not in {ChargeMode.FAST, ChargeMode.SLOW}:
            raise AppException(ErrorCode.VALIDATION_ERROR, '参数校验失败')
        amount = Decimal(str(request_amount))
        if amount <= 0:
            raise AppException(ErrorCode.VALIDATION_ERROR, '参数校验失败')
        if ChargingRequestService.get_active_request(vehicle):
            raise AppException(ErrorCode.ACTIVE_REQUEST_EXISTS, '已有未完成请求')

        config = StationConfigService.get_active_config()
        DispatchService.try_dispatch_all()
        if QueueService.waiting_area_used() >= config.waiting_area_size:
            has_slot = any(
                DispatchService._pile_has_slot(p, config)
                for p in DispatchService._available_piles(request_mode, config)
            )
            if not has_slot:
                return {
                    'accepted': False,
                    'reason': 'waiting_area_full',
                    'message': '等候区已无空位',
                }

        queue_num = QueueService.next_queue_num(config, request_mode)
        request = ChargingRequest.objects.create(
            request_no=generate_no('REQ'),
            user=vehicle.user,
            vehicle=vehicle,
            request_mode=request_mode,
            request_amount=amount,
            status=RequestStatus.QUEUING,
            queue_num=queue_num,
            queued_at=system_now(),
        )
        QueueService.create_waiting_ticket(request, queue_num)
        VehicleService.sync_vehicle_status(vehicle, VehicleStatus.WAITING, False)
        DispatchService.try_dispatch_all()
        request.refresh_from_db()
        data = ChargingRequestService.request_to_dict(request)
        data['accepted'] = True
        return data

    @staticmethod
    @transaction.atomic
    def update_amount(vehicle: Vehicle, amount):
        request = ChargingRequestService.get_active_request(vehicle)
        if not request:
            raise AppException(ErrorCode.REQUEST_NOT_FOUND, '请求不存在')
        if request.status != RequestStatus.QUEUING:
            raise AppException(ErrorCode.INVALID_STATUS, '当前状态不允许操作')
        new_amount = Decimal(str(amount))
        if new_amount <= 0:
            raise AppException(ErrorCode.VALIDATION_ERROR, '参数校验失败')
        request.request_amount = new_amount
        request.save(update_fields=['request_amount'])
        return ChargingRequestService.request_to_dict(request)

    @staticmethod
    @transaction.atomic
    def update_mode(vehicle: Vehicle, mode: str):
        if mode not in {ChargeMode.FAST, ChargeMode.SLOW}:
            raise AppException(ErrorCode.VALIDATION_ERROR, '参数校验失败')
        request = ChargingRequestService.get_active_request(vehicle)
        if not request:
            raise AppException(ErrorCode.REQUEST_NOT_FOUND, '请求不存在')
        if request.status != RequestStatus.QUEUING:
            raise AppException(ErrorCode.INVALID_STATUS, '当前状态不允许操作')
        if request.request_mode == mode:
            return ChargingRequestService.request_to_dict(request)

        config = StationConfigService.get_active_config()
        queue_num = QueueService.next_queue_num(config, mode)
        request.request_mode = mode
        request.queue_num = queue_num
        request.request_time = system_now()
        request.save(update_fields=['request_mode', 'queue_num', 'request_time'])
        QueueService.create_waiting_ticket(request, queue_num)
        DispatchService.try_dispatch_all()
        request.refresh_from_db()
        return ChargingRequestService.request_to_dict(request)

    @staticmethod
    def get_queue_status(vehicle: Vehicle):
        request = ChargingRequestService.get_active_request(vehicle)
        if not request:
            return {'has_request': False}
        position = QueueService.position_info(request)
        ahead = position.get('ahead_count', 0) if position else 0
        return {
            'has_request': True,
            'request_id': request.id,
            'queue_num': request.queue_num,
            'status': request.status,
            'request_mode': request.request_mode,
            'ahead_count': ahead,
            'position': position,
        }


class ChargingSessionService:
    @staticmethod
    def get_active_session(vehicle: Vehicle):
        return ChargingSession.objects.filter(
            vehicle=vehicle, session_status=SessionStatus.ACTIVE, end_time__isnull=True
        ).select_related('pile', 'request').first()

    @staticmethod
    @transaction.atomic
    def start_charging(vehicle: Vehicle, pile_id):
        request = ChargingRequestService.get_active_request(vehicle)
        if not request:
            raise AppException(ErrorCode.REQUEST_NOT_FOUND, '请求不存在')
        if request.status != RequestStatus.DISPATCHED:
            raise AppException(ErrorCode.INVALID_STATUS, '当前状态不允许操作')
        if request.current_pile_id != pile_id:
            raise AppException(ErrorCode.INVALID_STATUS, '当前状态不允许操作')

        first = ChargingRequest.objects.filter(
            current_pile_id=pile_id, status=RequestStatus.DISPATCHED
        ).order_by('queued_at', 'id').first()
        if not first or first.id != request.id:
            raise AppException(ErrorCode.INVALID_STATUS, '当前状态不允许操作')

        if ChargingSession.objects.filter(request=request).exists():
            raise AppException(ErrorCode.INVALID_STATUS, '当前状态不允许操作')

        pile = request.current_pile
        if pile.status == PileStatus.FAULT:
            raise AppException(ErrorCode.PILE_STATUS_ERROR, '充电桩状态不允许操作')
        if ChargingSession.objects.filter(
            pile=pile,
            session_status=SessionStatus.ACTIVE,
            end_time__isnull=True,
        ).exists():
            raise AppException(ErrorCode.INVALID_STATUS, '当前状态不允许操作')

        now = system_now()
        request.status = RequestStatus.CHARGING
        request.charge_started_at = now
        request.save(update_fields=['status', 'charge_started_at'])
        session = ChargingSession.objects.create(
            session_no=generate_no('SES'),
            request=request,
            vehicle=vehicle,
            pile=pile,
            start_time=now,
            session_status=SessionStatus.ACTIVE,
        )
        pile.status = PileStatus.CHARGING
        pile.save(update_fields=['status', 'updated_at'])
        VehicleService.sync_vehicle_status(vehicle, VehicleStatus.CHARGING, True)
        QueueService.deactivate_ticket(QueueService.get_active_ticket(request))
        return {
            'session_id': session.id,
            'request_id': request.id,
            'pile_id': pile.id,
            'status': request.status,
            'start_time': now.isoformat(),
        }

    @staticmethod
    def get_charging_status(vehicle: Vehicle):
        request = ChargingRequestService.get_active_request(vehicle)
        session = ChargingSessionService.get_active_session(vehicle)
        if not request:
            return {'has_request': False}
        charged_amount = Decimal('0')
        if session:
            from apps.common.utils import compute_charged_amount
            charged_amount = compute_charged_amount(session)
            session.charged_amount = charged_amount
            duration_hours = Decimal(str((system_now() - session.start_time).total_seconds())) / Decimal('3600')
            session.charged_duration = duration_hours.quantize(Decimal('0.0001'))
            session.save(update_fields=['charged_amount', 'charged_duration'])
        return {
            'has_request': True,
            'request_id': request.id,
            'status': request.status,
            'request_mode': request.request_mode,
            'request_amount': float(request.request_amount),
            'charged_amount': float(charged_amount),
            'pile_id': request.current_pile_id,
            'session_id': session.id if session else None,
            'start_time': session.start_time.isoformat() if session else None,
        }

    @staticmethod
    @transaction.atomic
    def end_charging(vehicle: Vehicle, stop_reason='normal'):
        request = ChargingRequestService.get_active_request(vehicle)
        if not request or request.status != RequestStatus.CHARGING:
            raise AppException(ErrorCode.INVALID_STATUS, '当前状态不允许操作')
        session = ChargingSessionService.get_active_session(vehicle)
        if not session:
            raise AppException(ErrorCode.INVALID_STATUS, '当前状态不允许操作')
        return ChargingSessionService._finalize_session(session, request, stop_reason)

    @staticmethod
    @transaction.atomic
    def cancel_charging(vehicle: Vehicle):
        request = ChargingRequestService.get_active_request(vehicle)
        if not request:
            raise AppException(ErrorCode.REQUEST_NOT_FOUND, '请求不存在')
        if request.status == RequestStatus.CHARGING:
            session = ChargingSessionService.get_active_session(vehicle)
            if session:
                result = ChargingSessionService._finalize_session(session, request, 'cancelled')
                request.status = RequestStatus.CANCELLED
                request.charge_ended_at = system_now()
                request.save(update_fields=['status', 'charge_ended_at'])
                return {'request_id': request.id, 'status': request.status, **result}
        elif request.status in {RequestStatus.QUEUING, RequestStatus.DISPATCHED, RequestStatus.PENDING_RESCHEDULE}:
            ticket = QueueService.get_active_ticket(request)
            if ticket:
                QueueService.deactivate_ticket(ticket)
            if request.current_pile_id:
                pile = request.current_pile
                pile.current_queue_length = max(pile.current_queue_length - 1, 0)
                pile.save(update_fields=['current_queue_length', 'updated_at'])
        else:
            raise AppException(ErrorCode.INVALID_STATUS, '当前状态不允许操作')

        request.status = RequestStatus.CANCELLED
        request.charge_ended_at = system_now()
        request.save(update_fields=['status', 'charge_ended_at'])
        VehicleService.reset_to_idle(vehicle)
        DispatchService.try_dispatch_all()
        return {'request_id': request.id, 'status': request.status}

    @staticmethod
    def _finalize_session(session, request, stop_reason, complete_request=True):
        from apps.common.utils import compute_charged_amount

        now = system_now()
        session.end_time = now
        session.charged_amount = compute_charged_amount(session, now)
        duration_hours = Decimal(str((now - session.start_time).total_seconds())) / Decimal('3600')
        session.charged_duration = duration_hours.quantize(Decimal('0.0001'))
        session.session_status = (
            SessionStatus.COMPLETED if stop_reason == 'normal' else SessionStatus.CANCELLED
        )
        session.stop_reason = stop_reason
        session.save()

        pile = session.pile
        pile.total_charge_num += 1
        pile.total_charge_time += session.charged_duration
        pile.total_charge_capacity += session.charged_amount
        pile.status = PileStatus.AVAILABLE if pile.status != PileStatus.FAULT else PileStatus.FAULT
        pile.save(update_fields=[
            'total_charge_num', 'total_charge_time', 'total_charge_capacity', 'status', 'updated_at'
        ])

        bill_data = BillingService.create_detail_and_bill(session, request)

        if complete_request:
            request.status = RequestStatus.COMPLETED
            request.charge_ended_at = now
            request.save(update_fields=['status', 'charge_ended_at'])

        VehicleService.reset_to_idle(request.vehicle)
        DispatchService.try_dispatch_all()
        return {
            'request_id': request.id,
            'status': request.status,
            'charged_amount': float(session.charged_amount),
            'bill_id': bill_data['bill_id'],
            'detail_id': bill_data['detail_id'],
        }

    @staticmethod
    def _queue_item_from_request(req: ChargingRequest, position: int, wait_seconds: int, **extra):
        item = {
            'request_id': req.id,
            'car_id': req.vehicle.plate_no,
            'user_id': req.user_id,
            'battery_capacity': float(req.vehicle.battery_capacity),
            'request_amount': float(req.request_amount),
            'queue_num': req.queue_num,
            'waiting_seconds': wait_seconds,
            'status': req.status,
            'position': position,
        }
        item.update(extra)
        return item

    @staticmethod
    def pile_queue_detail(pile_id):
        pile = ChargingPile.objects.filter(id=pile_id).first()
        if not pile:
            raise AppException(ErrorCode.PILE_NOT_FOUND, '充电桩不存在')
        config = StationConfigService.get_active_config()
        requests = QueueService.pile_queue_requests(pile)
        queue_items = []
        position = 1

        session = ChargingSession.objects.filter(
            pile=pile, session_status=SessionStatus.ACTIVE, end_time__isnull=True
        ).select_related('vehicle', 'request', 'request__user').first()
        charging_car = None
        if session:
            from apps.common.utils import compute_charged_amount
            charged = float(compute_charged_amount(session))
            wait_seconds = int((system_now() - session.start_time).total_seconds())
            req = session.request
            charging_car = {
                'car_id': session.vehicle.plate_no,
                'request_id': session.request_id,
                'charged_amount': charged,
            }
            queue_items.append(ChargingSessionService._queue_item_from_request(
                req, position, wait_seconds,
                status=RequestStatus.CHARGING,
                charged_amount=charged,
            ))
            position += 1

        for req in requests:
            wait_seconds = 0
            if req.queued_at:
                wait_seconds = int((system_now() - req.queued_at).total_seconds())
            queue_items.append(ChargingSessionService._queue_item_from_request(
                req, position, wait_seconds,
            ))
            position += 1

        pending = ChargingRequest.objects.filter(
            current_pile=pile,
            status=RequestStatus.PENDING_RESCHEDULE,
        ).select_related('vehicle', 'user').order_by('queued_at', 'id')
        for req in pending:
            wait_seconds = 0
            if req.queued_at:
                wait_seconds = int((system_now() - req.queued_at).total_seconds())
            queue_items.append(ChargingSessionService._queue_item_from_request(
                req, position, wait_seconds,
                status=RequestStatus.PENDING_RESCHEDULE,
            ))
            position += 1

        return {
            'pile_id': pile.id,
            'pile_no': pile.pile_no,
            'status': pile.status,
            'queue_used': len(queue_items),
            'queue_total': config.charging_queue_len,
            'queue': queue_items,
            'charging_car': charging_car,
        }

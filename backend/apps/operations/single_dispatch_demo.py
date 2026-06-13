from decimal import Decimal

from django.core.management import call_command
from django.db import transaction

from apps.accounts.models import UserAccount, Vehicle
from apps.accounts.services import VehicleService
from apps.charging.models import ChargingRequest, ChargingSession, QueueTicket
from apps.charging.services import ChargingRequestService, DispatchService
from apps.common.enums import (
    ChargeMode,
    DispatchMode,
    PileStatus,
    QueueType,
    RequestStatus,
    SessionStatus,
    VehicleStatus,
)
from apps.common.sim_clock import disable, enable, make_case_time, system_now
from apps.common.utils import generate_no
from apps.station.models import ChargingPile
from apps.station.services import StationConfigService


class SingleDispatchDemoService:
    """
    固定场景的单次调度演示：
    - 只构造一次场景
    - 直接调用当前代码中的调度算法
    - 返回结果后回滚，不污染正式环境
    """

    FAST_WAITING = [
        ('a', Decimal('20')),
        ('b', Decimal('20')),
        ('c', Decimal('10')),
        ('d', Decimal('10')),
        ('e', Decimal('15')),
        ('f', Decimal('15')),
    ]
    SLOW_WAITING = [
        ('g', Decimal('13')),
        ('h', Decimal('15')),
        ('i', Decimal('10')),
        ('j', Decimal('20')),
    ]

    ACTIVE_CHARGING = [
        ('FAST-ACTIVE-A', ChargeMode.FAST, 'F1', Decimal('30')),
        ('FAST-ACTIVE-B', ChargeMode.FAST, 'F2', Decimal('60')),
        ('SLOW-ACTIVE-A', ChargeMode.SLOW, 'T1', Decimal('10')),
        ('SLOW-ACTIVE-B', ChargeMode.SLOW, 'T2', Decimal('20')),
    ]

    @staticmethod
    def run():
        with transaction.atomic():
            result = SingleDispatchDemoService._run_impl()
            transaction.set_rollback(True)
        return result

    @staticmethod
    def _run_impl():
        SingleDispatchDemoService._reset_demo_environment()
        config = StationConfigService.get_active_config()

        enable(make_case_time(6, 0))
        try:
            SingleDispatchDemoService._configure_scene(config)
            SingleDispatchDemoService._create_active_charging_sessions()
            SingleDispatchDemoService._submit_waiting_requests()

            config.refresh_from_db()
            config.waiting_dispatch_paused = False
            config.save(update_fields=['waiting_dispatch_paused'])

            DispatchService.try_dispatch_mode(config, ChargeMode.FAST)
            DispatchService.try_dispatch_mode(config, ChargeMode.SLOW)

            return SingleDispatchDemoService._build_result(config)
        finally:
            disable()

    @staticmethod
    def _reset_demo_environment():
        call_command('init_system', verbosity=0)

    @staticmethod
    def _configure_scene(config):
        config.dispatch_mode = DispatchMode.SINGLE_MIN_TOTAL
        config.waiting_dispatch_paused = True
        config.charging_queue_len = 3
        config.waiting_area_size = 20
        config.fast_queue_seq = 0
        config.slow_queue_seq = 0
        config.save(update_fields=[
            'dispatch_mode',
            'waiting_dispatch_paused',
            'charging_queue_len',
            'waiting_area_size',
            'fast_queue_seq',
            'slow_queue_seq',
        ])

        # 仅保留 2 个快充桩和 2 个慢充桩参与本次场景。
        for pile in ChargingPile.objects.filter(pile_no='T3'):
            pile.is_enabled = False
            pile.status = PileStatus.OFF
            pile.save(update_fields=['is_enabled', 'status', 'updated_at'])

    @staticmethod
    def _create_vehicle(plate_no: str):
        user = UserAccount.objects.create(user_name=plate_no, password_hash='x')
        return Vehicle.objects.create(
            user=user,
            plate_no=plate_no,
            battery_capacity=Decimal('60'),
            current_battery_level=Decimal('60'),
        )

    @staticmethod
    def _create_active_charging_sessions():
        now = system_now()
        for plate_no, mode, pile_no, amount in SingleDispatchDemoService.ACTIVE_CHARGING:
            vehicle = SingleDispatchDemoService._create_vehicle(plate_no)
            pile = ChargingPile.objects.get(pile_no=pile_no)
            pile.status = PileStatus.CHARGING
            pile.save(update_fields=['status', 'updated_at'])

            request = ChargingRequest.objects.create(
                request_no=generate_no('REQ'),
                user=vehicle.user,
                vehicle=vehicle,
                request_mode=mode,
                request_amount=amount,
                status=RequestStatus.CHARGING,
                current_pile=pile,
                queued_at=now,
                charge_started_at=now,
            )
            ChargingSession.objects.create(
                session_no=generate_no('SES'),
                request=request,
                vehicle=vehicle,
                pile=pile,
                start_time=now,
                session_status=SessionStatus.ACTIVE,
            )
            VehicleService.sync_vehicle_status(vehicle, VehicleStatus.CHARGING, True)

    @staticmethod
    def _submit_waiting_requests():
        for label, amount in SingleDispatchDemoService.FAST_WAITING:
            vehicle = SingleDispatchDemoService._create_vehicle(f'FAST-{label.upper()}')
            ChargingRequestService.submit_request(vehicle, ChargeMode.FAST, amount)

        for label, amount in SingleDispatchDemoService.SLOW_WAITING:
            vehicle = SingleDispatchDemoService._create_vehicle(f'SLOW-{label.upper()}')
            ChargingRequestService.submit_request(vehicle, ChargeMode.SLOW, amount)

    @staticmethod
    def _build_pile_result(pile_no: str):
        pile = ChargingPile.objects.get(pile_no=pile_no)
        session = ChargingSession.objects.filter(
            pile=pile,
            session_status=SessionStatus.ACTIVE,
            end_time__isnull=True,
        ).select_related('request', 'vehicle').first()

        base_wait = Decimal('0')
        current_car = None
        if session:
            base_wait = session.request.request_amount / pile.rated_power
            current_car = {
                'plate_no': session.vehicle.plate_no,
                'remaining_amount': float(session.request.request_amount),
                'remaining_hours': float(base_wait),
            }

        tickets = list(
            QueueTicket.objects.filter(
                queue_type=QueueType.PILE_QUEUE,
                pile=pile,
                is_active=True,
            ).select_related('request__vehicle').order_by('queue_position', 'request__id')
        )

        entries = []
        current = base_wait
        for ticket in tickets:
            charge_hours = ticket.request.request_amount / pile.rated_power
            current += charge_hours
            entries.append({
                'label': ticket.request.vehicle.plate_no.split('-')[-1].lower(),
                'plate_no': ticket.request.vehicle.plate_no,
                'request_amount': float(ticket.request.request_amount),
                'queue_position': ticket.queue_position,
                'completion_hours': float(current),
            })

        return {
            'pile_no': pile_no,
            'mode': pile.pile_type,
            'current_car': current_car,
            'entries': entries,
            'total_completion_hours': float(sum(
                Decimal(str(entry['completion_hours'])) for entry in entries
            )),
        }

    @staticmethod
    def _remaining_waiting(mode: str):
        return [
            {
                'label': request.vehicle.plate_no.split('-')[-1].lower(),
                'plate_no': request.vehicle.plate_no,
                'request_amount': float(request.request_amount),
            }
            for request in ChargingRequest.objects.filter(
                request_mode=mode,
                status=RequestStatus.QUEUING,
            ).select_related('vehicle').order_by('request_time', 'id')
        ]

    @staticmethod
    def _build_result(config):
        fast_piles = ['F1', 'F2']
        slow_piles = ['T1', 'T2']
        fast_results = [SingleDispatchDemoService._build_pile_result(pile_no) for pile_no in fast_piles]
        slow_results = [SingleDispatchDemoService._build_pile_result(pile_no) for pile_no in slow_piles]

        fast_total = sum(Decimal(str(item['total_completion_hours'])) for item in fast_results)
        slow_total = sum(Decimal(str(item['total_completion_hours'])) for item in slow_results)

        return {
            'dispatch_mode': config.dispatch_mode,
            'charging_queue_len': config.charging_queue_len,
            'fast_results': fast_results,
            'slow_results': slow_results,
            'remaining_fast_waiting': SingleDispatchDemoService._remaining_waiting(ChargeMode.FAST),
            'remaining_slow_waiting': SingleDispatchDemoService._remaining_waiting(ChargeMode.SLOW),
            'fast_total_completion_hours': float(fast_total),
            'slow_total_completion_hours': float(slow_total),
            'total_completion_hours': float(fast_total + slow_total),
        }

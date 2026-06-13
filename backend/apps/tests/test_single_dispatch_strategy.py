from decimal import Decimal
from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from apps.accounts.models import UserAccount, Vehicle
from apps.charging.models import ChargingRequest, ChargingSession, QueueTicket
from apps.charging.services import ChargingRequestService, DispatchService
from apps.common.enums import (
    ChargeMode,
    DispatchMode,
    PileStatus,
    QueueType,
    RequestStatus,
    SessionStatus,
)
from apps.common.sim_clock import disable, enable, make_case_time, system_now
from apps.station.models import ChargingPile, SystemConfig
from apps.station.services import StationConfigService


class SingleDispatchStrategyTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('init_system')

    def setUp(self):
        self.config = SystemConfig.objects.filter(is_active=True).first()
        self.config.dispatch_mode = DispatchMode.SINGLE_MIN_TOTAL
        self.config.waiting_dispatch_paused = True
        self.config.charging_queue_len = 2
        self.config.save(update_fields=['dispatch_mode', 'waiting_dispatch_paused', 'charging_queue_len'])

        self.fast_piles = list(ChargingPile.objects.filter(pile_type=ChargeMode.FAST).order_by('id'))
        self.fast_primary = self.fast_piles[0]
        self.fast_secondary = self.fast_piles[1]
        self.fast_secondary.is_enabled = False
        self.fast_secondary.status = PileStatus.OFF
        self.fast_secondary.save(update_fields=['is_enabled', 'status', 'updated_at'])

    def _create_vehicle(self, plate_no: str):
        user = UserAccount.objects.create(user_name=plate_no, password_hash='x')
        return Vehicle.objects.create(user=user, plate_no=plate_no, battery_capacity=60, current_battery_level=60)

    def _submit_fast_request(self, plate_no: str, amount: int):
        vehicle = self._create_vehicle(plate_no)
        return ChargingRequestService.submit_request(vehicle, ChargeMode.FAST, amount)

    def _resume_single_dispatch(self):
        self.config.refresh_from_db()
        self.config.waiting_dispatch_paused = False
        self.config.save(update_fields=['waiting_dispatch_paused'])
        DispatchService.try_dispatch_mode(StationConfigService.get_active_config(), ChargeMode.FAST)

    def _create_active_fast_session(self, pile: ChargingPile, plate_no: str, amount: int):
        vehicle = self._create_vehicle(plate_no)
        now = system_now()
        request = ChargingRequest.objects.create(
            request_no=f'REQ-{plate_no}',
            user=vehicle.user,
            vehicle=vehicle,
            request_mode=ChargeMode.FAST,
            request_amount=Decimal(str(amount)),
            status=RequestStatus.CHARGING,
            current_pile=pile,
            queued_at=now,
            charge_started_at=now,
        )
        ChargingSession.objects.create(
            session_no=f'SES-{plate_no}',
            request=request,
            vehicle=vehicle,
            pile=pile,
            start_time=now,
            session_status=SessionStatus.ACTIVE,
        )
        pile.status = PileStatus.CHARGING
        pile.save(update_fields=['status', 'updated_at'])
        return request

    def _active_queue_tickets(self, pile: ChargingPile):
        return list(
            QueueTicket.objects.filter(
                queue_type=QueueType.PILE_QUEUE,
                pile=pile,
                is_active=True,
            ).select_related('request__vehicle').order_by('queue_position', 'request__id')
        )

    def test_single_dispatch_keeps_fifo_candidate_selection(self):
        self._submit_fast_request('FIFO-A', 90)
        self._submit_fast_request('FIFO-B', 30)
        self._submit_fast_request('FIFO-C', 10)

        self._resume_single_dispatch()

        requests = list(
            ChargingRequest.objects.filter(request_mode=ChargeMode.FAST).order_by('request_time', 'id')
        )
        self.assertEqual([request.vehicle.plate_no for request in requests], ['FIFO-A', 'FIFO-B', 'FIFO-C'])
        self.assertEqual(requests[0].status, RequestStatus.DISPATCHED)
        self.assertEqual(requests[1].status, RequestStatus.DISPATCHED)
        self.assertEqual(requests[2].status, RequestStatus.QUEUING)

    def test_single_dispatch_optimizes_selected_batch_globally(self):
        self._submit_fast_request('OPT-LONG', 90)
        self._submit_fast_request('OPT-SHORT', 30)

        self._resume_single_dispatch()

        requests = list(
            ChargingRequest.objects.filter(request_mode=ChargeMode.FAST)
            .select_related('vehicle', 'current_pile')
            .order_by('request_time', 'id')
        )
        self.assertEqual(len(requests), 2)
        self.assertTrue(all(request.status == RequestStatus.DISPATCHED for request in requests))
        self.assertTrue(all(request.current_pile_id == self.fast_primary.id for request in requests))

        tickets = {
            ticket.request.vehicle.plate_no: ticket.queue_position
            for ticket in QueueTicket.objects.filter(
                queue_type=QueueType.PILE_QUEUE,
                pile=self.fast_primary,
                is_active=True,
            ).select_related('request__vehicle')
        }
        self.assertEqual(tickets['OPT-SHORT'], 1)
        self.assertEqual(tickets['OPT-LONG'], 2)

    def test_single_dispatch_keeps_earlier_request_first_on_tie(self):
        self._submit_fast_request('TIE-FIRST', 30)
        self._submit_fast_request('TIE-SECOND', 30)

        self._resume_single_dispatch()

        tickets = {
            ticket.request.vehicle.plate_no: ticket.queue_position
            for ticket in QueueTicket.objects.filter(
                queue_type=QueueType.PILE_QUEUE,
                pile=self.fast_primary,
                is_active=True,
            ).select_related('request__vehicle')
        }
        self.assertEqual(tickets['TIE-FIRST'], 1)
        self.assertEqual(tickets['TIE-SECOND'], 2)

    def test_single_dispatch_actual_scenario_with_two_fast_piles(self):
        enable(make_case_time(6, 0))
        try:
            self.config.refresh_from_db()
            self.config.dispatch_mode = DispatchMode.SINGLE_MIN_TOTAL
            self.config.waiting_dispatch_paused = True
            self.config.charging_queue_len = 3
            self.config.save(update_fields=['dispatch_mode', 'waiting_dispatch_paused', 'charging_queue_len'])

            self.fast_primary.status = PileStatus.CHARGING
            self.fast_primary.save(update_fields=['status', 'updated_at'])
            self.fast_secondary.is_enabled = True
            self.fast_secondary.status = PileStatus.CHARGING
            self.fast_secondary.save(update_fields=['is_enabled', 'status', 'updated_at'])

            self._create_active_fast_session(self.fast_primary, 'RUN-A', 10)
            self._create_active_fast_session(self.fast_secondary, 'RUN-B', 20)

            for plate_no, amount in [('SCENE-A', 10), ('SCENE-B', 20), ('SCENE-C', 10), ('SCENE-D', 20)]:
                self._submit_fast_request(plate_no, amount)

            self._resume_single_dispatch()

            primary_tickets = self._active_queue_tickets(self.fast_primary)
            secondary_tickets = self._active_queue_tickets(self.fast_secondary)

            self.assertEqual(
                [ticket.request.vehicle.plate_no for ticket in primary_tickets],
                ['SCENE-A', 'SCENE-B'],
            )
            self.assertEqual(
                [ticket.request.vehicle.plate_no for ticket in secondary_tickets],
                ['SCENE-C', 'SCENE-D'],
            )

            primary_completion = [
                Decimal('0.3333') + Decimal('0.3333'),
                Decimal('0.3333') + Decimal('0.3333') + Decimal('0.6667'),
            ]
            secondary_completion = [
                Decimal('0.6667') + Decimal('0.3333'),
                Decimal('0.6667') + Decimal('0.3333') + Decimal('0.6667'),
            ]
            total_completion = sum(primary_completion + secondary_completion, Decimal('0'))

            self.assertEqual(primary_completion, [Decimal('0.6666'), Decimal('1.3333')])
            self.assertEqual(secondary_completion, [Decimal('1.0000'), Decimal('1.6667')])
            self.assertEqual(total_completion, Decimal('4.6666'))
        finally:
            disable()


class RunSingleDispatchCommandTests(TestCase):
    def test_run_single_dispatch_prints_actual_dispatch_result(self):
        stdout = StringIO()

        call_command('run_single_dispatch', stdout=stdout)

        output = stdout.getvalue()
        self.assertIn('单次调度场景执行完成（已自动回滚，不影响正式环境）', output)
        self.assertIn('调度模式：single_min_total', output)
        self.assertIn('c -> F1', output)
        self.assertIn('a -> F1', output)
        self.assertIn('d -> F2', output)
        self.assertIn('b -> F2', output)
        self.assertIn('g -> T1', output)
        self.assertIn('h -> T1', output)
        self.assertIn('i -> T2', output)
        self.assertIn('j -> T2', output)
        self.assertIn('快充：e(15.0度)，f(15.0度)', output)
        self.assertIn('慢充：无', output)
        self.assertIn('快充本轮总完成时长：8.6667 小时', output)
        self.assertIn('慢充本轮总完成时长：14.1000 小时', output)
        self.assertIn('本次调度总完成时长：22.7667 小时', output)

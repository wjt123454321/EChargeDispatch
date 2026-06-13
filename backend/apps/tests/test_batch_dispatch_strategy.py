from django.core.management import call_command
from django.test import TestCase

from apps.accounts.models import UserAccount, Vehicle
from apps.charging.models import ChargingRequest
from apps.charging.services import ChargingRequestService, DispatchService
from apps.common.enums import ChargeMode, DispatchMode, PileStatus, RequestStatus
from apps.station.models import ChargingPile, SystemConfig
from apps.station.services import StationConfigService


class BatchDispatchStrategyTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('init_system')

    def setUp(self):
        self.config = SystemConfig.objects.filter(is_active=True).first()
        self.config.dispatch_mode = DispatchMode.BATCH_MIN_TOTAL
        self.config.waiting_dispatch_paused = False
        self.config.waiting_area_size = 1
        self.config.charging_queue_len = 1
        self.config.fast_queue_seq = 0
        self.config.slow_queue_seq = 0
        self.config.save(update_fields=[
            'dispatch_mode',
            'waiting_dispatch_paused',
            'waiting_area_size',
            'charging_queue_len',
            'fast_queue_seq',
            'slow_queue_seq',
        ])

        piles = list(ChargingPile.objects.order_by('pile_no'))
        for pile in piles:
            enabled = pile.pile_no in {'F1', 'T1'}
            pile.is_enabled = enabled
            pile.status = PileStatus.AVAILABLE if enabled else PileStatus.OFF
            pile.save(update_fields=['is_enabled', 'status', 'updated_at'])

    def _create_vehicle(self, plate_no: str):
        user = UserAccount.objects.create(user_name=plate_no, password_hash='x')
        return Vehicle.objects.create(user=user, plate_no=plate_no, battery_capacity=60, current_battery_level=60)

    def _submit(self, plate_no: str, mode: str, amount: int):
        vehicle = self._create_vehicle(plate_no)
        return ChargingRequestService.submit_request(vehicle, mode, amount)

    def test_batch_dispatch_starts_only_when_total_capacity_is_reached(self):
        self._submit('BATCH-A', ChargeMode.FAST, 30)
        self._submit('BATCH-B', ChargeMode.FAST, 10)

        requests = list(ChargingRequest.objects.order_by('request_time', 'id'))
        self.assertTrue(all(request.status == RequestStatus.QUEUING for request in requests))
        self.assertTrue(all(request.current_pile_id is None for request in requests))

        self._submit('BATCH-C', ChargeMode.FAST, 20)

        requests = list(
            ChargingRequest.objects.select_related('vehicle', 'current_pile').order_by('request_time', 'id')
        )
        dispatched = {request.vehicle.plate_no: request for request in requests if request.status == RequestStatus.DISPATCHED}
        waiting = [request.vehicle.plate_no for request in requests if request.status == RequestStatus.QUEUING]

        self.assertEqual(sorted(waiting), ['BATCH-A'])
        self.assertEqual(dispatched['BATCH-B'].current_pile.pile_no, 'T1')
        self.assertEqual(dispatched['BATCH-C'].current_pile.pile_no, 'F1')

    def test_batch_dispatch_does_not_top_up_until_batch_finishes(self):
        self.config.waiting_area_size = 2
        self.config.save(update_fields=['waiting_area_size'])

        self._submit('KEEP-A', ChargeMode.FAST, 40)
        self._submit('KEEP-B', ChargeMode.FAST, 30)
        self._submit('KEEP-C', ChargeMode.FAST, 20)
        self._submit('KEEP-D', ChargeMode.FAST, 10)

        initial_requests = {
            request.vehicle.plate_no: request
            for request in ChargingRequest.objects.select_related('vehicle').all()
        }
        self.assertEqual(initial_requests['KEEP-C'].status, RequestStatus.DISPATCHED)
        self.assertEqual(initial_requests['KEEP-D'].status, RequestStatus.DISPATCHED)
        self.assertEqual(initial_requests['KEEP-A'].status, RequestStatus.QUEUING)
        self.assertEqual(initial_requests['KEEP-B'].status, RequestStatus.QUEUING)

        request = initial_requests['KEEP-C']
        request.status = RequestStatus.COMPLETED
        request.save(update_fields=['status'])
        DispatchService.try_dispatch_all()

        refreshed = {
            item.vehicle.plate_no: item
            for item in ChargingRequest.objects.select_related('vehicle').all()
        }
        self.assertEqual(refreshed['KEEP-A'].status, RequestStatus.QUEUING)
        self.assertEqual(refreshed['KEEP-B'].status, RequestStatus.QUEUING)

        other = refreshed['KEEP-D']
        other.status = RequestStatus.COMPLETED
        other.save(update_fields=['status'])
        DispatchService.try_dispatch_all()

        refreshed = {
            item.vehicle.plate_no: item
            for item in ChargingRequest.objects.select_related('vehicle').all()
        }
        self.assertEqual(refreshed['KEEP-A'].status, RequestStatus.QUEUING)
        self.assertEqual(refreshed['KEEP-B'].status, RequestStatus.QUEUING)

        self._submit('KEEP-E', ChargeMode.SLOW, 5)
        refreshed = {
            item.vehicle.plate_no: item
            for item in ChargingRequest.objects.select_related('vehicle', 'current_pile').all()
        }
        self.assertEqual(refreshed['KEEP-E'].status, RequestStatus.QUEUING)

        self._submit('KEEP-F', ChargeMode.SLOW, 15)
        refreshed = {
            item.vehicle.plate_no: item
            for item in ChargingRequest.objects.select_related('vehicle', 'current_pile').all()
        }
        dispatched = {
            plate_no: request.current_pile.pile_no
            for plate_no, request in refreshed.items()
            if request.status == RequestStatus.DISPATCHED
        }
        waiting = sorted(
            plate_no for plate_no, request in refreshed.items() if request.status == RequestStatus.QUEUING
        )

        self.assertEqual(dispatched, {'KEEP-E': 'T1', 'KEEP-F': 'F1'})
        self.assertEqual(waiting, ['KEEP-A', 'KEEP-B'])

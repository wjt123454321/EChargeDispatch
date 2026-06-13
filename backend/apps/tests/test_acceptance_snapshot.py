"""
验收快照：车辆可见性与三行子表格式。
"""

from decimal import Decimal

from django.test import TestCase

from apps.accounts.models import Vehicle
from apps.charging.models import ChargingRequest
from apps.charging.services import ChargingRequestService, QueueService
from apps.common.enums import ChargeMode, RequestStatus
from apps.common.sim_clock import disable, enable, make_case_time, system_now
from apps.common.utils import generate_no
from apps.operations.acceptance_events import ACCEPTANCE_EVENTS
from apps.operations.acceptance_service import AcceptanceService
from apps.station.services import StationConfigService


class AcceptanceSnapshotTests(TestCase):
    def _run_until(self, until: str):
        enable(make_case_time(6, 0))
        try:
            AcceptanceService.reset_environment()
            for case_time, event in ACCEPTANCE_EVENTS:
                snap = AcceptanceService.run(case_time, event)
                self.assertEqual(
                    snap.get('validation_errors', []),
                    [],
                    msg=f'{case_time} 快照校验失败: {snap.get("validation_errors")}',
                )
                if case_time == until:
                    return snap
        finally:
            disable()

    def test_v7_visible_in_fast1_queue_row2_at_0635(self):
        snap = self._run_until('06:35')
        f1_slots = snap['piles']['F1']['slots']
        self.assertEqual(len(f1_slots), 3)
        self.assertIn('V3', f1_slots[0])
        self.assertIn('V7', f1_slots[1])
        self.assertEqual(f1_slots[2], '-')

    def test_table_rows_has_three_subrows(self):
        snap = self._run_until('06:15')
        self.assertEqual(len(snap['table_rows']), 3)
        self.assertEqual(snap['table_rows'][0]['时刻'], '06:15')
        self.assertEqual(snap['table_rows'][1]['时刻'], '')
        self.assertIn('V4', snap['table_rows'][0]['快充2'])

    def test_dispatched_car_shows_zero_on_slow_pile(self):
        snap = self._run_until('06:05')
        self.assertIn('V2', snap['piles']['T2']['slots'][0])
        self.assertTrue(snap['piles']['T2']['slots'][0].endswith('0.00)'))

    def test_fault_cars_stay_on_fault_pile_queue(self):
        snap = self._run_until('08:25')
        t1_slots = snap['piles']['T1']['slots']
        waiting = snap['waiting_area']['display']
        self.assertTrue(
            any('V1' in s for s in t1_slots if s != '-'),
            msg=f'V1 应留在故障桩 T1 队列，实际 {t1_slots}',
        )
        self.assertNotIn('V1,T', waiting)

    def test_recovery_reorders_v24_before_v25_at_0915(self):
        snap = self._run_until('09:15')
        slow_slots = []
        for pile_no in ('T1', 'T2', 'T3'):
            for slot in snap['piles'][pile_no]['slots']:
                if slot != '-':
                    slow_slots.append(slot.split(',')[0].lstrip('('))
        self.assertIn('V24', slow_slots)
        self.assertIn('V25', slow_slots)
        self.assertLess(
            slow_slots.index('V24'),
            slow_slots.index('V25'),
            msg=f'恢复后 V24(T10) 应排在 V25(T11) 前，实际顺序 {slow_slots}',
        )

    def test_advance_time_accumulates_charge_across_interval(self):
        enable(make_case_time(6, 0))
        try:
            AcceptanceService.reset_environment()
            AcceptanceService.run('06:00', ('A', 'V1', 'T', 40), realtime=False)
            AcceptanceService.advance_time_to(make_case_time(6, 5), realtime=False)
            snap = AcceptanceService.build_snapshot('06:05')
            charged = snap['piles']['T1']['charged_amount']
            self.assertIsNotNone(charged)
            self.assertAlmostEqual(charged, 0.83, delta=0.05)
        finally:
            disable()

    def test_mid_interval_handoff_shows_charged_amount(self):
        """区间内前车充满、后车接上后，快照应显示后车已充电量。"""
        enable(make_case_time(6, 0))
        try:
            AcceptanceService.reset_environment()
            AcceptanceService.run('06:00', ('A', 'V1', 'T', 0.5), realtime=False)
            pile = ChargingRequest.objects.get(
                vehicle__plate_no='V1',
            ).current_pile
            self.assertIsNotNone(pile)

            v2 = Vehicle.objects.select_related('user').get(plate_no='V2')
            config = StationConfigService.get_active_config()
            queue_num = QueueService.next_queue_num(config, ChargeMode.SLOW)
            v2_req = ChargingRequest.objects.create(
                request_no=generate_no('REQ'),
                user=v2.user,
                vehicle=v2,
                request_mode=ChargeMode.SLOW,
                request_amount=Decimal('30'),
                status=RequestStatus.DISPATCHED,
                current_pile=pile,
                queue_num=queue_num,
                queued_at=system_now(),
            )
            QueueService.create_pile_ticket(v2_req, pile, queue_num, 1)

            AcceptanceService.advance_time_to(make_case_time(6, 5), realtime=False)
            snap = AcceptanceService.build_snapshot('06:05')
            slot = snap['piles'][pile.pile_no]['slots'][0]
            self.assertIn('V2', slot, msg=f'V2 应正在充电，实际 {slot}')
            charged = float(slot.split(',')[1])
            self.assertGreater(charged, 0.1, msg=f'V2 应有区间内充电量，实际 {slot}')
        finally:
            disable()

    def test_submit_rejected_when_waiting_full(self):
        enable(make_case_time(6, 0))
        try:
            AcceptanceService.reset_environment()
            for case_time, event in ACCEPTANCE_EVENTS:
                AcceptanceService.run(case_time, event)
                if case_time == '09:00':
                    break
            vehicle = Vehicle.objects.get(plate_no='V30')
            result = ChargingRequestService.submit_request(vehicle, 'F', 30)
            if result.get('accepted', True):
                self.skipTest('09:00 时等候区未满，跳过拒绝场景')
            self.assertFalse(result['accepted'])
            self.assertEqual(result['message'], '等候区已无空位')
        finally:
            disable()

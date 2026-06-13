from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.db import transaction

from apps.accounts.services import AuthService
from apps.charging.models import ChargingRequest, ChargingSession, DispatchRecord
from apps.charging.services import ChargingRequestService, QueueService
from apps.common.enums import ChargeMode, DispatchMode, RequestStatus, SessionStatus
from apps.common.sim_clock import disable, enable, make_case_time, set_now, system_now
from apps.operations.acceptance_service import AcceptanceService
from apps.station.models import ChargingPile
from apps.station.services import StationConfigService


class BatchDispatchDemoService:
    """
    两次严格批量调度演示：
    1. 车辆陆续到达至满载，触发第一批调度
    2. 第一批运行期间继续有车辆入站，但不进行补位调度
    3. 第一批全部完成后，站内再次满载，触发第二批调度

    所有数据库写入均放在事务中，结果提取后回滚；CSV 在事务外写文件。
    """

    INITIAL_REQUESTS = [
        ('V1', ChargeMode.FAST, Decimal('24')),
        ('V2', ChargeMode.SLOW, Decimal('27')),
        ('V3', ChargeMode.FAST, Decimal('18')),
        ('V4', ChargeMode.SLOW, Decimal('26')),
        ('V5', ChargeMode.FAST, Decimal('22')),
        ('V6', ChargeMode.SLOW, Decimal('25')),
        ('V7', ChargeMode.FAST, Decimal('6')),
        ('V8', ChargeMode.SLOW, Decimal('28')),
        ('V9', ChargeMode.FAST, Decimal('8')),
        ('V10', ChargeMode.SLOW, Decimal('30')),
        ('V11', ChargeMode.FAST, Decimal('10')),
        ('V12', ChargeMode.SLOW, Decimal('32')),
        ('V13', ChargeMode.FAST, Decimal('12')),
        ('V14', ChargeMode.SLOW, Decimal('34')),
        ('V15', ChargeMode.FAST, Decimal('14')),
        ('V16', ChargeMode.SLOW, Decimal('36')),
        ('V17', ChargeMode.FAST, Decimal('16')),
        ('V18', ChargeMode.SLOW, Decimal('38')),
        ('V19', ChargeMode.FAST, Decimal('20')),
        ('V20', ChargeMode.SLOW, Decimal('40')),
        ('V21', ChargeMode.FAST, Decimal('42')),
        ('V22', ChargeMode.SLOW, Decimal('44')),
        ('V23', ChargeMode.FAST, Decimal('46')),
        ('V24', ChargeMode.SLOW, Decimal('48')),
        ('V25', ChargeMode.FAST, Decimal('50')),
    ]

    FOLLOW_UP_REQUESTS = [
        ('V26', ChargeMode.SLOW, Decimal('23')),
        ('V27', ChargeMode.FAST, Decimal('29')),
        ('V28', ChargeMode.SLOW, Decimal('9')),
        ('V29', ChargeMode.FAST, Decimal('31')),
        ('V30', ChargeMode.SLOW, Decimal('11')),
        ('V31', ChargeMode.FAST, Decimal('33')),
        ('V32', ChargeMode.SLOW, Decimal('13')),
        ('V33', ChargeMode.FAST, Decimal('35')),
        ('V34', ChargeMode.SLOW, Decimal('15')),
        ('V35', ChargeMode.FAST, Decimal('37')),
        ('V36', ChargeMode.SLOW, Decimal('17')),
        ('V37', ChargeMode.FAST, Decimal('39')),
        ('V38', ChargeMode.SLOW, Decimal('19')),
        ('V39', ChargeMode.FAST, Decimal('41')),
        ('V40', ChargeMode.SLOW, Decimal('21')),
    ]

    FIELDNAMES = ['时刻', '事件', '快充1', '快充2', '慢充1', '慢充2', '慢充3', '等候区']

    @staticmethod
    def run():
        with transaction.atomic():
            result = BatchDispatchDemoService._run_impl()
            transaction.set_rollback(True)
        return result

    @staticmethod
    def _run_impl():
        AcceptanceService.reset_environment()
        BatchDispatchDemoService._register_extra_vehicles(40)
        BatchDispatchDemoService._configure_batch_mode()

        rows = []
        batch_reports = []
        enable(make_case_time(6, 0))
        try:
            BatchDispatchDemoService._simulate(rows, batch_reports)
        finally:
            disable()
        return {'rows': rows, 'batch_reports': batch_reports}

    @staticmethod
    def _register_extra_vehicles(max_vehicle_no: int):
        for i in range(31, max_vehicle_no + 1):
            car_id = f'V{i}'
            AuthService.register(car_id, car_id, 60, '123456')

    @staticmethod
    def _configure_batch_mode():
        config = StationConfigService.get_active_config()
        config.dispatch_mode = DispatchMode.BATCH_MIN_TOTAL
        config.waiting_dispatch_paused = False
        config.waiting_area_size = 10
        config.charging_queue_len = 3
        config.fast_queue_seq = 0
        config.slow_queue_seq = 0
        config.save(update_fields=[
            'dispatch_mode',
            'waiting_dispatch_paused',
            'waiting_area_size',
            'charging_queue_len',
            'fast_queue_seq',
            'slow_queue_seq',
        ])

    @staticmethod
    def _set_case_time(hour: int, minute: int):
        set_now(make_case_time(hour, minute))

    @staticmethod
    def _append_snapshot(rows: list[dict], event_desc: str):
        case_time = system_now().strftime('%H:%M')
        snapshot = AcceptanceService.build_snapshot(case_time)
        snapshot['validation_errors'] = AcceptanceService.validate_snapshot(snapshot)
        if snapshot['validation_errors']:
            raise AssertionError(f'批量调度快照校验失败 [{case_time}]: {snapshot["validation_errors"]}')
        for index, row in enumerate(snapshot['table_rows']):
            rows.append({
                **row,
                '事件': event_desc if index == 0 else '',
            })

    @staticmethod
    def _submit_request(car_id: str, mode: str, amount: Decimal):
        vehicle = AcceptanceService._vehicle(car_id)
        ChargingRequestService.submit_request(vehicle, mode, amount)
        AcceptanceService.stabilize_system()

    @staticmethod
    def _active_count() -> int:
        return ChargingRequest.objects.filter(status__in=RequestStatus.ACTIVE).count()

    @staticmethod
    def _batch_active_count() -> int:
        return ChargingRequest.objects.filter(
            status__in={
                RequestStatus.DISPATCHED,
                RequestStatus.CHARGING,
                RequestStatus.PENDING_RESCHEDULE,
            },
            current_pile__isnull=False,
        ).count()

    @staticmethod
    def _total_capacity() -> int:
        config = StationConfigService.get_active_config()
        pile_count = config.fast_pile_num + config.slow_pile_num
        return config.waiting_area_size + config.charging_queue_len * pile_count

    @staticmethod
    def _charging_area_capacity() -> int:
        config = StationConfigService.get_active_config()
        return config.charging_queue_len * ChargingPile.objects.filter(is_enabled=True).count()

    @staticmethod
    def _describe_arrivals(arrivals: list[tuple[str, str, Decimal]]) -> str:
        if not arrivals:
            return '本时段无新入站车辆'
        joined = '、'.join(
            f'{car_id}({mode},{float(amount):.0f})' for car_id, mode, amount in arrivals
        )
        return f'本时段入站车辆：{joined}'

    @staticmethod
    def _build_batch_report(batch_no: int):
        now = system_now()
        report = {
            'batch_no': batch_no,
            'trigger_time': now.strftime('%H:%M'),
            'entries': [],
            'cross_mode_entries': [],
            'non_fifo_examples': [],
            'total_completion_hours': Decimal('0'),
            'charging_area_capacity': BatchDispatchDemoService._charging_area_capacity(),
            'total_capacity': BatchDispatchDemoService._total_capacity(),
        }

        for pile in ChargingPile.objects.filter(is_enabled=True).order_by('id'):
            current = Decimal('0')
            session = ChargingSession.objects.filter(
                pile=pile,
                session_status=SessionStatus.ACTIVE,
                end_time__isnull=True,
            ).select_related('request', 'vehicle').order_by('start_time', 'id').first()
            if session and session.request.status == RequestStatus.CHARGING:
                current += session.request.request_amount / pile.rated_power
                report['entries'].append({
                    'car_id': session.vehicle.plate_no,
                    'request_mode': session.request.request_mode,
                    'request_time': session.request.request_time,
                    'pile_no': pile.pile_no,
                    'pile_type': pile.pile_type,
                    'position': 1,
                    'request_amount': float(session.request.request_amount),
                    'completion_hours': float(current.quantize(Decimal('0.0001'))),
                })
                report['total_completion_hours'] += current

            start_position = 2 if session else 1
            position = start_position
            for req in QueueService.pile_queue_requests(pile):
                current += req.request_amount / pile.rated_power
                report['entries'].append({
                    'car_id': req.vehicle.plate_no,
                    'request_mode': req.request_mode,
                    'request_time': req.request_time,
                    'pile_no': pile.pile_no,
                    'pile_type': pile.pile_type,
                    'position': position,
                    'request_amount': float(req.request_amount),
                    'completion_hours': float(current.quantize(Decimal('0.0001'))),
                })
                report['total_completion_hours'] += current
                position += 1

        arrival_order = sorted(
            report['entries'],
            key=lambda item: (item['request_time'], item['car_id']),
        )
        arrival_rank = {item['car_id']: index + 1 for index, item in enumerate(arrival_order)}

        for entry in report['entries']:
            entry['arrival_rank'] = arrival_rank[entry['car_id']]
            entry['cross_mode'] = entry['request_mode'] != entry['pile_type']

        report['entries'].sort(key=lambda item: (item['pile_no'], item['position'], item['car_id']))
        report['cross_mode_entries'] = [
            entry for entry in report['entries'] if entry['cross_mode']
        ]

        for pile_no in sorted({entry['pile_no'] for entry in report['entries']}):
            pile_entries = [entry for entry in report['entries'] if entry['pile_no'] == pile_no]
            for later_index in range(1, len(pile_entries)):
                current_entry = pile_entries[later_index]
                for earlier_index in range(later_index):
                    previous_entry = pile_entries[earlier_index]
                    if current_entry['arrival_rank'] < previous_entry['arrival_rank']:
                        report['non_fifo_examples'].append({
                            'pile_no': pile_no,
                            'ahead_car_id': current_entry['car_id'],
                            'ahead_mode': current_entry['request_mode'],
                            'ahead_arrival_rank': current_entry['arrival_rank'],
                            'behind_car_id': previous_entry['car_id'],
                            'behind_mode': previous_entry['request_mode'],
                            'behind_arrival_rank': previous_entry['arrival_rank'],
                        })
                        break
                if report['non_fifo_examples']:
                    break
            if report['non_fifo_examples']:
                break

        report['total_completion_hours'] = report['total_completion_hours'].quantize(Decimal('0.0001'))
        return report

    @staticmethod
    def _build_sample_description(
        interval_start,
        interval_end,
        arrivals,
        triggered_report,
        batch_reports,
        current_batch_count,
    ) -> str:
        active = BatchDispatchDemoService._active_count()
        total_capacity = BatchDispatchDemoService._total_capacity()

        if current_batch_count == 0 and len(batch_reports) == 0:
            stage = '初始攒批阶段'
        elif current_batch_count > 0 and len(batch_reports) == 1:
            stage = '第一批运行中'
        elif current_batch_count == 0 and len(batch_reports) == 1:
            stage = '第一批已完成，等待第二批满载'
        else:
            stage = '第二批运行中'

        time_range = f'{interval_start.strftime("%H:%M")}-{interval_end.strftime("%H:%M")}'
        parts = [
            stage,
            f'时间段 {time_range}',
            BatchDispatchDemoService._describe_arrivals(arrivals),
            f'站内活跃车辆 {active}/{total_capacity}',
        ]

        if triggered_report is not None:
            latest = triggered_report
            parts.append(
                f'触发第{latest["batch_no"]}批批量调度；本批进入充电区 {len(latest["entries"])} 辆；'
                f'本批总完成时长 {float(latest["total_completion_hours"]):.4f} 小时'
            )
        elif current_batch_count > 0:
            parts.append('当前批次已固定；即使中途出现空位也不补位')
        else:
            parts.append('当前无批次运行，继续等待下一次满载触发')
        return '；'.join(parts)

    @staticmethod
    def _simulate(rows: list[dict], batch_reports: list[dict]):
        current = make_case_time(6, 0)
        end = make_case_time(16, 0)
        initial = list(BatchDispatchDemoService.INITIAL_REQUESTS)
        follow_up = list(BatchDispatchDemoService.FOLLOW_UP_REQUESTS)
        pending_arrivals = []
        interval_start = current
        triggered_report = None
        previous_dispatch_record_count = 0

        while current <= end:
            set_now(current)
            AcceptanceService.stabilize_system()

            arrivals_this_minute = []
            if initial:
                car_id, mode, amount = initial.pop(0)
                BatchDispatchDemoService._submit_request(car_id, mode, amount)
                arrivals_this_minute.append((car_id, mode, amount))
            else:
                free_slots = BatchDispatchDemoService._total_capacity() - BatchDispatchDemoService._active_count()
                while follow_up and free_slots > 0:
                    car_id, mode, amount = follow_up.pop(0)
                    BatchDispatchDemoService._submit_request(car_id, mode, amount)
                    arrivals_this_minute.append((car_id, mode, amount))
                    free_slots -= 1

            if arrivals_this_minute:
                pending_arrivals.extend(arrivals_this_minute)

            current_batch_count = BatchDispatchDemoService._batch_active_count()
            current_dispatch_record_count = DispatchRecord.objects.count()
            if current_dispatch_record_count > previous_dispatch_record_count:
                triggered_report = BatchDispatchDemoService._build_batch_report(len(batch_reports) + 1)
                batch_reports.append(triggered_report)
                previous_dispatch_record_count = current_dispatch_record_count

            if current.minute % 5 == 0:
                event_desc = BatchDispatchDemoService._build_sample_description(
                    interval_start,
                    current,
                    pending_arrivals,
                    triggered_report,
                    batch_reports,
                    current_batch_count,
                )
                BatchDispatchDemoService._append_snapshot(rows, event_desc)
                pending_arrivals = []
                interval_start = current + timedelta(minutes=1)
                triggered_report = None

            if len(batch_reports) >= 2 and current_batch_count > 0 and current.minute % 5 == 0:
                return

            current += timedelta(minutes=1)

        raise AssertionError('未在预期时间内完成两次批量调度演示')

    @staticmethod
    def write_csv(path: str, rows: list[dict]):
        import csv

        with open(path, 'w', newline='', encoding='utf-8-sig') as file_obj:
            writer = csv.DictWriter(file_obj, fieldnames=BatchDispatchDemoService.FIELDNAMES)
            writer.writeheader()
            for row in rows:
                writer.writerow({key: row.get(key, '') for key in BatchDispatchDemoService.FIELDNAMES})

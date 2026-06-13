"""
验收测试：环境重置、事件执行、状态快照。
"""

import time
from datetime import timedelta
from decimal import Decimal

from django.core.management import call_command
from django.db import transaction

from apps.accounts.models import AdminAccount, Vehicle
from apps.accounts.services import AuthService
from apps.billing.models import Bill, ChargeDetail
from apps.charging.models import ChargingRequest, ChargingSession, DispatchRecord, QueueTicket
from apps.charging.services import (
    ChargingRequestService,
    ChargingSessionService,
    DispatchService,
    QueueService,
)
from apps.common.enums import (
    ErrorCode,
    PileStatus,
    RequestStatus,
    SERVICE_FEE_RATE,
    SessionStatus,
    VehicleStatus,
)
from apps.common.exceptions import AppException
from apps.common.sim_clock import (
    is_active,
    make_case_time,
    set_now,
    sim_delta_to_real_seconds,
    system_now,
)
from apps.common.utils import calculate_cross_period_fee, compute_charged_amount
from apps.operations.acceptance_events import ACCEPTANCE_EVENTS, DEFAULT_UNTIL, PILE_COLUMNS
from apps.operations.models import FaultRecord
from apps.operations.services import FaultService
from apps.station.models import ChargingPile
from apps.station.services import StationConfigService

# 方案2：每模拟 1 分钟前进一步，网页轮询快照时可见电量上涨
SIM_STEP = timedelta(minutes=1)
MAX_ADVANCE_ITERATIONS = 10000


class AcceptanceService:
    @staticmethod
    def parse_case_time(label: str):
        """'06:05' 或 '1:35+1'（调度结束标记）"""
        if '+' in label:
            return None
        parts = label.split(':')
        return make_case_time(int(parts[0]), int(parts[1]))

    @staticmethod
    @transaction.atomic
    def reset_environment():
        """清空业务数据并重新初始化充电站。"""
        ChargingSession.objects.all().delete()
        QueueTicket.objects.all().delete()
        DispatchRecord.objects.all().delete()
        ChargingRequest.objects.all().delete()
        ChargeDetail.objects.all().delete()
        Bill.objects.all().delete()
        FaultRecord.objects.all().delete()

        call_command('init_system', verbosity=0)

        config = StationConfigService.get_active_config()
        config.fault_strategy = 'priority'
        config.charging_queue_len = 3
        config.waiting_area_size = 10
        config.fast_queue_seq = 0
        config.slow_queue_seq = 0
        config.waiting_dispatch_paused = False
        config.save()

        # 注册 V1–V30
        for i in range(1, 31):
            car_id = f'V{i}'
            if not Vehicle.objects.filter(plate_no=car_id).exists():
                AuthService.register(car_id, car_id, 60, '123456')

        Vehicle.objects.update(
            vehicle_status=VehicleStatus.IDLE,
            is_charging=False,
        )

    @staticmethod
    def _acceptance_admin_id():
        """验收 B 类事件使用的管理员 ID（init_system 创建）。"""
        admin = AdminAccount.objects.order_by('id').first()
        return admin.id if admin else None

    @staticmethod
    def _vehicle(car_id: str) -> Vehicle:
        vehicle = Vehicle.objects.filter(plate_no=car_id).select_related('user').first()
        if not vehicle:
            raise AppException(ErrorCode.USER_NOT_FOUND, f'车辆 {car_id} 未注册')
        return vehicle

    @staticmethod
    def _pile(pile_no: str) -> ChargingPile:
        pile = ChargingPile.objects.filter(pile_no=pile_no).first()
        if not pile:
            raise AppException(ErrorCode.PILE_NOT_FOUND, f'充电桩 {pile_no} 不存在')
        return pile

    @staticmethod
    def _earliest_completion_between(current, limit):
        """返回 (current, limit] 内最早的充满时刻；无则 None。"""
        earliest = None
        sessions = ChargingSession.objects.filter(
            session_status=SessionStatus.ACTIVE,
            end_time__isnull=True,
        ).select_related('request', 'pile')
        for session in sessions:
            if session.request.status != RequestStatus.CHARGING:
                continue
            charged = compute_charged_amount(session, current)
            need = session.request.request_amount - charged
            if need <= 0:
                continue
            power = session.pile.rated_power
            if not power or power <= 0:
                continue
            hours = Decimal(str(need)) / Decimal(str(power))
            completion = current + timedelta(seconds=float(hours) * 3600)
            if completion <= current or completion > limit:
                continue
            if earliest is None or completion < earliest:
                earliest = completion
        return earliest

    @staticmethod
    def advance_time_to(target_moment, realtime: bool = False):
        """
        将模拟时间推进到 target_moment（不早于当前时刻）。

        方案1：在充满时刻精确跳转，区间内换车电量正确。
        方案2：每模拟 1 分钟前进一步，HTTP 快照可看到电量上涨。
        realtime=True 时按 1:10 真实等待；False 时瞬间推进（--fast）。
        """
        if not is_active() or not target_moment:
            return

        for _ in range(MAX_ADVANCE_ITERATIONS):
            current = system_now()
            if current >= target_moment:
                return

            candidates = [target_moment]
            minute_tick = current + SIM_STEP
            if minute_tick <= target_moment:
                candidates.append(minute_tick)

            completion = AcceptanceService._earliest_completion_between(current, target_moment)
            if completion:
                candidates.append(completion)

            next_stop = min(c for c in candidates if c > current)

            if realtime:
                sim_seconds = (next_stop - current).total_seconds()
                real_seconds = sim_delta_to_real_seconds(sim_seconds)
                if real_seconds > 0:
                    time.sleep(real_seconds)

            set_now(next_stop)
            AcceptanceService.stabilize_system()

        raise RuntimeError('advance_time_to 超过最大迭代次数')

    @staticmethod
    def auto_complete_full_charges():
        """已充满请求电量的会话自动结束，释放桩位。"""
        completed = []
        sessions = ChargingSession.objects.filter(
            session_status=SessionStatus.ACTIVE,
            end_time__isnull=True,
        ).select_related('vehicle', 'request', 'pile')
        for session in sessions:
            if session.request.status != RequestStatus.CHARGING:
                continue
            charged = compute_charged_amount(session, system_now())
            if charged + Decimal('0.0001') >= session.request.request_amount:
                try:
                    ChargingSessionService.end_charging(session.vehicle)
                    completed.append(session.vehicle.plate_no)
                except AppException:
                    pass
        return completed

    @staticmethod
    def retry_pending_reschedule():
        """故障桩队列车辆优先重调度；无空位则继续留在故障桩队列。"""
        from apps.operations.services import RescheduleService

        config = StationConfigService.get_active_config()
        pending = list(
            ChargingRequest.objects.filter(status=RequestStatus.PENDING_RESCHEDULE)
            .select_related('vehicle', 'current_pile')
            .order_by('queued_at', 'id')
        )
        for request in pending:
            exclude_pile_id = None
            if request.current_pile and request.current_pile.status == PileStatus.FAULT:
                exclude_pile_id = request.current_pile_id
            if exclude_pile_id:
                pile = RescheduleService._best_reschedule_pile(request, config, exclude_pile_id)
            else:
                pile = DispatchService._best_pile_for_request(request, config)
                if pile and not DispatchService._pile_has_slot(pile, config):
                    pile = None
            if not pile:
                continue
            request.status = RequestStatus.DISPATCHED
            request.current_pile = pile
            request.queued_at = system_now()
            request.save(update_fields=['status', 'current_pile', 'queued_at'])
            position = DispatchService._pile_queue_count(pile) + 1
            QueueService.create_pile_ticket(request, pile, request.queue_num, position)

        RescheduleService.sync_waiting_dispatch_pause(config)

    @staticmethod
    def stabilize_system(max_rounds=25):
        """
        推进模拟：满电结束 → 重调度 → 派队 → 自动启充，直到状态稳定。
        在每个验收时刻执行事件前调用，释放桩位、清等候区。
        """
        for _ in range(max_rounds):
            changed = False

            if AcceptanceService.auto_complete_full_charges():
                changed = True

            before_pending = ChargingRequest.objects.filter(
                status=RequestStatus.PENDING_RESCHEDULE,
            ).count()
            AcceptanceService.retry_pending_reschedule()
            if ChargingRequest.objects.filter(
                status=RequestStatus.PENDING_RESCHEDULE,
            ).count() < before_pending:
                changed = True

            before_waiting = QueueService.waiting_area_used()
            DispatchService.try_dispatch_all()
            AcceptanceService.try_auto_start_all()
            after_waiting = QueueService.waiting_area_used()
            if after_waiting < before_waiting:
                changed = True

            if AcceptanceService.auto_complete_full_charges():
                changed = True

            if not changed:
                break

    @staticmethod
    def submit_charging_request(vehicle, mode: str, amount):
        """提交充电请求；等候区满且无同模式桩位时返回 accepted=false，不中断验收。"""
        AcceptanceService.stabilize_system(max_rounds=40)
        result = ChargingRequestService.submit_request(vehicle, mode, amount)
        if result.get('accepted', True):
            return result
        AcceptanceService.stabilize_system(max_rounds=60)
        return ChargingRequestService.submit_request(vehicle, mode, amount)

    @staticmethod
    def try_auto_start_all():
        """队首车辆自动开始充电（模拟插枪确认）；桩上已有车在充时不得启充下一辆。"""
        piles = ChargingPile.objects.filter(
            is_enabled=True,
            status__in={PileStatus.AVAILABLE, PileStatus.CHARGING},
        )
        for pile in piles:
            if ChargingSession.objects.filter(
                pile=pile,
                session_status=SessionStatus.ACTIVE,
                end_time__isnull=True,
            ).exists():
                continue
            first = ChargingRequest.objects.filter(
                current_pile=pile,
                status=RequestStatus.DISPATCHED,
            ).order_by('queued_at', 'id').first()
            if not first:
                continue
            if ChargingSession.objects.filter(request=first).exists():
                continue
            if ChargingSessionService.get_active_session(first.vehicle):
                continue
            try:
                ChargingSessionService.start_charging(first.vehicle, pile.id)
            except AppException:
                pass

    @staticmethod
    def compute_current_fee(session) -> Decimal:
        """充电中实时费用（充电费 + 服务费）。"""
        now = system_now()
        charged = compute_charged_amount(session, now)
        if charged <= 0:
            return Decimal('0')
        charge_fee, _ = calculate_cross_period_fee(session.start_time, now, charged)
        service_fee = (charged * Decimal(str(SERVICE_FEE_RATE))).quantize(Decimal('0.01'))
        return (charge_fee + service_fee).quantize(Decimal('0.01'))

    @staticmethod
    def _format_pile_slot(car_id: str, charged, fee) -> str:
        return f"({car_id},{float(charged):.2f},{float(fee):.2f})"

    @staticmethod
    def _build_pile_slots(pile: ChargingPile, queue_len: int, now) -> list:
        """
        单桩最多 queue_len 行：队首正在充（有电量/费用），后续排队为 (车,0.00,0.00)。
        与 pile_queue_detail 一致，按队列顺位填充。
        """
        slots = []
        if not pile:
            return ['-'] * queue_len

        session = ChargingSession.objects.filter(
            pile=pile,
            session_status=SessionStatus.ACTIVE,
            end_time__isnull=True,
        ).select_related('vehicle', 'request').order_by('start_time', 'id').first()
        if session:
            charged = compute_charged_amount(session, now)
            fee = AcceptanceService.compute_current_fee(session)
            slots.append(AcceptanceService._format_pile_slot(
                session.vehicle.plate_no, charged, fee,
            ))

        for req in QueueService.pile_queue_requests(pile):
            slots.append(AcceptanceService._format_pile_slot(
                req.vehicle.plate_no, 0, 0,
            ))

        for req in ChargingRequest.objects.filter(
            current_pile=pile,
            status=RequestStatus.PENDING_RESCHEDULE,
        ).select_related('vehicle').order_by('queued_at', 'id'):
            slots.append(AcceptanceService._format_pile_slot(
                req.vehicle.plate_no, 0, 0,
            ))

        while len(slots) < queue_len:
            slots.append('-')
        return slots[:queue_len]

    @staticmethod
    def validate_snapshot(snap: dict) -> list:
        """
        校验快照是否覆盖所有活跃请求，且每桩最多一个活跃充电会话。
        返回错误信息列表，空列表表示通过。
        """
        errors = []
        visible = set()
        for pile_no in PILE_COLUMNS:
            for slot in snap['piles'][pile_no]['slots']:
                if slot != '-':
                    visible.add(slot.split(',')[0].lstrip('('))
        for item in snap['waiting_area']['items']:
            visible.add(item['car_id'])

        active = ChargingRequest.objects.filter(
            status__in=RequestStatus.ACTIVE,
        ).select_related('vehicle', 'current_pile')
        for req in active:
            car = req.vehicle.plate_no
            if car not in visible:
                pile_no = req.current_pile.pile_no if req.current_pile else None
                errors.append(
                    f'{car} 状态={req.status} 桩={pile_no} 未出现在快照中',
                )

        for pile_no in PILE_COLUMNS:
            pile = ChargingPile.objects.filter(pile_no=pile_no).first()
            if not pile:
                continue
            active_count = ChargingSession.objects.filter(
                pile=pile,
                session_status=SessionStatus.ACTIVE,
                end_time__isnull=True,
            ).count()
            if active_count > 1:
                errors.append(f'{pile_no} 同时存在 {active_count} 个活跃充电会话')

        return errors

    @staticmethod
    def build_snapshot(case_time: str = None) -> dict:
        """生成验收填表格式快照（每时刻 3 行子表）。"""
        now = system_now()
        config = StationConfigService.get_active_config()
        queue_len = config.charging_queue_len

        piles_data = {}
        piles_slots = {}
        for pile_no in PILE_COLUMNS:
            pile = ChargingPile.objects.filter(pile_no=pile_no).first()
            slots = AcceptanceService._build_pile_slots(pile, queue_len, now)
            piles_slots[pile_no] = slots

            head = slots[0] if slots else '-'
            car_id = None
            charged_amount = None
            current_fee = None
            if head != '-':
                car_id = head.split(',')[0].lstrip('(')
                try:
                    charged_amount = float(head.split(',')[1])
                    current_fee = float(head.split(',')[2].rstrip(')'))
                except (IndexError, ValueError):
                    pass

            piles_data[pile_no] = {
                'slots': slots,
                'display': head,
                'car_id': car_id,
                'charged_amount': charged_amount,
                'current_fee': current_fee,
            }

        waiting = ChargingRequest.objects.filter(
            status=RequestStatus.QUEUING,
        ).select_related('vehicle').order_by('request_time', 'id')

        waiting_items = []
        waiting_parts = []
        for req in waiting:
            part = f"({req.vehicle.plate_no},{req.request_mode},{float(req.request_amount):.2f})"
            waiting_parts.append(part)
            waiting_items.append({
                'car_id': req.vehicle.plate_no,
                'request_mode': req.request_mode,
                'request_amount': float(req.request_amount),
                'queue_num': req.queue_num,
                'status': req.status,
            })

        waiting_display = '-'.join(waiting_parts) if waiting_parts else '-'
        table_rows = AcceptanceService.format_table_rows(
            case_time, piles_slots, waiting_display, queue_len,
        )
        return {
            'case_time': case_time,
            'sim_time': now.isoformat(),
            'sim_active': is_active(),
            'queue_rows': queue_len,
            'piles': piles_data,
            'waiting_area': {
                'display': waiting_display,
                'used': len(waiting_items),
                'capacity': config.waiting_area_size,
                'items': waiting_items,
            },
            'table_rows': table_rows,
            'table_row': table_rows[0] if table_rows else {},
        }

    @staticmethod
    def format_table_rows(case_time, piles_slots, waiting_display, queue_len):
        """按作业用例表格式生成 queue_len 行（时刻/事件/等候区仅首行填写）。"""
        if not case_time:
            case_time = system_now().strftime('%H:%M')
        rows = []
        for i in range(queue_len):
            rows.append({
                '时刻': case_time if i == 0 else '',
                '快充1': piles_slots['F1'][i],
                '快充2': piles_slots['F2'][i],
                '慢充1': piles_slots['T1'][i],
                '慢充2': piles_slots['T2'][i],
                '慢充3': piles_slots['T3'][i],
                '等候区': waiting_display if i == 0 else '',
            })
        return rows

    @staticmethod
    @transaction.atomic
    def execute_event(event: tuple):
        """执行单条验收事件。到达被拒时返回 submit 结果（accepted=false）。"""
        kind = event[0]
        submit_result = None

        if kind == 'A':
            car_id, action, value = event[1], event[2], event[3]
            vehicle = AcceptanceService._vehicle(car_id)

            if action in ('F', 'T'):
                submit_result = AcceptanceService.submit_charging_request(vehicle, action, value)
            elif action == 'O':
                req = ChargingRequestService.get_active_request(vehicle)
                if not req:
                    return
                if req.status == RequestStatus.CHARGING:
                    ChargingSessionService.end_charging(vehicle)
                else:
                    ChargingSessionService.cancel_charging(vehicle)
            else:
                raise ValueError(f'未知用户操作: {action}')

        elif kind == 'B':
            pile_no, action, flag = event[1], event[2], event[3]
            pile = AcceptanceService._pile(pile_no)
            admin_id = AcceptanceService._acceptance_admin_id()
            if action == 'O' and flag == 0:
                FaultService.report_fault(pile.id, admin_id=admin_id)
            elif action == 'O' and flag == 1:
                FaultService.recover_fault(pile.id, admin_id=admin_id)
            else:
                raise ValueError(f'未知管理操作: {event}')

        elif kind == 'C':
            car_id, action, amount = event[1], event[2], event[3]
            if action == 'O':
                vehicle = AcceptanceService._vehicle(car_id)
                ChargingRequestService.update_amount(vehicle, amount)
            else:
                raise ValueError(f'未知修改操作: {event}')

        else:
            raise ValueError(f'未知事件类型: {kind}')

        DispatchService.try_dispatch_all()
        AcceptanceService.try_auto_start_all()
        return submit_result

    @staticmethod
    def filter_events(until: str = DEFAULT_UNTIL):
        """截取到指定用例时刻（含）。"""
        result = []
        for case_time, event in ACCEPTANCE_EVENTS:
            result.append((case_time, event))
            if case_time == until:
                break
        return result

    @staticmethod
    def run(case_time: str, event: tuple, event_desc: str = '', realtime: bool = False) -> dict:
        """推进模拟时间、执行事件、返回快照。"""
        moment = AcceptanceService.parse_case_time(case_time)
        if moment:
            AcceptanceService.advance_time_to(moment, realtime=realtime)

        # 到达事件时刻后先推进充电完成与调度，再执行本条事件
        AcceptanceService.stabilize_system()
        submit_result = AcceptanceService.execute_event(event)
        AcceptanceService.stabilize_system()
        snapshot = AcceptanceService.build_snapshot(case_time)
        snapshot['event'] = event_desc or str(event)
        if isinstance(submit_result, dict) and not submit_result.get('accepted', True):
            snapshot['request_rejected'] = submit_result.get('message', '等候区已无空位')
        snapshot['validation_errors'] = AcceptanceService.validate_snapshot(snapshot)
        return snapshot

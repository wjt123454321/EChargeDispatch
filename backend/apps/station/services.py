from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from apps.charging.models import ChargingSession, QueueTicket
from apps.common.enums import (
    DispatchMode,
    ErrorCode,
    FaultStrategy,
    PileStatus,
    QueueType,
    RequestStatus,
)
from apps.common.exceptions import AppException

from .models import ChargingPile, ChargingStation, SystemConfig


class StationConfigService:
    @staticmethod
    def get_active_config():
        config = SystemConfig.objects.filter(is_active=True).select_related('station').first()
        if not config:
            raise AppException(ErrorCode.VALIDATION_ERROR, '系统未初始化')
        return config

    @staticmethod
    def get_station():
        station = ChargingStation.objects.first()
        if not station:
            raise AppException(ErrorCode.VALIDATION_ERROR, '系统未初始化')
        return station

    @staticmethod
    def to_dict(config: SystemConfig):
        return {
            'station_id': config.station.station_code,
            'fast_pile_num': config.fast_pile_num,
            'slow_pile_num': config.slow_pile_num,
            'waiting_area_size': config.waiting_area_size,
            'charging_queue_len': config.charging_queue_len,
            'fault_strategy': config.fault_strategy,
            'dispatch_mode': config.dispatch_mode,
            'service_price': float(config.service_price),
        }

    @staticmethod
    def update_config(data: dict):
        config = StationConfigService.get_active_config()
        allowed = {
            'fast_pile_num', 'slow_pile_num', 'waiting_area_size', 'charging_queue_len',
            'fault_strategy', 'dispatch_mode',
        }
        for key, value in data.items():
            if key in allowed and value is not None:
                if key == 'fault_strategy' and value not in {FaultStrategy.PRIORITY, FaultStrategy.TIME_ORDER}:
                    raise AppException(ErrorCode.VALIDATION_ERROR, '参数校验失败')
                if key == 'dispatch_mode' and value not in {
                    DispatchMode.NORMAL, DispatchMode.SINGLE_MIN_TOTAL, DispatchMode.BATCH_MIN_TOTAL
                }:
                    raise AppException(ErrorCode.VALIDATION_ERROR, '参数校验失败')
                setattr(config, key, value)
        config.save()
        return StationConfigService.to_dict(config)


class ChargingPileService:
    @staticmethod
    def get_pile(pile_id):
        pile = ChargingPile.objects.filter(id=pile_id).first()
        if not pile:
            raise AppException(ErrorCode.PILE_NOT_FOUND, '充电桩不存在')
        return pile

    @staticmethod
    def _current_car(pile: ChargingPile):
        session = ChargingSession.objects.filter(
            pile=pile, session_status='active', end_time__isnull=True
        ).select_related('vehicle', 'request').first()
        if not session:
            return None
        from apps.common.utils import compute_charged_amount
        return {
            'car_id': session.vehicle.plate_no,
            'request_id': session.request_id,
            'charged_amount': float(compute_charged_amount(session)),
        }

    @staticmethod
    def pile_to_dict(pile: ChargingPile, config: SystemConfig):
        from apps.charging.services import QueueService
        queue_used = QueueService.pile_occupancy_count(pile)
        return {
            'pile_id': pile.id,
            'pile_no': pile.pile_no,
            'mode': pile.pile_type,
            'mode_label': pile.mode_label,
            'power': float(pile.rated_power),
            'status': pile.status,
            'queue_used': queue_used,
            'queue_total': config.charging_queue_len,
            'current_car': ChargingPileService._current_car(pile),
            'total_charge_num': pile.total_charge_num,
            'total_charge_time': float(pile.total_charge_time),
            'total_charge_capacity': float(pile.total_charge_capacity),
        }

    @staticmethod
    def list_piles_status():
        config = StationConfigService.get_active_config()
        station = config.station
        piles = ChargingPile.objects.filter(station=station).order_by('pile_no')
        return [ChargingPileService.pile_to_dict(p, config) for p in piles]

    @staticmethod
    def power_on(pile_id):
        pile = ChargingPileService.get_pile(pile_id)
        if pile.status not in {PileStatus.OFF, PileStatus.STANDBY}:
            raise AppException(ErrorCode.PILE_STATUS_ERROR, '充电桩状态不允许操作')
        pile.status = PileStatus.STANDBY
        pile.save(update_fields=['status', 'updated_at'])
        return ChargingPileService.pile_to_dict(pile, StationConfigService.get_active_config())

    @staticmethod
    def start_pile(pile_id):
        pile = ChargingPileService.get_pile(pile_id)
        if pile.status not in {PileStatus.STANDBY, PileStatus.OFF}:
            raise AppException(ErrorCode.PILE_STATUS_ERROR, '充电桩状态不允许操作')
        pile.status = PileStatus.AVAILABLE
        pile.is_enabled = True
        pile.last_heartbeat_at = timezone.now()
        pile.save(update_fields=['status', 'is_enabled', 'last_heartbeat_at', 'updated_at'])
        from apps.charging.services import DispatchService
        DispatchService.try_dispatch_all()
        return ChargingPileService.pile_to_dict(pile, StationConfigService.get_active_config())

    @staticmethod
    def power_off(pile_id):
        pile = ChargingPileService.get_pile(pile_id)
        has_queue = QueueTicket.objects.filter(
            pile=pile, queue_type=QueueType.PILE_QUEUE, is_active=True
        ).exists()
        has_charging = ChargingSession.objects.filter(
            pile=pile, session_status='active', end_time__isnull=True
        ).exists()
        if has_queue or has_charging:
            raise AppException(ErrorCode.PILE_STATUS_ERROR, '充电桩状态不允许操作')
        pile.status = PileStatus.OFF
        pile.is_enabled = False
        pile.save(update_fields=['status', 'is_enabled', 'updated_at'])
        return ChargingPileService.pile_to_dict(pile, StationConfigService.get_active_config())

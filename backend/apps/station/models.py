from django.db import models

from apps.common.enums import (
    DispatchMode,
    FaultStrategy,
    PileStatus,
    SLOW_CHARGE_POWER,
    FAST_CHARGE_POWER,
    ChargeMode,
)
from apps.common.models import BaseModel


class ChargingStation(BaseModel):
    station_code = models.CharField(max_length=32, unique=True)
    station_name = models.CharField(max_length=128)
    status = models.CharField(max_length=20, default='active')

    class Meta:
        db_table = 'station_charging_station'


class SystemConfig(BaseModel):
    station = models.ForeignKey(ChargingStation, on_delete=models.CASCADE, related_name='configs')
    fast_pile_num = models.IntegerField(default=2)
    slow_pile_num = models.IntegerField(default=3)
    waiting_area_size = models.IntegerField(default=10)
    charging_queue_len = models.IntegerField(default=3)
    fault_strategy = models.CharField(max_length=20, default=FaultStrategy.PRIORITY)
    dispatch_mode = models.CharField(max_length=20, default=DispatchMode.NORMAL)
    service_price = models.DecimalField(max_digits=8, decimal_places=2, default=0.8)
    is_active = models.BooleanField(default=True)
    effective_from = models.DateTimeField(auto_now_add=True)
    fast_queue_seq = models.IntegerField(default=0)
    slow_queue_seq = models.IntegerField(default=0)
    waiting_dispatch_paused = models.BooleanField(default=False)

    class Meta:
        db_table = 'station_system_config'


class ChargingPile(BaseModel):
    station = models.ForeignKey(ChargingStation, on_delete=models.CASCADE, related_name='piles')
    pile_no = models.CharField(max_length=32)
    pile_type = models.CharField(max_length=1)
    rated_power = models.DecimalField(max_digits=8, decimal_places=2)
    status = models.CharField(max_length=20, default=PileStatus.OFF)
    is_enabled = models.BooleanField(default=False)
    current_queue_length = models.IntegerField(default=0)
    total_charge_num = models.IntegerField(default=0)
    total_charge_time = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_charge_capacity = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    last_heartbeat_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'station_charging_pile'
        unique_together = [('station', 'pile_no')]

    @property
    def mode_label(self):
        from apps.common.utils import mode_label
        return mode_label(self.pile_type)

    @classmethod
    def default_power(cls, pile_type: str):
        if pile_type == ChargeMode.FAST:
            return FAST_CHARGE_POWER
        return SLOW_CHARGE_POWER


class SimulationClock(BaseModel):
    """验收模拟时钟（单例行）。"""

    is_active = models.BooleanField(default=False)
    current_time = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'station_simulation_clock'

    @classmethod
    def get_state(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

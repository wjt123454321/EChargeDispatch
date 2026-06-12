from datetime import time
from decimal import Decimal

from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand

from apps.accounts.models import AdminAccount
from apps.billing.models import TariffPeriod, TariffPolicy
from apps.common.enums import ChargeMode, PileStatus
from apps.station.models import ChargingPile, ChargingStation, SystemConfig


class Command(BaseCommand):
    help = '初始化充电站系统数据'

    def handle(self, *args, **options):
        station, _ = ChargingStation.objects.get_or_create(
            station_code='BUPT-01',
            defaults={'station_name': '北京邮电大学充电站', 'status': 'active'},
        )

        SystemConfig.objects.filter(is_active=True).update(is_active=False)
        config = SystemConfig.objects.create(
            station=station,
            fast_pile_num=2,
            slow_pile_num=3,
            waiting_area_size=10,
            charging_queue_len=3,
            fault_strategy='priority',
            dispatch_mode='normal',
            service_price=Decimal('0.8'),
            is_active=True,
        )

        ChargingPile.objects.filter(station=station).delete()
        for i in range(1, config.fast_pile_num + 1):
            ChargingPile.objects.create(
                station=station,
                pile_no=f'F{i}',
                pile_type=ChargeMode.FAST,
                rated_power=Decimal('30'),
                status=PileStatus.AVAILABLE,
                is_enabled=True,
            )
        for i in range(1, config.slow_pile_num + 1):
            ChargingPile.objects.create(
                station=station,
                pile_no=f'T{i}',
                pile_type=ChargeMode.SLOW,
                rated_power=Decimal('10'),
                status=PileStatus.AVAILABLE,
                is_enabled=True,
            )

        AdminAccount.objects.get_or_create(
            admin_code='A077379',
            defaults={
                'user_name': '管理员',
                'password_hash': make_password('123456'),
            },
        )

        TariffPolicy.objects.filter(is_active=True).update(is_active=False)
        policy = TariffPolicy.objects.create(
            policy_name='默认峰平谷策略',
            service_price=Decimal('0.8'),
            is_active=True,
        )
        periods = [
            ('peak', time(10, 0), time(15, 0), Decimal('1.0')),
            ('peak', time(18, 0), time(21, 0), Decimal('1.0')),
            ('flat', time(7, 0), time(10, 0), Decimal('0.7')),
            ('flat', time(15, 0), time(18, 0), Decimal('0.7')),
            ('flat', time(21, 0), time(23, 0), Decimal('0.7')),
            ('valley', time(23, 0), time(23, 59, 59), Decimal('0.4')),
            ('valley', time(0, 0), time(7, 0), Decimal('0.4')),
        ]
        for period_type, start, end, price in periods:
            TariffPeriod.objects.create(
                policy=policy,
                period_type=period_type,
                start_time=start,
                end_time=end,
                unit_price=price,
            )

        self.stdout.write(self.style.SUCCESS('系统初始化完成'))

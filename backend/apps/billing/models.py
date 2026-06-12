from django.db import models

from apps.accounts.models import UserAccount, Vehicle
from apps.charging.models import ChargingRequest, ChargingSession
from apps.common.enums import PayStatus
from apps.station.models import ChargingPile


class TariffPolicy(models.Model):
    policy_name = models.CharField(max_length=64)
    service_price = models.DecimalField(max_digits=8, decimal_places=2, default=0.8)
    is_active = models.BooleanField(default=True)
    effective_from = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'billing_tariff_policy'


class TariffPeriod(models.Model):
    policy = models.ForeignKey(TariffPolicy, on_delete=models.CASCADE, related_name='periods')
    period_type = models.CharField(max_length=16)
    start_time = models.TimeField()
    end_time = models.TimeField()
    unit_price = models.DecimalField(max_digits=8, decimal_places=2)

    class Meta:
        db_table = 'billing_tariff_period'


class ChargeDetail(models.Model):
    detail_no = models.CharField(max_length=32, unique=True)
    session = models.OneToOneField(ChargingSession, on_delete=models.CASCADE, related_name='charge_detail')
    request = models.ForeignKey(ChargingRequest, on_delete=models.CASCADE, related_name='charge_details')
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='charge_details')
    pile = models.ForeignKey(ChargingPile, on_delete=models.CASCADE, related_name='charge_details')
    tariff_policy = models.ForeignKey(TariffPolicy, on_delete=models.SET_NULL, null=True)
    charge_amount = models.DecimalField(max_digits=10, decimal_places=2)
    charge_duration = models.DecimalField(max_digits=10, decimal_places=4)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    charge_fee = models.DecimalField(max_digits=10, decimal_places=2)
    service_fee = models.DecimalField(max_digits=10, decimal_places=2)
    total_fee = models.DecimalField(max_digits=10, decimal_places=2)
    generated_at = models.DateTimeField(auto_now_add=True)
    bill = models.ForeignKey('Bill', null=True, blank=True, on_delete=models.SET_NULL, related_name='details')

    class Meta:
        db_table = 'billing_charge_detail'


class Bill(models.Model):
    bill_no = models.CharField(max_length=32, unique=True)
    user = models.ForeignKey(UserAccount, on_delete=models.CASCADE, related_name='bills')
    bill_date = models.DateField()
    total_charge_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_charge_duration = models.DecimalField(max_digits=10, decimal_places=4, default=0)
    total_charge_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_service_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    pay_status = models.CharField(max_length=16, default=PayStatus.UNPAID)
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'billing_bill'

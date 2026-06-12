from django.db import models

from apps.accounts.models import AdminAccount
from apps.charging.models import ChargingRequest
from apps.station.models import ChargingPile


class FaultRecord(models.Model):
    pile = models.ForeignKey(ChargingPile, on_delete=models.CASCADE, related_name='fault_records')
    fault_type = models.CharField(max_length=32, default='hardware')
    fault_status = models.CharField(max_length=16, default='open')
    occurred_at = models.DateTimeField(auto_now_add=True)
    recovered_at = models.DateTimeField(null=True, blank=True)
    description = models.TextField(blank=True, default='')

    class Meta:
        db_table = 'operations_fault_record'


class RescheduleRecord(models.Model):
    fault_record = models.ForeignKey(FaultRecord, on_delete=models.CASCADE, related_name='reschedules')
    request = models.ForeignKey(ChargingRequest, on_delete=models.CASCADE, related_name='reschedules')
    source_pile = models.ForeignKey(
        ChargingPile, null=True, blank=True, on_delete=models.SET_NULL, related_name='reschedule_sources'
    )
    target_pile = models.ForeignKey(
        ChargingPile, null=True, blank=True, on_delete=models.SET_NULL, related_name='reschedule_targets'
    )
    strategy_type = models.CharField(max_length=32)
    result_status = models.CharField(max_length=32, default='success')
    handled_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'operations_reschedule_record'


class OperationLog(models.Model):
    admin = models.ForeignKey(AdminAccount, on_delete=models.SET_NULL, null=True, related_name='operation_logs')
    operation_type = models.CharField(max_length=32)
    target_type = models.CharField(max_length=32)
    target_id = models.CharField(max_length=64)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'operations_operation_log'


class ReportSnapshot(models.Model):
    period_type = models.CharField(max_length=16)
    report_date = models.DateField()
    pile = models.ForeignKey(ChargingPile, on_delete=models.CASCADE, related_name='report_snapshots')
    total_charge_num = models.IntegerField(default=0)
    total_charge_time = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_charge_capacity = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_charge_fee = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_service_fee = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_fee = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    generated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'operations_report_snapshot'

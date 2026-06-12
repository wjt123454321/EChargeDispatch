from django.db import models

from apps.accounts.models import UserAccount, Vehicle
from apps.common.enums import RequestStatus
from apps.station.models import ChargingPile


class ChargingRequest(models.Model):
    request_no = models.CharField(max_length=32, unique=True)
    user = models.ForeignKey(UserAccount, on_delete=models.CASCADE, related_name='charging_requests')
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='charging_requests')
    request_mode = models.CharField(max_length=1)
    request_amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=32, default=RequestStatus.QUEUING)
    request_time = models.DateTimeField(auto_now_add=True)
    queued_at = models.DateTimeField(null=True, blank=True)
    charge_started_at = models.DateTimeField(null=True, blank=True)
    charge_ended_at = models.DateTimeField(null=True, blank=True)
    current_pile = models.ForeignKey(
        ChargingPile, null=True, blank=True, on_delete=models.SET_NULL, related_name='active_requests'
    )
    queue_num = models.CharField(max_length=16, blank=True, default='')
    remark = models.TextField(blank=True, default='')

    class Meta:
        db_table = 'charging_request'


class QueueTicket(models.Model):
    request = models.ForeignKey(ChargingRequest, on_delete=models.CASCADE, related_name='queue_tickets')
    queue_num = models.CharField(max_length=16)
    queue_type = models.CharField(max_length=20)
    pile = models.ForeignKey(ChargingPile, null=True, blank=True, on_delete=models.SET_NULL, related_name='queue_tickets')
    queue_position = models.IntegerField(default=0)
    entered_queue_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'charging_queue_ticket'
        ordering = ['queue_position', 'entered_queue_at']


class ChargingSession(models.Model):
    session_no = models.CharField(max_length=32, unique=True)
    request = models.OneToOneField(ChargingRequest, on_delete=models.CASCADE, related_name='session')
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='charging_sessions')
    pile = models.ForeignKey(ChargingPile, on_delete=models.CASCADE, related_name='charging_sessions')
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, blank=True)
    charged_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    charged_duration = models.DecimalField(max_digits=10, decimal_places=4, default=0)
    session_status = models.CharField(max_length=20, default='active')
    stop_reason = models.CharField(max_length=32, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'charging_session'


class DispatchRecord(models.Model):
    request = models.ForeignKey(ChargingRequest, on_delete=models.CASCADE, related_name='dispatch_records')
    source_type = models.CharField(max_length=32)
    target_pile = models.ForeignKey(ChargingPile, null=True, blank=True, on_delete=models.SET_NULL)
    dispatch_strategy = models.CharField(max_length=32, blank=True, default='')
    before_status = models.CharField(max_length=32)
    after_status = models.CharField(max_length=32)
    dispatched_at = models.DateTimeField(auto_now_add=True)
    operator_type = models.CharField(max_length=16, default='system')

    class Meta:
        db_table = 'charging_dispatch_record'

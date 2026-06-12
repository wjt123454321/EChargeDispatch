from django.db import models

from apps.common.enums import VehicleStatus
from apps.common.models import BaseModel


class UserAccount(BaseModel):
    user_name = models.CharField(max_length=64)
    password_hash = models.CharField(max_length=128)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'accounts_user'


class AdminAccount(BaseModel):
    admin_code = models.CharField(max_length=32, unique=True)
    user_name = models.CharField(max_length=64)
    password_hash = models.CharField(max_length=128)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'accounts_admin'


class Vehicle(BaseModel):
    user = models.ForeignKey(UserAccount, on_delete=models.CASCADE, related_name='vehicles')
    plate_no = models.CharField(max_length=32, unique=True)
    battery_capacity = models.DecimalField(max_digits=10, decimal_places=2, default=60)
    current_battery_level = models.DecimalField(max_digits=10, decimal_places=2, default=60)
    is_charging = models.BooleanField(default=False)
    vehicle_status = models.CharField(max_length=20, default=VehicleStatus.IDLE)

    class Meta:
        db_table = 'accounts_vehicle'

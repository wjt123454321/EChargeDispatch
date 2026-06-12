from django.contrib.auth.hashers import check_password, make_password
from django.db import transaction

from apps.common.auth import create_token
from apps.common.enums import ErrorCode, TokenRole, VehicleStatus
from apps.common.exceptions import AppException

from .models import AdminAccount, UserAccount, Vehicle


class AuthService:
    @staticmethod
    def register(car_id: str, user_name: str, car_capacity, password: str):
        if not car_id or not password:
            raise AppException(ErrorCode.VALIDATION_ERROR, '参数校验失败')
        if Vehicle.objects.filter(plate_no=car_id).exists():
            raise AppException(ErrorCode.USER_EXISTS, '用户已注册')
        with transaction.atomic():
            user = UserAccount.objects.create(
                user_name=user_name or car_id,
                password_hash=make_password(password),
            )
            vehicle = Vehicle.objects.create(
                user=user,
                plate_no=car_id,
                battery_capacity=car_capacity or 60,
                current_battery_level=car_capacity or 60,
            )
        token = create_token(user.id, TokenRole.USER, {'vehicle_id': vehicle.id, 'car_id': car_id})
        return {
            'access_token': token,
            'expires_in': 7200,
            'car_id': car_id,
            'user_name': user.user_name,
        }

    @staticmethod
    def login(car_id: str, password: str):
        if not car_id or not password:
            raise AppException(ErrorCode.VALIDATION_ERROR, '参数校验失败')

        admin = AdminAccount.objects.filter(admin_code=car_id, is_active=True).first()
        if admin:
            if not check_password(password, admin.password_hash):
                raise AppException(ErrorCode.PASSWORD_ERROR, '密码错误')
            token = create_token(admin.id, TokenRole.ADMIN, {'admin_code': admin.admin_code})
            return {
                'access_token': token,
                'expires_in': 7200,
                'role': TokenRole.ADMIN,
                'admin_code': admin.admin_code,
            }

        vehicle = Vehicle.objects.select_related('user').filter(plate_no=car_id).first()
        if not vehicle:
            raise AppException(ErrorCode.USER_NOT_FOUND, '用户不存在')
        if not check_password(password, vehicle.user.password_hash):
            raise AppException(ErrorCode.PASSWORD_ERROR, '密码错误')
        token = create_token(
            vehicle.user.id,
            TokenRole.USER,
            {'vehicle_id': vehicle.id, 'car_id': vehicle.plate_no},
        )
        return {
            'access_token': token,
            'expires_in': 7200,
            'role': TokenRole.USER,
            'car_id': vehicle.plate_no,
        }


class VehicleService:
    @staticmethod
    def sync_vehicle_status(vehicle: Vehicle, status: str, is_charging: bool = False):
        vehicle.vehicle_status = status
        vehicle.is_charging = is_charging
        vehicle.save(update_fields=['vehicle_status', 'is_charging', 'updated_at'])

    @staticmethod
    def reset_to_idle(vehicle: Vehicle):
        VehicleService.sync_vehicle_status(vehicle, VehicleStatus.IDLE, False)

    @staticmethod
    def get_vehicle_for_user(user_id, vehicle_id=None):
        if vehicle_id:
            return Vehicle.objects.filter(id=vehicle_id, user_id=user_id).first()
        return Vehicle.objects.filter(user_id=user_id).first()

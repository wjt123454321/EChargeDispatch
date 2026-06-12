class ErrorCode:
    SUCCESS = 0
    VALIDATION_ERROR = 1001
    AUTH_ERROR = 1002
    PERMISSION_ERROR = 1003
    USER_NOT_FOUND = 2001
    PASSWORD_ERROR = 2002
    USER_EXISTS = 2003
    ACTIVE_REQUEST_EXISTS = 3001
    REQUEST_NOT_FOUND = 3002
    INVALID_STATUS = 3003
    WAITING_AREA_FULL = 3005
    PILE_NOT_FOUND = 4001
    PILE_STATUS_ERROR = 4002
    PILE_NO_SLOT = 4003
    BILL_NOT_FOUND = 6001


class ChargeMode:
    FAST = 'F'
    SLOW = 'T'
    LABELS = {FAST: '快充', SLOW: '慢充'}


class RequestStatus:
    QUEUING = 'queuing'
    DISPATCHED = 'dispatched'
    CHARGING = 'charging'
    PENDING_RESCHEDULE = 'pending_reschedule'
    COMPLETED = 'completed'
    CANCELLED = 'cancelled'

    ACTIVE = {QUEUING, DISPATCHED, CHARGING, PENDING_RESCHEDULE}


class VehicleStatus:
    IDLE = 'idle'
    WAITING = 'waiting'
    QUEUING = 'queuing'
    CHARGING = 'charging'


class PileStatus:
    OFF = 'off'
    STANDBY = 'standby'
    AVAILABLE = 'available'
    CHARGING = 'charging'
    FAULT = 'fault'


class QueueType:
    WAITING_AREA = 'waiting_area'
    PILE_QUEUE = 'pile_queue'


class FaultStrategy:
    PRIORITY = 'priority'
    TIME_ORDER = 'time_order'


class DispatchMode:
    NORMAL = 'normal'
    SINGLE_MIN_TOTAL = 'single_min_total'
    BATCH_MIN_TOTAL = 'batch_min_total'


class PayStatus:
    UNPAID = 'unpaid'
    PAID = 'paid'


class SessionStatus:
    ACTIVE = 'active'
    COMPLETED = 'completed'
    CANCELLED = 'cancelled'
    FAULT_INTERRUPTED = 'fault_interrupted'


class TokenRole:
    USER = 'user'
    ADMIN = 'admin'


FAST_CHARGE_POWER = 30
SLOW_CHARGE_POWER = 10
SERVICE_FEE_RATE = 0.8

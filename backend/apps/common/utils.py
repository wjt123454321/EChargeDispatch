import uuid
from datetime import datetime, time, timedelta
from decimal import Decimal

from django.utils import timezone

from .enums import FAST_CHARGE_POWER, SLOW_CHARGE_POWER, ChargeMode


def generate_no(prefix: str) -> str:
    return f'{prefix}{uuid.uuid4().hex[:12].upper()}'


def get_charge_power(mode: str) -> Decimal:
    if mode == ChargeMode.FAST:
        return Decimal(str(FAST_CHARGE_POWER))
    return Decimal(str(SLOW_CHARGE_POWER))


def estimate_charge_hours(amount: Decimal, mode: str) -> Decimal:
    power = get_charge_power(mode)
    if power <= 0:
        return Decimal('0')
    return (amount / power).quantize(Decimal('0.0001'))


def mode_label(mode: str) -> str:
    from .enums import ChargeMode
    return ChargeMode.LABELS.get(mode, mode)


TARIFF_PERIODS = [
    ('peak', time(10, 0), time(15, 0), Decimal('1.0')),
    ('peak', time(18, 0), time(21, 0), Decimal('1.0')),
    ('flat', time(7, 0), time(10, 0), Decimal('0.7')),
    ('flat', time(15, 0), time(18, 0), Decimal('0.7')),
    ('flat', time(21, 0), time(23, 0), Decimal('0.7')),
    ('valley', time(23, 0), time(23, 59, 59, 999999), Decimal('0.4')),
    ('valley', time(0, 0), time(7, 0), Decimal('0.4')),
]


def _period_end_today(period_end: time, ref_date):
    dt = datetime.combine(ref_date, period_end)
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt)
    return dt


def _period_start_today(period_start: time, ref_date):
    dt = datetime.combine(ref_date, period_start)
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt)
    return dt


def get_unit_price_at(moment):
    local_moment = timezone.localtime(moment)
    t = local_moment.time()
    for period_type, start, end, price in TARIFF_PERIODS:
        if start <= end:
            if start <= t < end:
                return price, period_type
        else:
            if t >= start or t < end:
                return price, period_type
    return Decimal('0.7'), 'flat'


def calculate_cross_period_fee(start_time, end_time, total_kwh: Decimal):
    if total_kwh <= 0 or not start_time or not end_time or end_time <= start_time:
        return Decimal('0'), Decimal('0')

    duration_seconds = (end_time - start_time).total_seconds()
    if duration_seconds <= 0:
        return Decimal('0'), Decimal('0')

    total_seconds = Decimal(str(duration_seconds))
    charge_fee = Decimal('0')
    cursor = start_time
    remaining_kwh = total_kwh

    while cursor < end_time and remaining_kwh > 0:
        unit_price, _ = get_unit_price_at(cursor)
        next_boundary = _next_tariff_boundary(cursor)
        if next_boundary > end_time:
            next_boundary = end_time
        slice_seconds = Decimal(str((next_boundary - cursor).total_seconds()))
        slice_kwh = (remaining_kwh * slice_seconds / total_seconds).quantize(Decimal('0.0001'))
        if next_boundary >= end_time:
            slice_kwh = remaining_kwh
        charge_fee += slice_kwh * unit_price
        remaining_kwh -= slice_kwh
        cursor = next_boundary

    return charge_fee.quantize(Decimal('0.01')), total_kwh


def _next_tariff_boundary(moment):
    local_moment = timezone.localtime(moment)
    today = local_moment.date()
    boundaries = []
    for _, start, end, _ in TARIFF_PERIODS:
        boundaries.append(_period_start_today(start, today))
        boundaries.append(_period_end_today(end, today))
        boundaries.append(_period_start_today(start, today + timedelta(days=1)))
    future = [b for b in boundaries if b > moment]
    if not future:
        return moment + timedelta(hours=1)
    return min(future)


def compute_charged_amount(session, now=None):
    if now is None:
        from apps.common.sim_clock import system_now
        now = system_now()
    if not session.start_time:
        return Decimal('0')
    end_point = session.end_time or now
    if end_point <= session.start_time:
        return Decimal('0')
    elapsed_hours = Decimal(str((end_point - session.start_time).total_seconds())) / Decimal('3600')
    power = session.pile.rated_power
    charged = (power * elapsed_hours).quantize(Decimal('0.0001'))
    request_amount = session.request.request_amount
    return min(charged, request_amount)

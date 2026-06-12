"""
验收用虚拟时钟。

比例尺 1:10：真实 1 分钟 = 模拟 10 分钟。
时钟状态存库，管理命令与 HTTP 服务可共享同一模拟时间。
"""

from datetime import datetime

from django.utils import timezone

# 验收用例基准日期（6:00 处于谷时 0.4 元/度）
ACCEPTANCE_BASE_DATE = (2026, 6, 12)
TIME_SCALE = 10


def _get_model():
    from apps.station.models import SimulationClock
    return SimulationClock


def is_active():
    return _get_model().get_state().is_active


def system_now():
    """业务统一取时：模拟时钟开启时返回模拟时间，否则返回真实时间。"""
    state = _get_model().get_state()
    if state.is_active and state.current_time:
        return state.current_time
    return timezone.now()


def enable(moment: datetime):
    """开启模拟时钟并设置起始时刻。"""
    if timezone.is_naive(moment):
        moment = timezone.make_aware(moment)
    state = _get_model().get_state()
    state.is_active = True
    state.current_time = moment
    state.save(update_fields=['is_active', 'current_time', 'updated_at'])


def set_now(moment: datetime):
    """跳转到指定模拟时刻。"""
    if timezone.is_naive(moment):
        moment = timezone.make_aware(moment)
    state = _get_model().get_state()
    if not state.is_active:
        return
    state.current_time = moment
    state.save(update_fields=['current_time', 'updated_at'])


def disable():
    """关闭模拟时钟，恢复真实时间。"""
    state = _get_model().get_state()
    state.is_active = False
    state.save(update_fields=['is_active', 'updated_at'])


def make_case_time(hour: int, minute: int) -> datetime:
    """将用例时刻（如 6:05）转为带时区的 datetime。"""
    y, m, d = ACCEPTANCE_BASE_DATE
    dt = datetime(y, m, d, hour, minute, 0)
    return timezone.make_aware(dt)

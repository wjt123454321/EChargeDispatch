/** 充电请求状态 */
export const REQUEST_STATUS = {
  queuing: { label: '等候区排队', color: 'info' },
  dispatched: { label: '已调度', color: 'warning' },
  charging: { label: '充电中', color: 'success' },
  pending_reschedule: { label: '等待重调度', color: 'warning' },
  completed: { label: '已完成', color: 'muted' },
  cancelled: { label: '已取消', color: 'muted' },
}

/** 充电桩状态 */
export const PILE_STATUS = {
  off: { label: '关闭', color: 'muted' },
  standby: { label: '待机', color: 'info' },
  available: { label: '可用', color: 'success' },
  charging: { label: '充电中', color: 'accent' },
  fault: { label: '故障', color: 'danger' },
}

/** 充电模式 */
export const CHARGE_MODE = {
  F: { label: '快充', power: 30, desc: '30 度/小时' },
  T: { label: '慢充', power: 10, desc: '10 度/小时' },
}

/** 支付状态 */
export const PAY_STATUS = {
  unpaid: { label: '待支付', color: 'warning' },
  paid: { label: '已支付', color: 'success' },
}

/** 故障调度策略 */
export const FAULT_STRATEGY = {
  priority: '优先级调度',
  time_order: '时间顺序调度',
}

/** 调度模式 */
export const DISPATCH_MODE = {
  normal: '普通调度',
  single_min_total: '单次总时长最短',
  batch_min_total: '批量总时长最短',
}

/** 分时电价说明 */
export const PRICE_PERIODS = [
  { name: '峰时', price: 1.0, time: '10:00–15:00，18:00–21:00' },
  { name: '平时', price: 0.7, time: '7:00–10:00，15:00–18:00，21:00–23:00' },
  { name: '谷时', price: 0.4, time: '23:00–次日 7:00' },
]

export const SERVICE_PRICE = 0.8

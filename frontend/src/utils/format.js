/** 格式化金额 */
export function formatMoney(value) {
  if (value == null) return '—'
  return `¥${Number(value).toFixed(2)}`
}

/** 格式化电量 */
export function formatKwh(value) {
  if (value == null) return '—'
  return `${Number(value).toFixed(1)} 度`
}

/** 格式化时长（小时） */
export function formatDuration(hours) {
  if (hours == null) return '—'
  const h = Number(hours)
  if (h < 1) return `${Math.round(h * 60)} 分钟`
  return `${h.toFixed(2)} 小时`
}

/** 格式化等待秒数为可读文本 */
export function formatWaitTime(seconds) {
  if (seconds == null) return '—'
  const s = Number(seconds)
  if (s < 60) return `${s} 秒`
  if (s < 3600) return `${Math.floor(s / 60)} 分 ${s % 60} 秒`
  const h = Math.floor(s / 3600)
  const m = Math.floor((s % 3600) / 60)
  return `${h} 小时 ${m} 分`
}

/** 格式化 ISO 时间为本地显示 */
export function formatDateTime(iso) {
  if (!iso) return '—'
  const d = new Date(iso)
  return d.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

/** 格式化日期 */
export function formatDate(iso) {
  if (!iso) return '—'
  const d = new Date(iso)
  return d.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  })
}

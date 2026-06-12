import { request } from './request'

// —— 系统配置 ——
export function getSystemConfig() {
  return request('/admin/system-config')
}

export function updateSystemConfig(data) {
  return request('/admin/system-config', { method: 'PUT', body: data })
}

// —— 充电桩 ——
export function getPileStatus() {
  return request('/pile/status')
}

export function getPileQueue(pileId) {
  return request(`/queue/pile/${pileId}`)
}

export function powerOnPile(pileId) {
  return request(`/pile/${pileId}/poweron`, { method: 'POST' })
}

export function startPile(pileId) {
  return request(`/pile/${pileId}/start`, { method: 'POST' })
}

export function powerOffPile(pileId) {
  return request(`/pile/${pileId}/poweroff`, { method: 'POST' })
}

// —— 故障 ——
export function reportFault(pileId) {
  return request('/admin/fault/report', { method: 'POST', body: { pile_id: pileId } })
}

export function recoverFault(pileId) {
  return request('/admin/fault/recover', { method: 'POST', body: { pile_id: pileId } })
}

export function getFaultList() {
  return request('/admin/fault/list')
}

// —— 报表 ——
export function getReportStats(period, date) {
  return request(`/admin/report/stats?period=${period}&date=${date}`)
}

/** 验收填表快照 */
export function getAcceptanceSnapshot(caseTime) {
  const q = caseTime ? `?case_time=${caseTime}` : ''
  return request(`/admin/acceptance/snapshot${q}`)
}

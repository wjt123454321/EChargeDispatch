import { request } from './request'

export function submitRequest(data) {
  return request('/charging/request', { method: 'POST', body: data })
}

export function updateAmount(amount) {
  return request('/charging/amount', { method: 'PUT', body: { amount } })
}

export function updateMode(mode) {
  return request('/charging/mode', { method: 'PUT', body: { mode } })
}

export function getQueueStatus() {
  return request('/charging/queue-status')
}

export function startCharging(pileId) {
  return request('/charging/start', { method: 'POST', body: { pile_id: pileId } })
}

export function getChargingStatus() {
  return request('/charging/status')
}

export function endCharging() {
  return request('/charging/end', { method: 'POST' })
}

export function cancelCharging() {
  return request('/charging/cancel', { method: 'DELETE' })
}

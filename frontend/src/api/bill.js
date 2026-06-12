import { request } from './request'

export function getBillList() {
  return request('/bill/list')
}

export function getBillDetail(billId) {
  return request(`/bill/detail/${billId}`)
}

export function payBill(billId) {
  return request(`/bill/pay/${billId}`, { method: 'POST' })
}

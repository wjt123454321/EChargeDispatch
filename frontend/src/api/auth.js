import { request } from './request'

/** 用户注册 */
export function register(data) {
  return request('/auth/register', { method: 'POST', body: data })
}

/** 用户 / 管理员登录 */
export function login(data) {
  return request('/auth/login', { method: 'POST', body: data })
}

/**
 * 统一 HTTP 请求封装
 * 所有接口 HTTP 状态码均为 200，业务成败由 code 字段区分
 */

const BASE_URL = '/api'

/** 从 localStorage 读取 Token */
function getToken() {
  return localStorage.getItem('access_token') || ''
}

/**
 * 发起 API 请求
 * @param {string} path - 接口路径（不含 /api 前缀）
 * @param {RequestInit & { body?: object }} options
 */
export async function request(path, options = {}) {
  const { body, headers: customHeaders, ...rest } = options

  const headers = {
    'Content-Type': 'application/json',
    ...customHeaders,
  }

  const token = getToken()
  if (token) {
    headers.Authorization = `Bearer ${token}`
  }

  const res = await fetch(`${BASE_URL}${path}`, {
    ...rest,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  })

  let json
  try {
    json = await res.json()
  } catch {
    throw new Error('服务器响应异常')
  }

  if (json.code !== 0) {
    const err = new Error(json.message || '请求失败')
    err.code = json.code
    throw err
  }

  return json.data
}

export function setToken(token) {
  if (token) {
    localStorage.setItem('access_token', token)
  } else {
    localStorage.removeItem('access_token')
  }
}

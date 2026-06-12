import { ref, computed } from 'vue'
import { setToken } from '@/api/request'

const STORAGE_KEY = 'auth_info'

/** 从 localStorage 恢复登录态 */
function loadAuth() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

const authInfo = ref(loadAuth())

export function useAuth() {
  const isLoggedIn = computed(() => !!authInfo.value)
  const role = computed(() => authInfo.value?.role || 'user')
  const isAdmin = computed(() => role.value === 'admin')
  const displayName = computed(() => {
    if (!authInfo.value) return ''
    return authInfo.value.user_name || authInfo.value.car_id || authInfo.value.admin_code || ''
  })

  /** 保存登录信息 */
  function saveAuth(data) {
    const info = {
      role: data.role || 'user',
      car_id: data.car_id,
      user_name: data.user_name,
      admin_code: data.admin_code,
      expires_in: data.expires_in,
    }
    setToken(data.access_token)
    localStorage.setItem(STORAGE_KEY, JSON.stringify(info))
    authInfo.value = info
  }

  /** 退出登录 */
  function logout() {
    setToken(null)
    localStorage.removeItem(STORAGE_KEY)
    authInfo.value = null
  }

  return { authInfo, isLoggedIn, role, isAdmin, displayName, saveAuth, logout }
}

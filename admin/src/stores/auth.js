import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { fetchMe, login as loginApi } from '@/api/auth'
import { apiErrorMessage } from '@/utils/error'

function readStoredUser() {
  try {
    const raw = localStorage.getItem('ca_admin_user')
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('ca_admin_token') || '')
  const user = ref(readStoredUser())

  const isLoggedIn = computed(() => Boolean(token.value))
  const displayName = computed(() => user.value?.name || user.value?.username || '管理员')

  function persist(nextToken, nextUser) {
    token.value = nextToken
    user.value = nextUser
    if (nextToken) localStorage.setItem('ca_admin_token', nextToken)
    else localStorage.removeItem('ca_admin_token')
    if (nextUser) localStorage.setItem('ca_admin_user', JSON.stringify(nextUser))
    else localStorage.removeItem('ca_admin_user')
  }

  async function login(username, password) {
    const { data } = await loginApi({ username, password })
    const role = data.role || data.user?.role
    if (role !== 'admin') {
      const err = new Error('此账号无权进入管理后台，请使用管理员账号')
      err.code = 'not_admin'
      throw err
    }
    const access = data.access_token || data.token
    if (!access) {
      throw new Error('登录响应缺少 access_token')
    }
    persist(access, data.user || { username, role })
    return data
  }

  async function hydrate() {
    if (!token.value) return false
    try {
      const { data } = await fetchMe()
      const profile = data.user || data
      const role = profile.role || data.role
      if (role !== 'admin') {
        logout()
        return false
      }
      persist(token.value, profile)
      return true
    } catch (err) {
      if (err?.response?.status === 401) logout()
      return Boolean(token.value)
    }
  }

  function logout() {
    persist('', null)
  }

  return { token, user, isLoggedIn, displayName, login, hydrate, logout, apiErrorMessage }
})

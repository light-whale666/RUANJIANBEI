import axios from 'axios'
import { ElMessage } from 'element-plus'
import { apiErrorMessage } from '@/utils/error'
import router from '@/router'

const rawBase = (import.meta.env.VITE_API_BASE || '').replace(/\/$/, '')

export const http = axios.create({
  baseURL: rawBase ? `${rawBase}/api/v1` : '/api/v1',
  timeout: 30000,
})

http.interceptors.request.use((config) => {
  const token = localStorage.getItem('ca_admin_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

http.interceptors.response.use(
  (res) => res,
  (err) => {
    const status = err?.response?.status
    const silent = err?.config?.silent
    if (status === 401 && !err?.config?.skipAuthRedirect) {
      localStorage.removeItem('ca_admin_token')
      localStorage.removeItem('ca_admin_user')
      if (router.currentRoute.value.path !== '/login') {
        router.replace({ path: '/login', query: { redirect: router.currentRoute.value.fullPath } })
      }
    }
    if (!silent && status !== 401) {
      ElMessage.error(apiErrorMessage(err))
    }
    return Promise.reject(err)
  },
)

export default http

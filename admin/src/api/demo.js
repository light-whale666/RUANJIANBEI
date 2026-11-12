import http from './http'

export function resetDemo() {
  return http.post('/admin/demo/reset', { confirm: true }, { timeout: 60000 })
}

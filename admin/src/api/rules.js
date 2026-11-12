import http from './http'

export function getRules() {
  return http.get('/admin/rules')
}

export function putRules(payload) {
  return http.put('/admin/rules', payload)
}

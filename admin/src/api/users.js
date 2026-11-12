import http from './http'

export function listUsers(params, config = {}) {
  return http.get('/admin/users', { params, ...config })
}

export function createUser(payload) {
  return http.post('/admin/users', payload)
}

export function updateUser(id, payload) {
  return http.patch(`/admin/users/${id}`, payload)
}

export function importUsers(file) {
  const data = new FormData()
  data.append('file', file)
  return http.post('/admin/users/import', data, {
    timeout: 120000,
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export function fetchStats() {
  return http.get('/admin/stats', { silent: true })
}

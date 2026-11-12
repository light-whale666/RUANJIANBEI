import http from './http'

export function login(payload) {
  return http.post('/auth/login', payload, { skipAuthRedirect: true, silent: true })
}

export function fetchMe() {
  return http.get('/me', { silent: true, skipAuthRedirect: true })
}

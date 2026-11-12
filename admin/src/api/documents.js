import http from './http'

export function listDocuments(params, config = {}) {
  return http.get('/admin/documents', { params, ...config })
}

export function getDocument(id) {
  return http.get(`/admin/documents/${id}`)
}

export function updateDocument(id, payload) {
  return http.patch(`/admin/documents/${id}`, payload)
}

export function uploadDocument(fields, file, onUploadProgress) {
  const data = new FormData()
  data.append('file', file)
  data.append('filename', fields.filename)
  data.append('semester', fields.semester)
  data.append('roles', JSON.stringify(fields.roles || []))
  data.append('scope', JSON.stringify(fields.scope || { type: 'all' }))
  data.append('is_priority', fields.is_priority ? 'true' : 'false')
  data.append('counselor_only', fields.counselor_only ? 'true' : 'false')
  return http.post('/admin/documents', data, {
    timeout: 120000,
    onUploadProgress,
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export function listChunks(documentId) {
  return http.get(`/admin/documents/${documentId}/chunks`)
}

export function updateChunk(documentId, chunkId, payload) {
  return http.patch(`/admin/documents/${documentId}/chunks/${chunkId}`, payload)
}

export function saveChunks(documentId, chunks) {
  return http.put(`/admin/documents/${documentId}/chunks`, { chunks })
}

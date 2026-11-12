export function apiErrorMessage(err, fallback = '请求失败') {
  if (!err) return fallback
  if (!err.response) {
    if (err.code === 'ERR_NETWORK' || err.message === 'Network Error') {
      return '无法连接服务器，请确认网络与 API 已就绪'
    }
    if (err.code === 'ECONNABORTED') return '请求超时，请稍后重试'
    return err.message || fallback
  }
  const data = err.response.data
  if (!data) {
    if (err.response.status === 401) return '登录已过期，请重新登录'
    if (err.response.status === 403) return '没有权限执行此操作'
    if (err.response.status === 404) return '接口不存在（后端可能尚未部署该路径）'
    return fallback
  }
  if (typeof data.message === 'string' && data.message) return data.message
  if (typeof data.detail === 'string' && data.detail) return data.detail
  if (Array.isArray(data.detail)) {
    return data.detail.map((x) => x.msg || x.message || JSON.stringify(x)).join('；')
  }
  return fallback
}

export function unwrapList(data) {
  if (Array.isArray(data)) {
    return { items: data, total: data.length, page: 1, page_size: data.length }
  }
  const items = data?.items ?? data?.data ?? data?.results ?? []
  return {
    items,
    total: Number(data?.total ?? data?.count ?? items.length) || 0,
    page: Number(data?.page ?? 1) || 1,
    page_size: Number(data?.page_size ?? data?.pageSize ?? items.length) || items.length,
  }
}

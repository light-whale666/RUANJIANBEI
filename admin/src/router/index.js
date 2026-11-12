import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes = [
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/Login.vue'),
    meta: { public: true, title: '登录' },
  },
  {
    path: '/',
    component: () => import('@/layouts/AdminLayout.vue'),
    redirect: '/overview',
    children: [
      { path: 'overview', name: 'overview', component: () => import('@/views/Overview.vue'), meta: { title: '概览' } },
      { path: 'users', name: 'users', component: () => import('@/views/Users.vue'), meta: { title: '名单与班级' } },
      { path: 'documents', name: 'documents', component: () => import('@/views/Documents.vue'), meta: { title: '规章库' } },
      {
        path: 'documents/:id/chunks',
        name: 'document-chunks',
        component: () => import('@/views/DocumentChunks.vue'),
        meta: { title: '校对切块' },
      },
      { path: 'rules', name: 'rules', component: () => import('@/views/Rules.vue'), meta: { title: '审批规则' } },
      { path: 'demo', name: 'demo', component: () => import('@/views/DemoReset.vue'), meta: { title: '演示数据' } },
    ],
  },
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

const router = createRouter({
  history: createWebHistory('/admin/'),
  routes,
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  document.title = to.meta.title
    ? `${to.meta.title} · 管理后台`
    : '校园办事与入学助手 · 管理后台'

  if (to.meta.public) {
    if (auth.isLoggedIn && to.name === 'login') return { path: '/' }
    return true
  }
  if (!auth.isLoggedIn) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }
  return true
})

export default router

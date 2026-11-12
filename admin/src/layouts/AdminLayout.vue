<template>
  <div class="shell">
    <aside class="sider">
      <div class="brand">
        <div class="logo" aria-hidden="true">
          <svg viewBox="0 0 32 32" width="28" height="28">
            <rect width="32" height="32" rx="8" fill="#2a8f88" />
            <path d="M8 12.5L16 8l8 4.5V22a1 1 0 0 1-1 1H9a1 1 0 0 1-1-1V12.5Z" stroke="#F4FBF9" stroke-width="1.6" stroke-linejoin="round" fill="none"/>
            <path d="M16 8v15" stroke="#F4FBF9" stroke-width="1.6"/>
          </svg>
        </div>
        <div>
          <div class="brand-name">智慧校园</div>
          <div class="brand-sub">管理后台</div>
        </div>
      </div>
      <el-menu :default-active="active" router class="menu" background-color="transparent" text-color="#c9d6d4" active-text-color="#ffffff">
        <el-menu-item index="/overview">
          <el-icon><HomeFilled /></el-icon>
          <span>概览</span>
        </el-menu-item>
        <el-menu-item index="/users">
          <el-icon><User /></el-icon>
          <span>名单与班级</span>
        </el-menu-item>
        <el-menu-item index="/documents">
          <el-icon><Collection /></el-icon>
          <span>规章库</span>
        </el-menu-item>
        <el-menu-item index="/rules">
          <el-icon><SetUp /></el-icon>
          <span>审批规则</span>
        </el-menu-item>
        <el-menu-item index="/demo">
          <el-icon><RefreshRight /></el-icon>
          <span>演示数据</span>
        </el-menu-item>
      </el-menu>
      <div class="sider-foot">初版 v1 · 仅管理员</div>
    </aside>
    <div class="main">
      <header class="topbar">
        <div class="crumb">{{ currentTitle }}</div>
        <div class="top-right">
          <span class="who">{{ auth.displayName }}</span>
          <el-button text @click="onLogout">退出</el-button>
        </div>
      </header>
      <main class="content">
        <router-view />
      </main>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { HomeFilled, User, Collection, SetUp, RefreshRight } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const active = computed(() => {
  if (route.path.startsWith('/documents')) return '/documents'
  return route.path
})

const currentTitle = computed(() => route.meta.title || '管理后台')

onMounted(() => {
  auth.hydrate()
})

function onLogout() {
  auth.logout()
  router.replace('/login')
}
</script>

<style scoped>
.shell {
  display: flex;
  min-height: 100vh;
  background: var(--ca-bg);
}
.sider {
  width: 220px;
  flex-shrink: 0;
  background: linear-gradient(180deg, var(--ca-sidebar) 0%, var(--ca-sidebar-2) 100%);
  color: #fff;
  display: flex;
  flex-direction: column;
  padding: 18px 0 12px;
}
.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 4px 20px 20px;
}
.brand-name {
  font-weight: 650;
  font-size: 15px;
  letter-spacing: 0.04em;
}
.brand-sub {
  font-size: 12px;
  color: #9bb0ad;
  margin-top: 2px;
}
.menu {
  border-right: none;
  flex: 1;
}
.menu :deep(.el-menu-item) {
  margin: 2px 10px;
  border-radius: 8px;
  height: 42px;
}
.menu :deep(.el-menu-item.is-active) {
  background: rgba(42, 143, 136, 0.35) !important;
}
.sider-foot {
  padding: 12px 20px;
  font-size: 12px;
  color: #7e9290;
}
.main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}
.topbar {
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  background: #fff;
  border-bottom: 1px solid var(--ca-line);
}
.crumb {
  font-weight: 600;
  font-size: 15px;
}
.top-right {
  display: flex;
  align-items: center;
  gap: 8px;
}
.who {
  font-size: 13px;
  color: var(--ca-muted);
}
.content {
  padding: 22px 24px 32px;
  flex: 1;
}
</style>

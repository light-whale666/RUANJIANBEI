<template>
  <div class="page">
    <PageHeader title="概览" description="管理员只负责规章、名单、规则和演示数据。日常问答、确认与审批在学生端 / 教师端完成。" />

    <div class="cards">
      <button v-for="item in entries" :key="item.to" class="entry" type="button" @click="router.push(item.to)">
        <div class="entry-title">{{ item.title }}</div>
        <div class="entry-desc">{{ item.desc }}</div>
        <div class="entry-meta">
          <span v-if="counts[item.key] != null">{{ counts[item.key] }}</span>
          <span v-else class="muted">进入</span>
        </div>
      </button>
    </div>

    <div class="panel">
      <h3 class="block-title">初版锁定的六件事</h3>
      <p class="hint">后台要为这些能力备好规章、名单和规则，比赛演示用导入数据即可。</p>
      <ul class="six">
        <li>带出处的知识问答</li>
        <li>请假闭环</li>
        <li>奖助或证明预审</li>
        <li>报到任务</li>
        <li>作业任务</li>
        <li>志愿者招募</li>
      </ul>
    </div>
  </div>
</template>

<script setup>
import { onMounted, reactive } from 'vue'
import { useRouter } from 'vue-router'
import PageHeader from '@/components/PageHeader.vue'
import { fetchStats, listUsers } from '@/api/users'
import { listDocuments } from '@/api/documents'
import { unwrapList } from '@/utils/error'

const router = useRouter()
const counts = reactive({ users: null, documents: null })

const entries = [
  { key: 'users', title: '名单与班级', desc: '导入师生名单，维护班级归属与辅导员。', to: '/users' },
  { key: 'documents', title: '规章库', desc: '入库 PDF / Word / 文本，校对切块与可见范围。', to: '/documents' },
  { key: 'rules', title: '审批规则', desc: '短假阈值、加签条件、材料有效期。', to: '/rules' },
  { key: 'demo', title: '演示数据', desc: '将环境重置为演示初始状态（需二次确认）。', to: '/demo' },
]

onMounted(async () => {
  try {
    const { data } = await fetchStats()
    if (data.user_count != null) counts.users = `${data.user_count} 人`
    if (data.users != null) counts.users = `${data.users} 人`
    if (data.document_count != null) counts.documents = `${data.document_count} 份`
    if (data.documents != null) counts.documents = `${data.documents} 份`
    if (counts.users != null && counts.documents != null) return
  } catch {
    /* 可选接口，忽略 */
  }
  try {
    const { data } = await listUsers({ page: 1, page_size: 1 }, { silent: true })
    const list = unwrapList(data)
    counts.users = `${list.total} 人`
  } catch {
    counts.users = null
  }
  try {
    const { data } = await listDocuments({ page: 1, page_size: 1 }, { silent: true })
    const list = unwrapList(data)
    counts.documents = `${list.total} 份`
  } catch {
    counts.documents = null
  }
})
</script>

<style scoped>
.cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 12px;
}
.entry {
  text-align: left;
  background: #fff;
  border: 1px solid var(--ca-line);
  border-radius: 12px;
  padding: 18px 18px 14px;
  cursor: pointer;
  min-height: 140px;
  display: flex;
  flex-direction: column;
}
.entry:hover { border-color: #9ec7c3; }
.entry-title { font-weight: 650; font-size: 16px; margin-bottom: 8px; }
.entry-desc { color: var(--ca-muted); font-size: 13px; line-height: 1.6; flex: 1; }
.entry-meta { margin-top: 12px; font-size: 13px; color: var(--ca-primary); font-weight: 600; }
.muted { color: var(--ca-muted); font-weight: 400; }
.block-title { margin: 0 0 6px; font-size: 15px; }
.six {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 8px 16px;
  margin: 12px 0 0;
  padding: 0;
  list-style: none;
}
.six li {
  font-size: 13px;
  padding: 8px 10px;
  background: var(--ca-primary-soft);
  border-radius: 8px;
  color: #155851;
}
</style>

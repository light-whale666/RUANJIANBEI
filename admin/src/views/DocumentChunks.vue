<template>
  <div class="page">
    <PageHeader :title="title" :description="subtitle">
      <template #actions>
        <el-button @click="router.push('/documents')">返回列表</el-button>
        <el-button @click="load">刷新</el-button>
        <el-button type="primary" :disabled="!dirtyCount" :loading="saving" @click="saveAll">保存全部改动（{{ dirtyCount }}）</el-button>
      </template>
    </PageHeader>

    <el-alert
      class="tip"
      type="info"
      show-icon
      :closable="false"
      title="初版允许半自动切块后由管理员校对。请核对条款/章节、原文和可见范围，保证引用能定位到原文高亮。"
    />

    <div class="panel" v-loading="loading">
      <el-table v-if="chunks.length" :data="chunks" stripe row-key="id">
        <el-table-column label="章节" min-width="140">
          <template #default="{ row }">
            <el-input v-model="row.section" placeholder="章节" @input="mark(row)" />
          </template>
        </el-table-column>
        <el-table-column label="条款" min-width="120">
          <template #default="{ row }">
            <el-input v-model="row.article" placeholder="条款号" @input="mark(row)" />
          </template>
        </el-table-column>
        <el-table-column label="页码 / 锚点" width="130">
          <template #default="{ row }">
            <el-input v-model="row.anchor" placeholder="页或锚点" @input="mark(row)" />
          </template>
        </el-table-column>
        <el-table-column label="原文" min-width="280">
          <template #default="{ row }">
            <el-input v-model="row.text" type="textarea" :autosize="{ minRows: 2, maxRows: 8 }" @input="mark(row)" />
          </template>
        </el-table-column>
        <el-table-column label="可见角色" min-width="200">
          <template #default="{ row }">
            <el-select v-model="row.visible_roles" multiple collapse-tags placeholder="继承文件" style="width: 100%" @change="mark(row)">
              <el-option v-for="r in DOC_ROLES" :key="r.value" :label="r.label" :value="r.value" />
            </el-select>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="90" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link :disabled="!row._dirty" :loading="row._saving" @click="saveOne(row)">保存</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div v-else class="empty-tip">{{ emptyText }}</div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import PageHeader from '@/components/PageHeader.vue'
import { DOC_ROLES } from '@/constants'
import { getDocument, listChunks, saveChunks, updateChunk } from '@/api/documents'
import { unwrapList } from '@/utils/error'

const route = useRoute()
const router = useRouter()
const loading = ref(false)
const saving = ref(false)
const doc = ref(null)
const chunks = ref([])

const title = computed(() => (doc.value?.filename ? `校对切块 · ${doc.value.filename}` : '校对切块'))
const subtitle = computed(() => {
  if (!doc.value) return '逐条核对原文、条款和可见范围。'
  const bits = [doc.value.semester && `生效学期 ${doc.value.semester}`, doc.value.is_priority ? '优先文件' : '']
  return bits.filter(Boolean).join(' · ') || '逐条核对原文、条款和可见范围。'
})
const dirtyCount = computed(() => chunks.value.filter((c) => c._dirty).length)
const emptyText = computed(() => {
  if (doc.value?.status === 'processing') return '正在切块，请稍后刷新。'
  return '还没有切块。若刚刚上传，请稍候刷新；若切块失败，请回到列表检查状态。'
})

function normalize(chunk) {
  return {
    id: chunk.id ?? chunk.chunk_id,
    section: chunk.section || '',
    article: chunk.article || '',
    anchor: chunk.anchor || (chunk.page != null ? String(chunk.page) : ''),
    text: chunk.text || chunk.content || chunk.quote || '',
    visible_roles: [...(chunk.visible_roles || chunk.roles || [])],
    _dirty: false,
    _saving: false,
  }
}

function mark(row) {
  row._dirty = true
}

function payloadOf(row) {
  const pageNum = Number(row.anchor)
  return {
    section: row.section,
    article: row.article,
    anchor: row.anchor,
    page: Number.isFinite(pageNum) && String(pageNum) === String(row.anchor).trim() ? pageNum : undefined,
    text: row.text,
    visible_roles: row.visible_roles,
  }
}

async function load() {
  const id = route.params.id
  loading.value = true
  try {
    try {
      const { data } = await getDocument(id)
      doc.value = data
    } catch {
      doc.value = { id, filename: '规章' }
    }
    const { data } = await listChunks(id)
    const list = unwrapList(data)
    chunks.value = list.items.map(normalize)
  } finally {
    loading.value = false
  }
}

async function saveOne(row) {
  row._saving = true
  try {
    await updateChunk(route.params.id, row.id, payloadOf(row))
    row._dirty = false
    ElMessage.success('已保存该切块')
  } finally {
    row._saving = false
  }
}

async function saveAll() {
  const dirty = chunks.value.filter((c) => c._dirty)
  if (!dirty.length) return
  saving.value = true
  try {
    try {
      await saveChunks(route.params.id, dirty.map((c) => ({ id: c.id, ...payloadOf(c) })))
      dirty.forEach((c) => { c._dirty = false })
      ElMessage.success(`已保存 ${dirty.length} 条切块`)
    } catch (err) {
      if (err?.response?.status === 404 || err?.response?.status === 405) {
        for (const row of dirty) {
          await updateChunk(route.params.id, row.id, payloadOf(row))
          row._dirty = false
        }
        ElMessage.success(`已逐条保存 ${dirty.length} 条切块`)
      } else {
        throw err
      }
    }
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.tip { margin-bottom: 4px; }
</style>

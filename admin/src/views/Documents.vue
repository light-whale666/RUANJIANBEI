<template>
  <div class="page">
    <PageHeader title="规章库" description="知识库默认空，不预置任何学校正文。请先下载空模板由校方填写后上传，或导入带【模板示例】字样的示例用于演示检索。入库时填写文件名、生效学期、适用角色、适用范围和是否优先文件。冲突时以优先文件为准；都未标记则提示人工确认。">
      <template #actions>
        <el-button @click="importExamples" :loading="importing">导入模板示例用于演示检索</el-button>
        <el-button type="primary" @click="openUpload()">上传校方文档</el-button>
      </template>
    </PageHeader>

    <div class="panel template-panel">
      <div class="template-head">
        <div>
          <h3>空模板</h3>
          <p class="template-note">【模板】请替换为学校正式文件，本文不是任何学校的正式校规。模板正文是【请填写…】占位符，下载后替换为学校正式文件再上传。导入的示例文件名带【模板示例】，仅供演示检索，不得当作正式校规。</p>
        </div>
      </div>
      <el-table :data="templates" v-loading="templatesLoading" stripe empty-text="暂无模板">
        <el-table-column prop="name" label="模板" min-width="160" />
        <el-table-column prop="category" label="类型" width="140" />
        <el-table-column prop="filename" label="下载文件名" min-width="220" show-overflow-tooltip />
        <el-table-column prop="description" label="说明" min-width="260" show-overflow-tooltip />
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="downloadTemplate(row)">下载空模板</el-button>
            <el-button v-if="row.has_example" type="primary" link @click="importOne(row)">导入该示例</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <div class="panel">
      <div class="toolbar">
        <el-input v-model="query.q" placeholder="搜索文件名" clearable style="width: 220px" @keyup.enter="reload(1)" />
        <el-input v-model="query.semester" placeholder="生效学期，如 2026-2027-1" clearable style="width: 200px" @keyup.enter="reload(1)" />
        <el-button type="primary" @click="reload(1)">查询</el-button>
        <el-button @click="resetQuery">重置</el-button>
      </div>

      <el-table :data="items" v-loading="loading" stripe empty-text="暂无规章。知识库默认为空，请先上传校方文档或导入模板示例。">
        <el-table-column prop="filename" label="文件名" min-width="200" show-overflow-tooltip />
        <el-table-column prop="semester" label="生效学期" width="140">
          <template #default="{ row }">{{ row.semester || '—' }}</template>
        </el-table-column>
        <el-table-column label="适用角色" min-width="180">
          <template #default="{ row }">
            <el-tag v-if="row.counselor_only" size="small" type="warning" style="margin-right: 4px">仅辅导员内部</el-tag>
            <el-tag v-for="r in asRoles(row)" :key="r" size="small" style="margin-right: 4px">{{ roleText(r) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="适用范围" min-width="140">
          <template #default="{ row }">{{ scopeText(row.scope) }}</template>
        </el-table-column>
        <el-table-column label="优先" width="80">
          <template #default="{ row }">
            <el-tag v-if="row.is_priority" size="small" class="priority-tag" effect="plain">优先</el-tag>
            <span v-else class="muted">否</span>
          </template>
        </el-table-column>
        <el-table-column label="切块" width="80">
          <template #default="{ row }">{{ row.chunk_count ?? '—' }}</template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)" size="small">{{ statusText(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="goChunks(row)">校对切块</el-button>
            <el-button type="primary" link @click="openUpload(row)">编辑信息</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pager">
        <el-pagination
          background
          layout="total, prev, pager, next, sizes"
          :total="total"
          :page-size="query.page_size"
          :current-page="query.page"
          :page-sizes="[10, 20, 50]"
          @current-change="reload"
          @size-change="onSizeChange"
        />
      </div>
    </div>

    <el-dialog v-model="dialogVisible" :title="editing ? '编辑规章信息' : '上传校方文档'" width="560px" destroy-on-close>
      <el-form ref="formRef" :model="form" :rules="formRules" label-width="108px">
        <el-form-item v-if="!editing" label="文件" prop="file">
          <el-upload
            :auto-upload="false"
            :limit="1"
            accept=".pdf,.doc,.docx,.txt,application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain"
            :on-change="onPickFile"
            :on-exceed="onExceedFile"
            :file-list="fileList"
          >
            <el-button>选择 PDF / Word / 文本</el-button>
            <template #tip>
              <div class="el-upload__tip">支持 .pdf、.doc、.docx、.txt。入库后将半自动切块，需人工校对。</div>
            </template>
          </el-upload>
        </el-form-item>
        <el-form-item label="文件名" prop="filename">
          <el-input v-model="form.filename" placeholder="如学校正式文件名，不要使用未替换的模板标题" />
        </el-form-item>
        <el-form-item label="生效学期" prop="semester">
          <el-input v-model="form.semester" placeholder="如 2026-2027-1" />
        </el-form-item>
        <el-form-item label="适用角色" prop="roles">
          <el-checkbox-group v-model="form.roles">
            <el-checkbox v-for="r in DOC_ROLES" :key="r.value" :value="r.value" :label="r.value">{{ r.label }}</el-checkbox>
          </el-checkbox-group>
        </el-form-item>
        <el-form-item label="辅导员内部">
          <el-switch v-model="form.counselor_only" />
          <span class="switch-hint">开启后，学生检索只提示「需辅导员查看」，不返回正文</span>
        </el-form-item>
        <el-form-item label="适用范围">
          <el-radio-group v-model="form.scopeType">
            <el-radio value="all">全体</el-radio>
            <el-radio value="colleges">指定学院</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item v-if="form.scopeType === 'colleges'" label="学院">
          <el-select v-model="form.colleges" multiple filterable allow-create default-first-option placeholder="输入学院名称后回车" style="width: 100%" />
        </el-form-item>
        <el-form-item label="优先文件">
          <el-switch v-model="form.is_priority" />
          <span class="switch-hint">不同文件冲突时，以优先文件为准</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitDoc">{{ editing ? '保存' : '上传并入库' }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import PageHeader from '@/components/PageHeader.vue'
import { DOC_ROLES, ROLE_LABEL } from '@/constants'
import { listDocuments, updateDocument, uploadDocument, listDocumentTemplates, downloadDocumentTemplate, importDocumentTemplate, importDocumentTemplateExamples } from '@/api/documents'
import { unwrapList } from '@/utils/error'

const router = useRouter()
const loading = ref(false)
const items = ref([])
const total = ref(0)
const templates = ref([])
const templatesLoading = ref(false)
const importing = ref(false)
const query = reactive({ q: '', semester: '', page: 1, page_size: 20 })

const dialogVisible = ref(false)
const formRef = ref()
const saving = ref(false)
const editing = ref(null)
const fileList = ref([])
const pickedFile = ref(null)

const emptyForm = () => ({
  filename: '',
  semester: '',
  roles: ['student'],
  counselor_only: false,
  scopeType: 'all',
  colleges: [],
  is_priority: false,
  file: null,
})
const form = reactive(emptyForm())
const formRules = {
  filename: [{ required: true, message: '请填写文件名', trigger: 'blur' }],
  semester: [{ required: true, message: '请填写生效学期', trigger: 'blur' }],
  roles: [{ type: 'array', required: true, min: 1, message: '请至少选择一个适用角色', trigger: 'change' }],
  file: [
    {
      validator: (_r, _v, cb) => {
        if (!editing.value && !pickedFile.value) cb(new Error('请选择要上传的文件'))
        else cb()
      },
      trigger: 'change',
    },
  ],
}

function asRoles(row) {
  return row.roles || row.applicable_roles || []
}

function roleText(r) {
  return ROLE_LABEL[r] || r
}

function scopeText(scope) {
  if (!scope) return '全体'
  if (typeof scope === 'string') return scope === 'all' ? '全体' : scope
  if (scope.type === 'colleges' && Array.isArray(scope.colleges) && scope.colleges.length) {
    return scope.colleges.join('、')
  }
  return '全体'
}

function statusText(status) {
  const map = { processing: '切块中', ready: '已就绪', failed: '失败', pending: '待校对' }
  return map[status] || status || '已入库'
}

function statusType(status) {
  if (status === 'failed') return 'danger'
  if (status === 'processing') return 'warning'
  if (status === 'pending') return 'info'
  return 'success'
}

function resetQuery() {
  query.q = ''
  query.semester = ''
  reload(1)
}

function onSizeChange(size) {
  query.page_size = size
  reload(1)
}

async function reload(page) {
  if (page) query.page = page
  loading.value = true
  try {
    const params = { page: query.page, page_size: query.page_size }
    if (query.q) params.q = query.q
    if (query.semester) params.semester = query.semester
    const { data } = await listDocuments(params)
    const list = unwrapList(data)
    items.value = list.items
    total.value = list.total
  } finally {
    loading.value = false
  }
}

function buildScope() {
  if (form.scopeType === 'colleges') return { type: 'colleges', colleges: form.colleges }
  return { type: 'all' }
}

function openUpload(row) {
  editing.value = row || null
  pickedFile.value = null
  fileList.value = []
  if (row) {
    const scope = row.scope || { type: 'all' }
    Object.assign(form, {
      filename: row.filename || '',
      semester: row.semester || '',
      roles: [...(asRoles(row) || ['student'])],
      counselor_only: Boolean(row.counselor_only),
      scopeType: scope.type === 'colleges' ? 'colleges' : 'all',
      colleges: scope.colleges ? [...scope.colleges] : [],
      is_priority: Boolean(row.is_priority),
      file: null,
    })
  } else {
    Object.assign(form, emptyForm())
  }
  dialogVisible.value = true
}

function onExceedFile(files) {
  fileList.value = []
  onPickFile(files[0])
}

function onPickFile(uploadFile) {
  const file = uploadFile.raw || uploadFile
  pickedFile.value = file
  fileList.value = [uploadFile]
  if (file && !form.filename) {
    form.filename = file.name.replace(/\.(pdf|docx?|txt)$/i, '')
  }
}

function goChunks(row) {
  router.push({ name: 'document-chunks', params: { id: row.id } })
}

async function submitDoc() {
  const ok = await formRef.value?.validate().catch(() => false)
  if (!ok) return
  saving.value = true
  try {
    const payload = {
      filename: form.filename.trim(),
      semester: form.semester.trim(),
      roles: form.roles,
      counselor_only: form.counselor_only,
      scope: buildScope(),
      is_priority: form.is_priority,
    }
    if (editing.value) {
      await updateDocument(editing.value.id, payload)
      ElMessage.success('已保存规章信息')
      dialogVisible.value = false
      await reload()
      return
    }
    const { data } = await uploadDocument(payload, pickedFile.value)
    ElMessage.success('已上传，正在切块')
    dialogVisible.value = false
    await reload(1)
    const id = data?.id || data?.document_id
    if (id) {
      try {
        await ElMessageBox.confirm('是否立即校对切块？', '入库成功', {
          confirmButtonText: '去校对',
          cancelButtonText: '稍后',
          type: 'success',
        })
        router.push({ name: 'document-chunks', params: { id } })
      } catch {
        /* 稍后 */
      }
    }
  } finally {
    saving.value = false
  }
}

async function loadTemplates() {
  templatesLoading.value = true
  try {
    const { data } = await listDocumentTemplates()
    templates.value = (data?.items || []).filter((t) => t.id !== 'enrollment-notice-prior' || t.has_example)
  } finally {
    templatesLoading.value = false
  }
}

function filenameFromDisposition(header, fallback) {
  if (!header) return fallback
  const utf = /filename\*=UTF-8''([^;]+)/i.exec(header)
  if (utf) return decodeURIComponent(utf[1])
  const plain = /filename="?([^"]+)"?/i.exec(header)
  return plain ? plain[1] : fallback
}

async function downloadTemplate(row) {
  const res = await downloadDocumentTemplate(row.id)
  const blob = new Blob([res.data], { type: res.headers['content-type'] || 'text/plain;charset=utf-8' })
  const name = filenameFromDisposition(res.headers['content-disposition'], row.filename)
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = name
  a.click()
  URL.revokeObjectURL(url)
}

async function importOne(row) {
  importing.value = true
  try {
    await importDocumentTemplate(row.id, true)
    ElMessage.success(`已导入 ${row.example_filename || row.filename}。这是【模板示例】，不是正式校规。`)
    await reload(1)
  } finally {
    importing.value = false
  }
}

async function importExamples() {
  importing.value = true
  try {
    const { data } = await importDocumentTemplateExamples(undefined, true)
    ElMessage.success(data?.message || '已导入模板示例，文件名带【模板示例】，不是正式校规。')
    await reload(1)
  } finally {
    importing.value = false
  }
}

onMounted(() => {
  reload(1)
  loadTemplates()
})
</script>

<style scoped>
.pager {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
.template-panel {
  margin-bottom: 16px;
}
.template-head h3 {
  margin: 0 0 6px;
  font-size: 16px;
}
.template-note {
  margin: 0 0 12px;
  color: var(--ca-muted);
  font-size: 13px;
  line-height: 1.55;
}
.muted { color: var(--ca-muted); }
.switch-hint {
  margin-left: 10px;
  color: var(--ca-muted);
  font-size: 12px;
  line-height: 1.4;
}
</style>

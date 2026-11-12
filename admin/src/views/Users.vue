<template>
  <div class="page">
    <PageHeader title="名单与班级归属" description="导入或维护学生、任课教师、辅导员名单。学号、姓名、学院专业年级班级由后台导入，学生可在 App 申请更正。">
      <template #actions>
        <el-button @click="downloadTemplate">下载导入模板</el-button>
        <el-button @click="openImport">导入名单</el-button>
        <el-button type="primary" @click="openEdit()">新建用户</el-button>
      </template>
    </PageHeader>

    <div class="panel">
      <div class="toolbar">
        <el-input v-model="query.q" placeholder="搜索姓名、用户名、学号" clearable style="width: 220px" @keyup.enter="reload(1)" />
        <el-select v-model="query.role" placeholder="角色" clearable style="width: 160px" @change="reload(1)">
          <el-option v-for="r in ROLES" :key="r.value" :label="r.label" :value="r.value" />
        </el-select>
        <el-input v-model="query.college" placeholder="学院" clearable style="width: 160px" @keyup.enter="reload(1)" />
        <el-input v-model="query.class_name" placeholder="班级" clearable style="width: 140px" @keyup.enter="reload(1)" />
        <el-button type="primary" @click="reload(1)">查询</el-button>
        <el-button @click="resetQuery">重置</el-button>
      </div>

      <el-table :data="items" v-loading="loading" stripe empty-text="暂无名单，请先导入或新建">
        <el-table-column prop="name" label="姓名" min-width="100" />
        <el-table-column prop="username" label="用户名" min-width="120" />
        <el-table-column label="角色" width="130">
          <template #default="{ row }">{{ ROLE_LABEL[row.role] || row.role }}</template>
        </el-table-column>
        <el-table-column label="学号 / 工号" min-width="130">
          <template #default="{ row }">{{ row.student_no || row.staff_no || '—' }}</template>
        </el-table-column>
        <el-table-column prop="college" label="学院" min-width="120" show-overflow-tooltip>
          <template #default="{ row }">{{ row.college || '—' }}</template>
        </el-table-column>
        <el-table-column label="专业年级班级" min-width="180" show-overflow-tooltip>
          <template #default="{ row }">{{ classLabel(row) }}</template>
        </el-table-column>
        <el-table-column label="辅导员" min-width="110">
          <template #default="{ row }">{{ row.counselor_name || row.counselor_username || '—' }}</template>
        </el-table-column>
        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link @click="openEdit(row)">编辑</el-button>
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
          :page-sizes="[10, 20, 50, 100]"
          @current-change="reload"
          @size-change="onSizeChange"
        />
      </div>
    </div>

    <el-drawer v-model="editVisible" :title="editing?.id ? '编辑用户与班级归属' : '新建用户'" size="480px">
      <el-form ref="editFormRef" :model="editForm" :rules="editRules" label-width="108px" label-position="right">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="editForm.username" :disabled="Boolean(editing?.id)" />
        </el-form-item>
        <el-form-item v-if="!editing?.id" label="密码" prop="password">
          <el-input v-model="editForm.password" type="password" show-password />
        </el-form-item>
        <el-form-item v-else label="新密码">
          <el-input v-model="editForm.password" type="password" show-password placeholder="留空则不修改" />
        </el-form-item>
        <el-form-item label="姓名" prop="name">
          <el-input v-model="editForm.name" />
        </el-form-item>
        <el-form-item label="角色" prop="role">
          <el-select v-model="editForm.role" style="width: 100%">
            <el-option v-for="r in ROLES" :key="r.value" :label="r.label" :value="r.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="学号">
          <el-input v-model="editForm.student_no" placeholder="学生填写" />
        </el-form-item>
        <el-form-item label="工号">
          <el-input v-model="editForm.staff_no" placeholder="教师 / 辅导员填写" />
        </el-form-item>
        <el-form-item label="学院">
          <el-input v-model="editForm.college" />
        </el-form-item>
        <el-form-item label="专业">
          <el-input v-model="editForm.major" />
        </el-form-item>
        <el-form-item label="年级">
          <el-input v-model="editForm.grade" placeholder="如 2026" />
        </el-form-item>
        <el-form-item label="班级">
          <el-input v-model="editForm.class_name" placeholder="如 软件2601" />
        </el-form-item>
        <el-form-item label="辅导员账号">
          <el-input v-model="editForm.counselor_username" placeholder="对应用户名" />
        </el-form-item>
        <el-form-item label="手机">
          <el-input v-model="editForm.phone" />
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input v-model="editForm.email" />
        </el-form-item>
        <el-form-item label="宿舍 / 床位">
          <div class="inline-2">
            <el-input v-model="editForm.dorm" placeholder="宿舍" />
            <el-input v-model="editForm.bed" placeholder="床位" />
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveUser">保存</el-button>
      </template>
    </el-drawer>

    <el-dialog v-model="importVisible" title="导入名单" width="720px" destroy-on-close>
      <p class="hint">请使用 CSV（可用模板）。角色取值：student / teacher / counselor / admin。导入后请核对学生班级与辅导员归属。</p>
      <el-upload
        drag
        :auto-upload="false"
        :limit="1"
        accept=".csv,text/csv"
        :on-change="onPickImport"
        :on-exceed="onExceedImport"
        :file-list="importFileList"
      >
        <div class="el-upload__text">将 CSV 拖到此处，或 <em>点击选择</em></div>
      </el-upload>
      <div v-if="preview.rows.length" class="preview">
        <div class="hint">预览前 {{ preview.rows.length }} 行（共解析 {{ preview.total }} 行）</div>
        <el-table :data="preview.rows" size="small" max-height="240">
          <el-table-column v-for="h in preview.headers" :key="h" :prop="h" :label="h" min-width="100" show-overflow-tooltip />
        </el-table>
      </div>
      <div v-if="importResult" class="result">
        <el-alert
          :type="importResult.errors?.length ? 'warning' : 'success'"
          :title="`新建 ${importResult.created ?? 0} 人，更新 ${importResult.updated ?? 0} 人${importResult.errors?.length ? `，${importResult.errors.length} 行失败` : ''}`"
          :closable="false"
          show-icon
        />
        <el-table v-if="importResult.errors?.length" :data="importResult.errors" size="small" max-height="180" class="err-table">
          <el-table-column prop="row" label="行" width="80" />
          <el-table-column prop="message" label="原因" />
        </el-table>
      </div>
      <template #footer>
        <el-button @click="importVisible = false">关闭</el-button>
        <el-button type="primary" :disabled="!importFile" :loading="importing" @click="doImport">确认导入</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import PageHeader from '@/components/PageHeader.vue'
import { createUser, importUsers, listUsers, updateUser } from '@/api/users'
import { IMPORT_TEMPLATE_URL, ROLE_LABEL, ROLES } from '@/constants'
import { unwrapList } from '@/utils/error'
import { parseCsv } from '@/utils/csv'

const loading = ref(false)
const items = ref([])
const total = ref(0)
const query = reactive({ q: '', role: '', college: '', class_name: '', page: 1, page_size: 20 })

const editVisible = ref(false)
const editFormRef = ref()
const saving = ref(false)
const editing = ref(null)
const emptyUser = () => ({
  username: '',
  password: '',
  name: '',
  role: 'student',
  student_no: '',
  staff_no: '',
  college: '',
  major: '',
  grade: '',
  class_name: '',
  counselor_username: '',
  phone: '',
  email: '',
  dorm: '',
  bed: '',
})
const editForm = reactive(emptyUser())
const editRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  name: [{ required: true, message: '请输入姓名', trigger: 'blur' }],
  role: [{ required: true, message: '请选择角色', trigger: 'change' }],
  password: [
    {
      validator: (_r, v, cb) => {
        if (!editing.value?.id && !v) cb(new Error('请设置初始密码'))
        else cb()
      },
      trigger: 'blur',
    },
  ],
}

const importVisible = ref(false)
const importFile = ref(null)
const importFileList = ref([])
const importing = ref(false)
const importResult = ref(null)
const preview = reactive({ headers: [], rows: [], total: 0 })

function classLabel(row) {
  const parts = [row.major, row.grade, row.class_name].filter(Boolean)
  return parts.length ? parts.join(' / ') : '—'
}

function resetQuery() {
  query.q = ''
  query.role = ''
  query.college = ''
  query.class_name = ''
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
    if (query.role) params.role = query.role
    if (query.college) params.college = query.college
    if (query.class_name) params.class_name = query.class_name
    const { data } = await listUsers(params)
    const list = unwrapList(data)
    items.value = list.items
    total.value = list.total
  } finally {
    loading.value = false
  }
}

function openEdit(row) {
  editing.value = row ? { ...row } : null
  const src = row || emptyUser()
  Object.assign(editForm, emptyUser(), {
    username: src.username || '',
    password: '',
    name: src.name || '',
    role: src.role || 'student',
    student_no: src.student_no || '',
    staff_no: src.staff_no || '',
    college: src.college || '',
    major: src.major || '',
    grade: src.grade || '',
    class_name: src.class_name || '',
    counselor_username: src.counselor_username || '',
    phone: src.phone || '',
    email: src.email || '',
    dorm: src.dorm || '',
    bed: src.bed || '',
  })
  editVisible.value = true
}

async function saveUser() {
  const ok = await editFormRef.value?.validate().catch(() => false)
  if (!ok) return
  saving.value = true
  try {
    const payload = { ...editForm }
    if (!payload.password) delete payload.password
    if (editing.value?.id) {
      await updateUser(editing.value.id, payload)
      ElMessage.success('已保存')
    } else {
      await createUser(payload)
      ElMessage.success('已新建')
    }
    editVisible.value = false
    await reload()
  } finally {
    saving.value = false
  }
}

function downloadTemplate() {
  const a = document.createElement('a')
  a.href = IMPORT_TEMPLATE_URL
  a.download = 'users-import-template.csv'
  a.click()
}

function openImport() {
  importFile.value = null
  importFileList.value = []
  importResult.value = null
  preview.headers = []
  preview.rows = []
  preview.total = 0
  importVisible.value = true
}

function onExceedImport(files) {
  importFileList.value = []
  onPickImport(files[0])
}

async function onPickImport(uploadFile) {
  const file = uploadFile.raw || uploadFile
  importFile.value = file
  importFileList.value = [uploadFile]
  importResult.value = null
  if (!file) return
  const text = await file.text()
  const parsed = parseCsv(text)
  preview.headers = parsed.headers
  preview.total = parsed.rows.length
  preview.rows = parsed.rows.slice(0, 8)
}

async function doImport() {
  if (!importFile.value) return
  importing.value = true
  try {
    const { data } = await importUsers(importFile.value)
    importResult.value = data
    ElMessage.success('导入完成')
    await reload(1)
  } finally {
    importing.value = false
  }
}

onMounted(() => reload(1))
</script>

<style scoped>
.pager {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
.inline-2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  width: 100%;
}
.preview,
.result { margin-top: 16px; }
.err-table { margin-top: 10px; }
</style>

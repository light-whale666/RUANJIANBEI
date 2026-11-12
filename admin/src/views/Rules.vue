<template>
  <div class="page">
    <PageHeader title="审批规则" description="短假阈值、加签条件和材料有效期放在这里，不要写死在提示词里。系统只建议层级，不代替老师批准。">
      <template #actions>
        <el-button @click="fillDefaults">恢复默认值</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存规则</el-button>
      </template>
    </PageHeader>

    <div class="panel" v-loading="loading">
      <el-form :model="form" label-width="220px" class="rules-form">
        <h3>短假判定</h3>
        <p class="hint">默认：不超过 1 个自然日且不跨天，且不影响已登记考试 → 只需辅导员审批。</p>
        <el-form-item label="短假最长自然日数">
          <el-input-number v-model="form.short_leave_max_days" :min="0.5" :max="30" :step="0.5" :precision="1" />
          <span class="unit">天</span>
        </el-form-item>
        <el-form-item label="短假必须在同一自然日（不跨天）">
          <el-switch v-model="form.short_leave_require_same_day" />
        </el-form-item>

        <h3>加签条件</h3>
        <p class="hint">跨天，或与已登记考试 / 课堂冲突时，在辅导员审批之外加一层。冲突本课则加签任课教师；名单中无年级负责人时，由辅导员终审并备案。</p>
        <el-form-item label="跨天时加签">
          <el-switch v-model="form.countersign_if_overnight" />
        </el-form-item>
        <el-form-item label="与已登记考试冲突时加签">
          <el-switch v-model="form.countersign_if_exam_conflict" />
        </el-form-item>
        <el-form-item label="与课堂任务冲突时加签">
          <el-switch v-model="form.countersign_if_class_conflict" />
        </el-form-item>
        <el-form-item label="无年级负责人时辅导员终审并备案">
          <el-switch v-model="form.counselor_final_if_no_grade_lead" />
        </el-form-item>

        <h3>材料有效期</h3>
        <p class="hint">假条、病例等附件在有效期内可复用，仍须走确认页。材料上缺日期时使用下面的默认天数，辅导员可在审批时调整。</p>
        <el-form-item label="材料有效期默认天数">
          <el-input-number v-model="form.attachment_valid_days_default" :min="1" :max="365" :step="1" />
          <span class="unit">天</span>
        </el-form-item>
      </el-form>
    </div>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import PageHeader from '@/components/PageHeader.vue'
import { DEFAULT_RULES } from '@/constants'
import { getRules, putRules } from '@/api/rules'

const loading = ref(false)
const saving = ref(false)
const form = reactive({ ...DEFAULT_RULES })

function apply(data) {
  Object.assign(form, DEFAULT_RULES, data || {})
}

function fillDefaults() {
  apply(DEFAULT_RULES)
  ElMessage.info('已填入默认值，点击「保存规则」后才会生效')
}

async function load() {
  loading.value = true
  try {
    const { data } = await getRules()
    apply(data)
  } finally {
    loading.value = false
  }
}

async function save() {
  saving.value = true
  try {
    await putRules({ ...form })
    ElMessage.success('审批规则已保存')
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.rules-form h3 {
  margin: 8px 0 4px;
  font-size: 15px;
}
.rules-form .hint {
  margin: 0 0 16px 0;
  padding-left: 0;
}
.unit {
  margin-left: 8px;
  color: var(--ca-muted);
  font-size: 13px;
}
</style>

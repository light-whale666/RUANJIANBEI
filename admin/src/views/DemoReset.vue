<template>
  <div class="page">
    <PageHeader title="演示数据" description="仅用于演示环境。重置会清空并重建演示师生、规章、待办和办事记录，不可用于生产数据。" />

    <div class="panel danger-panel">
      <h3>重置演示数据</h3>
      <p class="hint">
        将环境恢复到初版演示初始状态：一个班级的学生（含新生与高年级）、一名辅导员、两名任课教师，以及带学期冲突的规章、作业、招募、报到清单和奖助项目。
        现有办事记录会被覆盖，此操作不可撤销。
      </p>
      <el-button type="danger" :loading="resetting" @click="askReset">重置演示数据</el-button>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import PageHeader from '@/components/PageHeader.vue'
import { resetDemo } from '@/api/demo'

const resetting = ref(false)

async function askReset() {
  try {
    await ElMessageBox.confirm(
      '将清空并重建演示数据，学生端与教师端的办事记录会恢复到演示初始状态。此操作不可撤销。是否继续？',
      '第一次确认',
      {
        type: 'warning',
        confirmButtonText: '继续',
        cancelButtonText: '取消',
      },
    )
  } catch {
    return
  }

  try {
    const { value } = await ElMessageBox.prompt(
      '请输入「确认重置」以继续。',
      '第二次确认',
      {
        type: 'warning',
        confirmButtonText: '立即重置',
        cancelButtonText: '取消',
        confirmButtonClass: 'el-button--danger',
        inputPlaceholder: '确认重置',
        inputValidator: (v) => v === '确认重置' || '请准确输入：确认重置',
      },
    )
    if (value !== '确认重置') return
  } catch {
    return
  }

  resetting.value = true
  try {
    const { data } = await resetDemo()
    ElMessage.success(data?.message || '演示数据已重置')
  } finally {
    resetting.value = false
  }
}
</script>

<style scoped>
.danger-panel h3 {
  margin: 0 0 8px;
  font-size: 16px;
}
.danger-panel .hint {
  margin-bottom: 16px;
  max-width: 640px;
}
</style>

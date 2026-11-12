<template>
  <div class="login-page">
    <section class="intro">
      <div class="intro-inner">
        <div class="kicker">师生共用 · 管理端</div>
        <h1>校园办事与入学助手</h1>
        <p class="lead">管理员在此导入规章和名单、配置审批规则、准备演示数据。日常问答与审批不在后台完成。</p>
        <ul>
          <li>有依据才回答</li>
          <li>有校验才出单</li>
          <li>系统不代替拍板</li>
        </ul>
      </div>
    </section>
    <section class="form-side">
      <div class="card">
        <h2>管理后台登录</h2>
        <p class="sub">仅管理员账号可进入，学生与教师请使用 App。</p>
        <el-form ref="formRef" :model="form" :rules="rules" @submit.prevent="onSubmit" label-position="top">
          <el-form-item label="用户名" prop="username">
            <el-input v-model="form.username" size="large" autocomplete="username" placeholder="管理员账号" @keyup.enter="onSubmit" />
          </el-form-item>
          <el-form-item label="密码" prop="password">
            <el-input v-model="form.password" size="large" type="password" show-password autocomplete="current-password" placeholder="密码" @keyup.enter="onSubmit" />
          </el-form-item>
          <el-alert v-if="error" type="error" :title="error" show-icon :closable="false" class="err" />
          <el-button type="primary" size="large" class="submit" :loading="loading" @click="onSubmit">登录</el-button>
        </el-form>
      </div>
    </section>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { apiErrorMessage } from '@/utils/error'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const formRef = ref()
const loading = ref(false)
const error = ref('')
const form = reactive({ username: '', password: '' })
const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

async function onSubmit() {
  error.value = ''
  const ok = await formRef.value?.validate().catch(() => false)
  if (!ok) return
  loading.value = true
  try {
    await auth.login(form.username.trim(), form.password)
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/'
    router.replace(redirect || '/')
  } catch (err) {
    error.value = err.code === 'not_admin' ? err.message : apiErrorMessage(err, '登录失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: grid;
  grid-template-columns: minmax(280px, 1.1fr) minmax(320px, 1fr);
}
.intro {
  background:
    radial-gradient(1200px 500px at -10% -10%, rgba(42, 143, 136, 0.35), transparent 55%),
    linear-gradient(160deg, #15232b 0%, #1b3a3a 55%, #12302e 100%);
  color: #f4fbf9;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 48px;
}
.intro-inner { max-width: 420px; }
.kicker {
  font-size: 12px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: #9ad4cf;
  margin-bottom: 14px;
}
.intro h1 {
  margin: 0 0 16px;
  font-size: 32px;
  font-weight: 650;
  letter-spacing: 0.04em;
  line-height: 1.25;
}
.lead {
  margin: 0 0 28px;
  color: #c5d7d4;
  line-height: 1.7;
  font-size: 14px;
}
.intro ul {
  margin: 0;
  padding: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.intro li {
  font-size: 14px;
  padding-left: 16px;
  position: relative;
  color: #e7f3f1;
}
.intro li::before {
  content: "";
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #3cb8ae;
  position: absolute;
  left: 0;
  top: 8px;
}
.form-side {
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f3f6f5;
  padding: 40px 24px;
}
.card {
  width: 100%;
  max-width: 380px;
  background: #fff;
  border-radius: 16px;
  padding: 32px 28px 28px;
  border: 1px solid var(--ca-line);
  box-shadow: 0 10px 30px rgba(21, 35, 43, 0.06);
}
.card h2 {
  margin: 0 0 6px;
  font-size: 22px;
}
.sub {
  margin: 0 0 22px;
  color: var(--ca-muted);
  font-size: 13px;
}
.err { margin-bottom: 12px; }
.submit { width: 100%; margin-top: 6px; }
@media (max-width: 800px) {
  .login-page { grid-template-columns: 1fr; }
  .intro { display: none; }
}
</style>

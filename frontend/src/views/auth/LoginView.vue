<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { login } from '@/api/auth'
import { useAuth } from '@/composables/useAuth'
import { useToast } from '@/composables/useToast'
import AppInput from '@/components/ui/AppInput.vue'
import AppButton from '@/components/ui/AppButton.vue'

const router = useRouter()
const { saveAuth } = useAuth()
const toast = useToast()

const carId = ref('')
const password = ref('')
const loading = ref(false)

async function handleLogin() {
  if (!carId.value || !password.value) {
    toast.warning('请填写账号和密码')
    return
  }

  loading.value = true
  try {
    const data = await login({ car_id: carId.value, password: password.value })
    saveAuth(data)
    toast.success('登录成功')
    router.push(data.role === 'admin' ? '/admin' : '/user')
  } catch (e) {
    toast.error(e.message)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-form">
    <h2 class="form-title">登录</h2>
    <p class="form-desc">用户请输入车牌号，管理员请输入管理员编号</p>

    <form class="form" @submit.prevent="handleLogin">
      <AppInput
        v-model="carId"
        label="账号"
        placeholder="车牌号 / 管理员编号"
      />
      <AppInput
        v-model="password"
        label="密码"
        type="password"
        placeholder="请输入密码"
      />
      <AppButton type="submit" block :loading="loading" size="lg">
        登录
      </AppButton>
    </form>

    <p class="form-footer">
      还没有账号？
      <router-link to="/register">立即注册</router-link>
    </p>
  </div>
</template>

<style scoped>
.login-form {
  width: 100%;
  max-width: 380px;
}

.form-title {
  font-size: 1.75rem;
  font-weight: 800;
  letter-spacing: -0.02em;
}

.form-desc {
  margin-top: 8px;
  font-size: 0.875rem;
  color: var(--color-text-secondary);
  margin-bottom: 32px;
}

.form {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.form-footer {
  margin-top: 24px;
  text-align: center;
  font-size: 0.875rem;
  color: var(--color-text-secondary);
}
</style>

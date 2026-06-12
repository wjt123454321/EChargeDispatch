<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { register } from '@/api/auth'
import { useAuth } from '@/composables/useAuth'
import { useToast } from '@/composables/useToast'
import AppInput from '@/components/ui/AppInput.vue'
import AppButton from '@/components/ui/AppButton.vue'

const router = useRouter()
const { saveAuth } = useAuth()
const toast = useToast()

const form = ref({
  car_id: '',
  user_name: '',
  car_capacity: '60',
  password: '',
})
const loading = ref(false)

async function handleRegister() {
  if (!form.value.car_id || !form.value.password) {
    toast.warning('请填写车牌号和密码')
    return
  }

  loading.value = true
  try {
    const data = await register({
      car_id: form.value.car_id,
      user_name: form.value.user_name || undefined,
      car_capacity: Number(form.value.car_capacity) || 60,
      password: form.value.password,
    })
    saveAuth({ ...data, role: 'user' })
    toast.success('注册成功')
    router.push('/user')
  } catch (e) {
    toast.error(e.message)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="register-form">
    <h2 class="form-title">注册</h2>
    <p class="form-desc">创建车辆账号，开始使用充电服务</p>

    <form class="form" @submit.prevent="handleRegister">
      <AppInput
        v-model="form.car_id"
        label="车牌号 / 车辆编号"
        placeholder="如 V001"
        hint="作为登录账号，不可重复"
      />
      <AppInput
        v-model="form.user_name"
        label="用户姓名（选填）"
        placeholder="默认使用车牌号"
      />
      <AppInput
        v-model="form.car_capacity"
        label="电池容量（度）"
        type="number"
        placeholder="默认 60"
      />
      <AppInput
        v-model="form.password"
        label="密码"
        type="password"
        placeholder="设置登录密码"
      />
      <AppButton type="submit" block :loading="loading" size="lg">
        注册并登录
      </AppButton>
    </form>

    <p class="form-footer">
      已有账号？
      <router-link to="/login">返回登录</router-link>
    </p>
  </div>
</template>

<style scoped>
.register-form {
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

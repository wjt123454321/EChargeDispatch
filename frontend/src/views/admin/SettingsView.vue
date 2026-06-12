<script setup>
import { ref, onMounted } from 'vue'
import { getSystemConfig, updateSystemConfig } from '@/api/admin'
import { useToast } from '@/composables/useToast'
import { FAULT_STRATEGY, DISPATCH_MODE } from '@/utils/constants'
import AppCard from '@/components/ui/AppCard.vue'
import AppInput from '@/components/ui/AppInput.vue'
import AppSelect from '@/components/ui/AppSelect.vue'
import AppButton from '@/components/ui/AppButton.vue'
import AppLoading from '@/components/ui/AppLoading.vue'

const toast = useToast()

const loading = ref(true)
const saving = ref(false)
const config = ref({})

const faultOptions = Object.entries(FAULT_STRATEGY).map(([value, label]) => ({ value, label }))
const dispatchOptions = Object.entries(DISPATCH_MODE).map(([value, label]) => ({ value, label }))

async function fetchConfig() {
  loading.value = true
  try {
    config.value = await getSystemConfig()
  } catch (e) {
    toast.error(e.message)
  } finally {
    loading.value = false
  }
}

async function handleSave() {
  saving.value = true
  try {
    const data = await updateSystemConfig({
      fast_pile_num: Number(config.value.fast_pile_num),
      slow_pile_num: Number(config.value.slow_pile_num),
      waiting_area_size: Number(config.value.waiting_area_size),
      charging_queue_len: Number(config.value.charging_queue_len),
      fault_strategy: config.value.fault_strategy,
      dispatch_mode: config.value.dispatch_mode,
    })
    config.value = data
    toast.success('配置已保存')
  } catch (e) {
    toast.error(e.message)
  } finally {
    saving.value = false
  }
}

onMounted(fetchConfig)
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h1 class="page-title">系统配置</h1>
      <p class="page-desc">管理充电站参数与调度策略</p>
    </div>

    <AppLoading v-if="loading" />

    <form v-else class="settings-form" @submit.prevent="handleSave">
      <AppCard title="站点信息">
        <div class="info-row">
          <span class="info-label">站点编号</span>
          <span class="info-value">{{ config.station_id }}</span>
        </div>
        <div class="info-row">
          <span class="info-label">服务费单价</span>
          <span class="info-value">{{ config.service_price }} 元/度</span>
        </div>
      </AppCard>

      <AppCard title="充电桩配置">
        <div class="form-grid">
          <AppInput
            v-model="config.fast_pile_num"
            label="快充桩数量"
            type="number"
          />
          <AppInput
            v-model="config.slow_pile_num"
            label="慢充桩数量"
            type="number"
          />
          <AppInput
            v-model="config.waiting_area_size"
            label="等候区容量"
            type="number"
          />
          <AppInput
            v-model="config.charging_queue_len"
            label="每桩队列长度"
            type="number"
          />
        </div>
      </AppCard>

      <AppCard title="调度策略">
        <div class="form-grid">
          <AppSelect
            v-model="config.fault_strategy"
            label="故障调度策略"
            :options="faultOptions"
          />
          <AppSelect
            v-model="config.dispatch_mode"
            label="调度模式"
            :options="dispatchOptions"
          />
        </div>
      </AppCard>

      <AppButton type="submit" :loading="saving" size="lg">
        保存配置
      </AppButton>
    </form>
  </div>
</template>

<style scoped>
.settings-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
  max-width: 720px;
}

.info-row {
  display: flex;
  justify-content: space-between;
  padding: 10px 0;
  border-bottom: 1px solid var(--color-border-light);
  font-size: 0.875rem;
}

.info-row:last-child {
  border-bottom: none;
}

.info-label {
  color: var(--color-text-secondary);
}

.info-value {
  font-weight: 700;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

@media (max-width: 640px) {
  .form-grid {
    grid-template-columns: 1fr;
  }
}
</style>

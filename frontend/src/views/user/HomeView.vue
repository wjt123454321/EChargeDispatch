<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import {
  submitRequest,
  updateAmount,
  updateMode,
  getQueueStatus,
  getChargingStatus,
  startCharging,
  endCharging,
  cancelCharging,
} from '@/api/charging'
import { useToast } from '@/composables/useToast'
import { REQUEST_STATUS, CHARGE_MODE, PRICE_PERIODS, SERVICE_PRICE } from '@/utils/constants'
import { formatKwh, formatDateTime } from '@/utils/format'
import AppCard from '@/components/ui/AppCard.vue'
import AppButton from '@/components/ui/AppButton.vue'
import AppInput from '@/components/ui/AppInput.vue'
import AppBadge from '@/components/ui/AppBadge.vue'
import AppProgress from '@/components/ui/AppProgress.vue'
import AppLoading from '@/components/ui/AppLoading.vue'
import AppModal from '@/components/ui/AppModal.vue'

const toast = useToast()

const loading = ref(true)
const actionLoading = ref(false)
const queueData = ref(null)
const chargingData = ref(null)

// 新请求表单
const requestMode = ref('F')
const requestAmount = ref('20')

// 修改表单
const editAmount = ref('')
const showCancelModal = ref(false)

const hasRequest = computed(() => queueData.value?.has_request)
const status = computed(() => queueData.value?.status || chargingData.value?.status)
const isQueuing = computed(() => status.value === 'queuing')
const isDispatched = computed(() => status.value === 'dispatched')
const isCharging = computed(() => status.value === 'charging')
const canModify = computed(() => isQueuing.value)

const progress = computed(() => {
  if (!chargingData.value?.request_amount) return 0
  return chargingData.value.charged_amount || 0
})

const progressMax = computed(() => chargingData.value?.request_amount || 100)

let pollTimer = null

async function fetchStatus() {
  try {
    const [queue, charging] = await Promise.all([
      getQueueStatus(),
      getChargingStatus(),
    ])
    queueData.value = queue
    chargingData.value = charging
    if (queue.has_request) {
      editAmount.value = String(charging.request_amount || queue.request_amount || '')
    }
  } catch (e) {
    toast.error(e.message)
  } finally {
    loading.value = false
  }
}

function startPolling() {
  pollTimer = setInterval(fetchStatus, 5000)
}

async function handleSubmit() {
  const amount = Number(requestAmount.value)
  if (!amount || amount <= 0) {
    toast.warning('请输入有效的充电量')
    return
  }
  actionLoading.value = true
  try {
    await submitRequest({ request_mode: requestMode.value, request_amount: amount })
    toast.success('充电请求已提交')
    await fetchStatus()
  } catch (e) {
    toast.error(e.message)
  } finally {
    actionLoading.value = false
  }
}

async function handleUpdateAmount() {
  const amount = Number(editAmount.value)
  if (!amount || amount <= 0) return
  actionLoading.value = true
  try {
    await updateAmount(amount)
    toast.success('充电量已更新')
    await fetchStatus()
  } catch (e) {
    toast.error(e.message)
  } finally {
    actionLoading.value = false
  }
}

async function handleSwitchMode(mode) {
  if (mode === queueData.value?.request_mode) return
  actionLoading.value = true
  try {
    await updateMode(mode)
    toast.success('充电模式已切换，排队号已更新')
    await fetchStatus()
  } catch (e) {
    toast.error(e.message)
  } finally {
    actionLoading.value = false
  }
}

async function handleStart() {
  const pileId = queueData.value?.position?.pile_id
  if (!pileId) {
    toast.warning('尚未分配到充电桩')
    return
  }
  actionLoading.value = true
  try {
    await startCharging(pileId)
    toast.success('充电已开始')
    await fetchStatus()
  } catch (e) {
    toast.error(e.message)
  } finally {
    actionLoading.value = false
  }
}

async function handleEnd() {
  actionLoading.value = true
  try {
    const data = await endCharging()
    toast.success(`充电结束，实际充电 ${formatKwh(data.charged_amount)}`)
    await fetchStatus()
  } catch (e) {
    toast.error(e.message)
  } finally {
    actionLoading.value = false
  }
}

async function handleCancel() {
  actionLoading.value = true
  try {
    await cancelCharging()
    toast.success('已取消充电请求')
    showCancelModal.value = false
    await fetchStatus()
  } catch (e) {
    toast.error(e.message)
  } finally {
    actionLoading.value = false
  }
}

onMounted(() => {
  fetchStatus()
  startPolling()
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h1 class="page-title">充电服务</h1>
      <p class="page-desc">提交充电请求、查看排队状态、管理充电过程</p>
    </div>

    <AppLoading v-if="loading" />

    <template v-else>
      <!-- 无活跃请求：提交新请求 -->
      <div v-if="!hasRequest" class="grid-2">
        <AppCard title="提交充电请求">
          <div class="request-form">
            <div class="mode-selector">
              <button
                class="mode-btn"
                :class="{ 'mode-btn--active': requestMode === 'F' }"
                @click="requestMode = 'F'"
              >
                <span class="mode-btn__icon">⚡</span>
                <span class="mode-btn__label">快充</span>
                <span class="mode-btn__desc">{{ CHARGE_MODE.F.desc }}</span>
              </button>
              <button
                class="mode-btn"
                :class="{ 'mode-btn--active mode-btn--slow': requestMode === 'T' }"
                @click="requestMode = 'T'"
              >
                <span class="mode-btn__icon">🔋</span>
                <span class="mode-btn__label">慢充</span>
                <span class="mode-btn__desc">{{ CHARGE_MODE.T.desc }}</span>
              </button>
            </div>
            <AppInput
              v-model="requestAmount"
              label="请求充电量（度）"
              type="number"
              placeholder="如 20"
            />
            <AppButton variant="accent" block :loading="actionLoading" @click="handleSubmit">
              提交请求
            </AppButton>
          </div>
        </AppCard>

        <AppCard title="计费说明">
          <div class="price-info">
            <div class="price-row price-row--service">
              <span>服务费</span>
              <strong>{{ SERVICE_PRICE }} 元/度</strong>
            </div>
            <div v-for="p in PRICE_PERIODS" :key="p.name" class="price-row">
              <div>
                <span class="price-name">{{ p.name }}</span>
                <span class="price-time">{{ p.time }}</span>
              </div>
              <strong>{{ p.price }} 元/度</strong>
            </div>
            <p class="price-formula">总费用 = 充电费 + 服务费</p>
          </div>
        </AppCard>
      </div>

      <!-- 有活跃请求 -->
      <div v-else class="active-session">
        <!-- 状态概览 -->
        <div class="status-hero" :class="`status-hero--${status}`">
          <div class="status-hero__left">
            <span class="queue-number">{{ queueData.queue_num }}</span>
            <AppBadge :color="REQUEST_STATUS[status]?.color || 'info'" dot>
              {{ REQUEST_STATUS[status]?.label || status }}
            </AppBadge>
          </div>
          <div class="status-hero__right">
            <div class="status-stat">
              <span class="status-stat__label">充电模式</span>
              <span class="status-stat__value" :class="queueData.request_mode === 'F' ? 'text-fast' : 'text-slow'">
                {{ CHARGE_MODE[queueData.request_mode]?.label }}
              </span>
            </div>
            <div class="status-stat">
              <span class="status-stat__label">当前位置</span>
              <span class="status-stat__value">
                {{ queueData.position?.position || '—' }}
              </span>
            </div>
            <div class="status-stat">
              <span class="status-stat__label">前方等待</span>
              <span class="status-stat__value">{{ queueData.ahead_count }} 辆</span>
            </div>
          </div>
        </div>

        <div class="grid-2">
          <!-- 充电进度（充电中） -->
          <AppCard v-if="isCharging" title="充电进度">
            <div class="charging-progress">
              <AppProgress
                :value="progress"
                :max="progressMax"
                color="accent"
                animated
              >
                <template #label>
                  <span>{{ formatKwh(progress) }} / {{ formatKwh(progressMax) }}</span>
                </template>
              </AppProgress>
              <div class="charging-meta">
                <span>充电桩 #{{ chargingData.pile_id }}</span>
                <span>开始于 {{ formatDateTime(chargingData.start_time) }}</span>
              </div>
              <div class="action-row">
                <AppButton variant="accent" :loading="actionLoading" @click="handleEnd">
                  结束充电
                </AppButton>
                <AppButton variant="ghost" @click="showCancelModal = true">
                  取消充电
                </AppButton>
              </div>
            </div>
          </AppCard>

          <!-- 等待调度 -->
          <AppCard v-else-if="isDispatched" title="等待开始充电">
            <p class="dispatch-hint">
              您已调度至充电桩 <strong>#{{ queueData.position?.pile_id }}</strong>，
              <template v-if="queueData.ahead_count === 0">
                队列第一位，可以开始充电。
              </template>
              <template v-else>
                前方还有 <strong>{{ queueData.ahead_count }}</strong> 辆车。
              </template>
            </p>
            <div class="action-row">
              <AppButton
                variant="accent"
                :loading="actionLoading"
                :disabled="queueData.ahead_count > 0"
                @click="handleStart"
              >
                开始充电
              </AppButton>
              <AppButton variant="ghost" @click="showCancelModal = true">
                取消排队
              </AppButton>
            </div>
          </AppCard>

          <!-- 等候区 -->
          <AppCard v-else title="等候区排队">
            <p class="dispatch-hint">
              您在等候区排队，前方 <strong>{{ queueData.ahead_count }}</strong> 辆车。
              有空位时系统将自动调度。
            </p>
            <div class="action-row">
              <AppButton variant="ghost" @click="showCancelModal = true">
                取消排队
              </AppButton>
            </div>
          </AppCard>

          <!-- 修改请求 -->
          <AppCard title="修改请求">
            <div class="edit-form">
              <div class="mode-selector mode-selector--compact">
                <button
                  class="mode-btn mode-btn--sm"
                  :class="{ 'mode-btn--active': queueData.request_mode === 'F' }"
                  :disabled="!canModify"
                  @click="handleSwitchMode('F')"
                >
                  快充
                </button>
                <button
                  class="mode-btn mode-btn--sm"
                  :class="{ 'mode-btn--active mode-btn--slow': queueData.request_mode === 'T' }"
                  :disabled="!canModify"
                  @click="handleSwitchMode('T')"
                >
                  慢充
                </button>
              </div>
              <p v-if="!canModify" class="edit-hint">
                已进入充电区，无法修改模式或充电量
              </p>
              <AppInput
                v-model="editAmount"
                label="请求充电量（度）"
                type="number"
                :disabled="!canModify"
              />
              <AppButton
                variant="secondary"
                :loading="actionLoading"
                :disabled="!canModify"
                @click="handleUpdateAmount"
              >
                更新充电量
              </AppButton>
            </div>
          </AppCard>
        </div>
      </div>
    </template>

    <!-- 取消确认弹窗 -->
    <AppModal
      :show="showCancelModal"
      title="确认取消"
      @close="showCancelModal = false"
    >
      <p>确定要取消当前充电请求吗？{{ isCharging ? '正在充电的车辆将按已充电量计费。' : '' }}</p>
      <template #footer>
        <AppButton variant="ghost" @click="showCancelModal = false">返回</AppButton>
        <AppButton variant="danger" :loading="actionLoading" @click="handleCancel">
          确认取消
        </AppButton>
      </template>
    </AppModal>
  </div>
</template>

<style scoped>
.request-form,
.edit-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.mode-selector {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.mode-selector--compact {
  gap: 8px;
}

.mode-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 18px 12px;
  border: 2px solid var(--color-border);
  border-radius: var(--radius-md);
  transition: all var(--transition-fast);
  text-align: center;
}

.mode-btn--sm {
  padding: 10px;
  font-weight: 600;
  font-size: 0.875rem;
}

.mode-btn:hover:not(:disabled) {
  border-color: var(--color-fast);
}

.mode-btn--active {
  border-color: var(--color-fast);
  background: var(--color-accent-muted);
}

.mode-btn--active.mode-btn--slow {
  border-color: var(--color-slow);
  background: rgba(61, 107, 142, 0.1);
}

.mode-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.mode-btn__icon { font-size: 1.5rem; }
.mode-btn__label { font-weight: 700; font-size: 0.9375rem; }
.mode-btn__desc { font-size: 0.75rem; color: var(--color-text-muted); }

.price-info {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.price-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 0;
  border-bottom: 1px solid var(--color-border-light);
  font-size: 0.875rem;
}

.price-row--service {
  background: var(--color-primary-muted);
  padding: 10px 14px;
  border-radius: var(--radius-sm);
  border: none;
  margin-bottom: 4px;
}

.price-name {
  font-weight: 600;
  margin-right: 8px;
}

.price-time {
  font-size: 0.75rem;
  color: var(--color-text-muted);
}

.price-formula {
  margin-top: 8px;
  font-size: 0.8125rem;
  color: var(--color-text-muted);
  text-align: center;
}

/* 活跃会话 */
.status-hero {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 28px 32px;
  background: var(--color-bg-elevated);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-xl);
  margin-bottom: 24px;
  box-shadow: var(--shadow-sm);
}

.status-hero--charging {
  border-color: rgba(196, 92, 38, 0.25);
  background: linear-gradient(135deg, #fff 60%, var(--color-accent-muted));
}

.status-hero__left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.queue-number {
  font-size: 2.5rem;
  font-weight: 900;
  letter-spacing: -0.03em;
  color: var(--color-primary);
  font-variant-numeric: tabular-nums;
}

.status-hero__right {
  display: flex;
  gap: 32px;
}

.status-stat {
  text-align: center;
}

.status-stat__label {
  display: block;
  font-size: 0.75rem;
  color: var(--color-text-muted);
  margin-bottom: 4px;
}

.status-stat__value {
  font-size: 1rem;
  font-weight: 700;
}

.text-fast { color: var(--color-fast); }
.text-slow { color: var(--color-slow); }

.dispatch-hint {
  font-size: 0.9375rem;
  color: var(--color-text-secondary);
  line-height: 1.7;
  margin-bottom: 20px;
}

.charging-meta {
  display: flex;
  justify-content: space-between;
  margin-top: 12px;
  font-size: 0.8125rem;
  color: var(--color-text-muted);
}

.action-row {
  display: flex;
  gap: 10px;
  margin-top: 20px;
}

.edit-hint {
  font-size: 0.8125rem;
  color: var(--color-warning);
}

@media (max-width: 768px) {
  .status-hero {
    flex-direction: column;
    gap: 20px;
    text-align: center;
  }

  .status-hero__right {
    gap: 20px;
  }
}
</style>

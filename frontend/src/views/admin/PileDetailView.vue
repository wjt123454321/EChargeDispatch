<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getPileQueue } from '@/api/admin'
import { useToast } from '@/composables/useToast'
import { REQUEST_STATUS, PILE_STATUS } from '@/utils/constants'
import { formatKwh, formatWaitTime } from '@/utils/format'
import AppCard from '@/components/ui/AppCard.vue'
import AppBadge from '@/components/ui/AppBadge.vue'
import AppLoading from '@/components/ui/AppLoading.vue'
import AppEmpty from '@/components/ui/AppEmpty.vue'

const route = useRoute()
const router = useRouter()
const toast = useToast()

const loading = ref(true)
const data = ref(null)

const queueSummary = computed(() => {
  if (!data.value) return ''
  const used = data.value.queue_used ?? data.value.queue?.length ?? 0
  const total = data.value.queue_total ?? '—'
  return `队列 ${used}/${total}`
})

async function fetchQueue(silent = false) {
  if (!silent) loading.value = true
  try {
    data.value = await getPileQueue(route.params.id)
  } catch (e) {
    toast.error(e.message)
    if (!silent) router.push('/admin')
  } finally {
    loading.value = false
  }
}

let pollTimer = null

onMounted(() => {
  fetchQueue()
  pollTimer = setInterval(() => fetchQueue(true), 5000)
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})
</script>

<template>
  <div class="page">
    <div class="page-header">
      <button class="back-btn" @click="router.push('/admin')">← 返回监控</button>
      <h1 class="page-title">
        充电桩 {{ data?.pile_no || '' }}
      </h1>
      <p v-if="data" class="page-desc">
        <AppBadge :color="PILE_STATUS[data.status]?.color" dot>
          {{ PILE_STATUS[data.status]?.label }}
        </AppBadge>
        <span class="queue-summary">{{ queueSummary }}</span>
      </p>
    </div>

    <AppLoading v-if="loading" />

    <template v-else-if="data">
      <AppCard title="队列车辆（队首为正在/即将充电）">
        <AppEmpty
          v-if="!data.queue?.length"
          title="队列为空"
          description="当前没有车辆在此充电桩排队或充电"
        />
        <div v-else class="queue-table">
          <div class="queue-header">
            <span>#</span>
            <span>排队号</span>
            <span>车牌号</span>
            <span>用户 ID</span>
            <span>电池容量</span>
            <span>请求充电量</span>
            <span>已充电量</span>
            <span>等待时长</span>
            <span>状态</span>
          </div>
          <div
            v-for="item in data.queue"
            :key="item.request_id"
            class="queue-row"
            :class="{ 'queue-row--charging': item.status === 'charging' }"
          >
            <span class="position">{{ item.position }}</span>
            <span class="queue-num">{{ item.queue_num }}</span>
            <span class="car-id">{{ item.car_id }}</span>
            <span>{{ item.user_id }}</span>
            <span>{{ formatKwh(item.battery_capacity) }}</span>
            <span>{{ formatKwh(item.request_amount) }}</span>
            <span class="charged">
              {{ item.status === 'charging' ? formatKwh(item.charged_amount) : '—' }}
            </span>
            <span>{{ formatWaitTime(item.waiting_seconds) }}</span>
            <AppBadge :color="REQUEST_STATUS[item.status]?.color || 'muted'" dot>
              {{ REQUEST_STATUS[item.status]?.label || item.status }}
            </AppBadge>
          </div>
        </div>
      </AppCard>
    </template>
  </div>
</template>

<style scoped>
.back-btn {
  font-size: 0.875rem;
  color: var(--color-text-secondary);
  margin-bottom: 8px;
  transition: color var(--transition-fast);
}

.back-btn:hover {
  color: var(--color-primary);
}

.page-desc {
  display: flex;
  align-items: center;
  gap: 12px;
}

.queue-summary {
  font-size: 0.875rem;
  font-weight: 600;
  color: var(--color-text-secondary);
}

.queue-table {
  overflow-x: auto;
}

.queue-header,
.queue-row {
  display: grid;
  grid-template-columns: 36px 72px 1fr 72px 96px 96px 88px 110px 96px;
  gap: 10px;
  align-items: center;
  padding: 12px 0;
  font-size: 0.8125rem;
}

.queue-header {
  font-weight: 700;
  color: var(--color-text-muted);
  border-bottom: 2px solid var(--color-border);
  font-size: 0.75rem;
}

.queue-row {
  border-bottom: 1px solid var(--color-border-light);
  transition: background var(--transition-fast);
}

.queue-row--charging {
  background: var(--color-accent-muted);
}

.position {
  font-weight: 800;
  color: var(--color-text-muted);
  text-align: center;
}

.queue-num {
  font-weight: 800;
  color: var(--color-primary);
}

.car-id {
  font-weight: 600;
}

.charged {
  font-weight: 700;
  color: var(--color-accent);
}

@media (max-width: 768px) {
  .queue-table {
    margin: 0 -4px;
  }

  .queue-header,
  .queue-row {
    min-width: 680px;
    font-size: 0.75rem;
  }
}
</style>

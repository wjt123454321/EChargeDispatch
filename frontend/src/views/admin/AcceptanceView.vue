<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { getAcceptanceSnapshot } from '@/api/admin'
import { useToast } from '@/composables/useToast'
import AppCard from '@/components/ui/AppCard.vue'
import AppBadge from '@/components/ui/AppBadge.vue'
import AppLoading from '@/components/ui/AppLoading.vue'

const toast = useToast()
const loading = ref(true)
const snapshot = ref(null)

const pileCols = [
  { key: 'F1', label: '快充1' },
  { key: 'F2', label: '快充2' },
  { key: 'T1', label: '慢充1' },
  { key: 'T2', label: '慢充2' },
  { key: 'T3', label: '慢充3' },
]

async function fetchSnapshot() {
  try {
    snapshot.value = await getAcceptanceSnapshot()
  } catch (e) {
    toast.error(e.message)
  } finally {
    loading.value = false
  }
}

let timer = null

onMounted(() => {
  fetchSnapshot()
  timer = setInterval(fetchSnapshot, 3000)
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h1 class="page-title">验收快照</h1>
      <p class="page-desc">
        配合 <code>python manage.py run_acceptance</code> 使用，每 3 秒刷新填表数据
      </p>
    </div>

    <AppCard title="使用说明" class="hint-card">
      <ol class="hint-list">
        <li>终端执行：<code>python manage.py run_acceptance --fast</code>（调试）或去掉 <code>--fast</code>（真实 30 秒节奏）</li>
        <li>每个时刻占 3 行（队列长度 M=3）：桩位第 2、3 行显示排队车辆</li>
        <li>仅查看当前状态：<code>python manage.py run_acceptance --snapshot-only</code></li>
      </ol>
    </AppCard>

    <AppLoading v-if="loading" />

    <template v-else-if="snapshot">
      <div class="status-bar">
        <AppBadge :color="snapshot.sim_active ? 'success' : 'muted'" dot>
          {{ snapshot.sim_active ? '模拟时钟运行中' : '真实时间' }}
        </AppBadge>
        <span v-if="snapshot.sim_time" class="sim-time">
          模拟时刻：{{ new Date(snapshot.sim_time).toLocaleString('zh-CN') }}
        </span>
        <span v-if="snapshot.case_time" class="sim-time">
          用例时刻：{{ snapshot.case_time }}
        </span>
      </div>

      <AppCard title="填表快照（3 行 / 时刻）">
        <div class="table-wrap">
          <table class="accept-table">
            <thead>
              <tr>
                <th>行</th>
                <th v-for="col in pileCols" :key="col.key">{{ col.label }}</th>
                <th>等候区</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="(row, idx) in snapshot.table_rows"
                :key="idx"
              >
                <td class="row-label">{{ idx + 1 }}</td>
                <td
                  v-for="col in pileCols"
                  :key="col.key"
                  class="mono"
                >
                  {{ row[col.label] || '-' }}
                </td>
                <td class="mono waiting-cell">{{ row['等候区'] }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </AppCard>

      <AppCard title="充电桩队列明细">
        <div class="pile-grid">
          <div v-for="col in pileCols" :key="col.key" class="pile-cell">
            <span class="pile-label">{{ col.label }}</span>
            <div
              v-for="(slot, idx) in snapshot.piles[col.key]?.slots || ['-']"
              :key="idx"
              class="pile-slot"
            >
              <span class="slot-index">#{{ idx + 1 }}</span>
              <span class="pile-value">{{ slot }}</span>
            </div>
          </div>
        </div>
      </AppCard>

      <AppCard title="等候区">
        <div class="waiting-summary">
          占用 {{ snapshot.waiting_area.used }}/{{ snapshot.waiting_area.capacity }}
        </div>
        <p class="waiting-display">{{ snapshot.waiting_area.display }}</p>
        <div v-if="snapshot.waiting_area.items?.length" class="waiting-list">
          <div
            v-for="item in snapshot.waiting_area.items"
            :key="item.car_id"
            class="waiting-item"
          >
            <strong>{{ item.queue_num }}</strong>
            {{ item.car_id }} · {{ item.request_mode === 'F' ? '快充' : '慢充' }}
            · {{ item.request_amount }} 度
          </div>
        </div>
      </AppCard>
    </template>
  </div>
</template>

<style scoped>
.hint-card {
  margin-bottom: 20px;
}

.hint-list {
  margin-left: 20px;
  font-size: 0.875rem;
  color: var(--color-text-secondary);
  line-height: 1.8;
}

code {
  font-family: var(--font-mono);
  font-size: 0.8125rem;
  background: var(--color-surface-muted);
  padding: 2px 6px;
  border-radius: 4px;
}

.status-bar {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 16px;
  margin-bottom: 20px;
}

.sim-time {
  font-size: 0.875rem;
  color: var(--color-text-secondary);
}

.table-wrap {
  overflow-x: auto;
}

.accept-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.8125rem;
}

.accept-table th,
.accept-table td {
  border: 1px solid var(--color-border);
  padding: 8px 10px;
  text-align: center;
}

.accept-table th {
  background: var(--color-surface-muted);
  font-weight: 700;
}

.row-label {
  font-weight: 700;
  color: var(--color-text-secondary);
  width: 48px;
}

.mono {
  font-family: var(--font-mono);
  word-break: break-all;
}

.waiting-cell {
  min-width: 180px;
}

.pile-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 12px;
}

.pile-cell {
  background: var(--color-surface-muted);
  border-radius: var(--radius-md);
  padding: 14px;
}

.pile-label {
  display: block;
  font-weight: 800;
  color: var(--color-primary);
  margin-bottom: 8px;
  text-align: center;
}

.pile-slot {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  margin-bottom: 6px;
}

.slot-index {
  font-size: 0.75rem;
  color: var(--color-text-secondary);
  flex-shrink: 0;
}

.pile-value {
  font-size: 0.8125rem;
  font-family: var(--font-mono);
  word-break: break-all;
}

.waiting-summary {
  font-weight: 700;
  margin-bottom: 8px;
}

.waiting-display {
  font-family: var(--font-mono);
  font-size: 0.875rem;
  color: var(--color-text-secondary);
  margin-bottom: 12px;
  word-break: break-all;
}

.waiting-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.waiting-item {
  font-size: 0.8125rem;
  padding: 8px 12px;
  background: var(--color-primary-muted);
  border-radius: var(--radius-sm);
}

@media (max-width: 768px) {
  .pile-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>

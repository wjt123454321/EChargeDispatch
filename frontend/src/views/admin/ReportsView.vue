<script setup>
import { ref, onMounted } from 'vue'
import { getReportStats } from '@/api/admin'
import { useToast } from '@/composables/useToast'
import { formatMoney, formatKwh, formatDuration } from '@/utils/format'
import AppCard from '@/components/ui/AppCard.vue'
import AppTabs from '@/components/ui/AppTabs.vue'
import AppInput from '@/components/ui/AppInput.vue'
import AppButton from '@/components/ui/AppButton.vue'
import AppLoading from '@/components/ui/AppLoading.vue'
import AppEmpty from '@/components/ui/AppEmpty.vue'

const toast = useToast()

const period = ref('day')
const date = ref(new Date().toISOString().slice(0, 10))
const loading = ref(false)
const report = ref(null)

const tabs = [
  { key: 'day', label: '日报' },
  { key: 'week', label: '周报' },
  { key: 'month', label: '月报' },
]

const dateLabel = ref('日期')
const dateInputType = ref('date')

function onPeriodChange(p) {
  period.value = p
  if (p === 'month') {
    date.value = new Date().toISOString().slice(0, 7)
    dateLabel.value = '月份'
    dateInputType.value = 'month'
  } else {
    date.value = new Date().toISOString().slice(0, 10)
    dateLabel.value = '日期'
    dateInputType.value = 'date'
  }
}

async function fetchReport() {
  if (!date.value) {
    toast.warning('请选择日期')
    return
  }
  loading.value = true
  try {
    report.value = await getReportStats(period.value, date.value)
  } catch (e) {
    toast.error(e.message)
    report.value = null
  } finally {
    loading.value = false
  }
}

// 汇总统计
function getTotals(items) {
  if (!items?.length) return null
  return items.reduce(
    (acc, item) => ({
      charge_num: acc.charge_num + item.total_charge_num,
      charge_time: acc.charge_time + item.total_charge_time,
      charge_capacity: acc.charge_capacity + item.total_charge_capacity,
      charge_fee: acc.charge_fee + item.total_charge_fee,
      service_fee: acc.service_fee + item.total_service_fee,
      total_fee: acc.total_fee + item.total_fee,
    }),
    { charge_num: 0, charge_time: 0, charge_capacity: 0, charge_fee: 0, service_fee: 0, total_fee: 0 },
  )
}

onMounted(fetchReport)
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h1 class="page-title">统计报表</h1>
      <p class="page-desc">按日、周、月查看各充电桩运营数据</p>
    </div>

    <div class="report-controls">
      <AppTabs :tabs="tabs" :model-value="period" @update:model-value="onPeriodChange" />
      <div class="report-filters">
        <AppInput v-model="date" :label="dateLabel" :type="dateInputType" />
        <AppButton :loading="loading" @click="fetchReport">查询</AppButton>
      </div>
    </div>

    <AppLoading v-if="loading" />

    <template v-else-if="report">
      <!-- 汇总卡片 -->
      <div v-if="getTotals(report.items)" class="totals-grid">
        <div class="total-card">
          <span class="total-card__val">{{ getTotals(report.items).charge_num }}</span>
          <span class="total-card__label">总充电次数</span>
        </div>
        <div class="total-card">
          <span class="total-card__val">{{ formatKwh(getTotals(report.items).charge_capacity) }}</span>
          <span class="total-card__label">总充电量</span>
        </div>
        <div class="total-card">
          <span class="total-card__val">{{ formatDuration(getTotals(report.items).charge_time) }}</span>
          <span class="total-card__label">总充电时长</span>
        </div>
        <div class="total-card total-card--highlight">
          <span class="total-card__val">{{ formatMoney(getTotals(report.items).total_fee) }}</span>
          <span class="total-card__label">总费用</span>
        </div>
      </div>

      <AppEmpty v-if="!report.items?.length" title="暂无数据" description="所选时段内没有充电记录" />

      <div v-else class="report-table-wrap">
        <table class="report-table">
          <thead>
            <tr>
              <th>充电桩</th>
              <th>充电次数</th>
              <th>充电量</th>
              <th>充电时长</th>
              <th>充电费</th>
              <th>服务费</th>
              <th>总费用</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in report.items" :key="item.pile_id">
              <td class="pile-cell">{{ item.pile_no }}</td>
              <td>{{ item.total_charge_num }}</td>
              <td>{{ formatKwh(item.total_charge_capacity) }}</td>
              <td>{{ formatDuration(item.total_charge_time) }}</td>
              <td>{{ formatMoney(item.total_charge_fee) }}</td>
              <td>{{ formatMoney(item.total_service_fee) }}</td>
              <td class="fee-cell">{{ formatMoney(item.total_fee) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>
  </div>
</template>

<style scoped>
.report-controls {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 28px;
  flex-wrap: wrap;
}

.report-filters {
  display: flex;
  align-items: flex-end;
  gap: 12px;
}

.totals-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 28px;
}

.total-card {
  background: var(--color-bg-elevated);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-lg);
  padding: 20px;
  text-align: center;
}

.total-card--highlight {
  border-color: var(--color-primary);
  background: var(--color-primary-muted);
}

.total-card__val {
  display: block;
  font-size: 1.375rem;
  font-weight: 800;
  color: var(--color-text);
  margin-bottom: 4px;
}

.total-card--highlight .total-card__val {
  color: var(--color-primary);
}

.total-card__label {
  font-size: 0.75rem;
  color: var(--color-text-muted);
}

.report-table-wrap {
  background: var(--color-bg-elevated);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-lg);
  overflow: hidden;
}

.report-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.875rem;
}

.report-table th {
  text-align: left;
  padding: 14px 18px;
  font-size: 0.75rem;
  font-weight: 700;
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.03em;
  background: var(--color-surface-muted);
  border-bottom: 1px solid var(--color-border);
}

.report-table td {
  padding: 14px 18px;
  border-bottom: 1px solid var(--color-border-light);
}

.report-table tbody tr {
  transition: background var(--transition-fast);
}

.report-table tbody tr:hover {
  background: var(--color-primary-muted);
}

.pile-cell {
  font-weight: 800;
  color: var(--color-primary);
}

.fee-cell {
  font-weight: 700;
  color: var(--color-primary);
}

@media (max-width: 768px) {
  .report-controls {
    flex-direction: column;
    align-items: stretch;
  }

  .report-filters {
    flex-direction: column;
    align-items: stretch;
  }

  .report-filters :deep(.btn) {
    width: 100%;
  }

  .totals-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .report-table-wrap {
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
  }

  .report-table {
    min-width: 640px;
  }
}
</style>

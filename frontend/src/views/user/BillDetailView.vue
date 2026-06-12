<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getBillDetail, payBill } from '@/api/bill'
import { useToast } from '@/composables/useToast'
import { PAY_STATUS } from '@/utils/constants'
import { formatMoney, formatKwh, formatDuration, formatDateTime } from '@/utils/format'
import AppCard from '@/components/ui/AppCard.vue'
import AppBadge from '@/components/ui/AppBadge.vue'
import AppButton from '@/components/ui/AppButton.vue'
import AppLoading from '@/components/ui/AppLoading.vue'

const route = useRoute()
const router = useRouter()
const toast = useToast()

const loading = ref(true)
const paying = ref(false)
const bill = ref(null)

async function fetchDetail() {
  loading.value = true
  try {
    bill.value = await getBillDetail(route.params.id)
  } catch (e) {
    toast.error(e.message)
    router.push('/user/bills')
  } finally {
    loading.value = false
  }
}

async function handlePay() {
  paying.value = true
  try {
    await payBill(bill.value.bill_id)
    toast.success('支付成功')
    await fetchDetail()
  } catch (e) {
    toast.error(e.message)
  } finally {
    paying.value = false
  }
}

onMounted(fetchDetail)
</script>

<template>
  <div class="page">
    <div class="page-header">
      <button class="back-btn" @click="router.push('/user/bills')">← 返回账单列表</button>
      <h1 class="page-title">账单详情</h1>
    </div>

    <AppLoading v-if="loading" />

    <template v-else-if="bill">
      <div class="bill-summary">
        <div class="summary-main">
          <span class="summary-no">{{ bill.bill_no }}</span>
          <AppBadge :color="PAY_STATUS[bill.pay_status]?.color" dot>
            {{ PAY_STATUS[bill.pay_status]?.label }}
          </AppBadge>
        </div>
        <div class="summary-total">
          <span class="summary-total__label">总费用</span>
          <span class="summary-total__value">{{ formatMoney(bill.total_fee) }}</span>
        </div>
        <div class="summary-grid">
          <div class="summary-item">
            <span class="summary-item__label">充电量</span>
            <span class="summary-item__val">{{ formatKwh(bill.total_charge_amount) }}</span>
          </div>
          <div class="summary-item">
            <span class="summary-item__label">充电时长</span>
            <span class="summary-item__val">{{ formatDuration(bill.total_charge_duration) }}</span>
          </div>
          <div class="summary-item">
            <span class="summary-item__label">充电费</span>
            <span class="summary-item__val">{{ formatMoney(bill.total_charge_fee) }}</span>
          </div>
          <div class="summary-item">
            <span class="summary-item__label">服务费</span>
            <span class="summary-item__val">{{ formatMoney(bill.total_service_fee) }}</span>
          </div>
        </div>
        <AppButton
          v-if="bill.pay_status === 'unpaid'"
          variant="accent"
          :loading="paying"
          @click="handlePay"
        >
          立即支付
        </AppButton>
      </div>

      <AppCard title="充电详单" class="details-card">
        <div class="detail-table">
          <div
            v-for="d in bill.details"
            :key="d.detail_no"
            class="detail-row"
          >
            <div class="detail-row__header">
              <span class="detail-no">{{ d.detail_no }}</span>
              <span class="detail-pile">桩 {{ d.pile_no }}</span>
            </div>
            <div class="detail-row__grid">
              <div class="detail-cell">
                <span class="detail-cell__label">充电量</span>
                <span>{{ formatKwh(d.charge_amount) }}</span>
              </div>
              <div class="detail-cell">
                <span class="detail-cell__label">时长</span>
                <span>{{ formatDuration(d.charge_duration) }}</span>
              </div>
              <div class="detail-cell">
                <span class="detail-cell__label">充电费</span>
                <span>{{ formatMoney(d.charge_fee) }}</span>
              </div>
              <div class="detail-cell">
                <span class="detail-cell__label">服务费</span>
                <span>{{ formatMoney(d.service_fee) }}</span>
              </div>
              <div class="detail-cell">
                <span class="detail-cell__label">总费用</span>
                <span class="detail-fee">{{ formatMoney(d.total_fee) }}</span>
              </div>
              <div class="detail-cell detail-cell--wide">
                <span class="detail-cell__label">时段</span>
                <span>{{ formatDateTime(d.start_time) }} — {{ formatDateTime(d.end_time) }}</span>
              </div>
            </div>
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

.bill-summary {
  background: var(--color-bg-elevated);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-xl);
  padding: 28px 32px;
  margin-bottom: 24px;
  box-shadow: var(--shadow-sm);
}

.summary-main {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
}

.summary-no {
  font-family: var(--font-mono);
  font-weight: 700;
  font-size: 1rem;
}

.summary-total {
  margin-bottom: 24px;
}

.summary-total__label {
  display: block;
  font-size: 0.8125rem;
  color: var(--color-text-muted);
  margin-bottom: 4px;
}

.summary-total__value {
  font-size: 2rem;
  font-weight: 900;
  color: var(--color-primary);
  letter-spacing: -0.02em;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 24px;
  padding: 16px 0;
  border-top: 1px solid var(--color-border-light);
  border-bottom: 1px solid var(--color-border-light);
}

.summary-item__label {
  display: block;
  font-size: 0.75rem;
  color: var(--color-text-muted);
  margin-bottom: 4px;
}

.summary-item__val {
  font-weight: 700;
  font-size: 0.9375rem;
}

.details-card {
  margin-top: 0;
}

.detail-row {
  padding: 18px 0;
  border-bottom: 1px solid var(--color-border-light);
}

.detail-row:last-child {
  border-bottom: none;
}

.detail-row__header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 12px;
}

.detail-no {
  font-family: var(--font-mono);
  font-weight: 600;
  font-size: 0.875rem;
}

.detail-pile {
  font-weight: 700;
  color: var(--color-accent);
}

.detail-row__grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
}

.detail-cell__label {
  display: block;
  font-size: 0.6875rem;
  color: var(--color-text-muted);
  margin-bottom: 2px;
}

.detail-cell--wide {
  grid-column: 1 / -1;
}

.detail-fee {
  font-weight: 700;
  color: var(--color-primary);
}

@media (max-width: 768px) {
  .bill-summary {
    padding: 20px 18px;
  }

  .summary-total__value {
    font-size: 1.625rem;
  }

  .summary-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .detail-row__grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .bill-summary :deep(.btn) {
    width: 100%;
  }
}
</style>

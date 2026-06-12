<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getBillList } from '@/api/bill'
import { useToast } from '@/composables/useToast'
import { PAY_STATUS } from '@/utils/constants'
import { formatMoney, formatDateTime } from '@/utils/format'
import AppCard from '@/components/ui/AppCard.vue'
import AppBadge from '@/components/ui/AppBadge.vue'
import AppLoading from '@/components/ui/AppLoading.vue'
import AppEmpty from '@/components/ui/AppEmpty.vue'

const router = useRouter()
const toast = useToast()

const loading = ref(true)
const bills = ref([])

async function fetchBills() {
  loading.value = true
  try {
    bills.value = await getBillList()
  } catch (e) {
    toast.error(e.message)
  } finally {
    loading.value = false
  }
}

function goDetail(billId) {
  router.push(`/user/bills/${billId}`)
}

onMounted(fetchBills)
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h1 class="page-title">我的账单</h1>
      <p class="page-desc">查看充电详单与费用明细</p>
    </div>

    <AppLoading v-if="loading" />

    <AppEmpty
      v-else-if="bills.length === 0"
      title="暂无账单"
      description="完成一次充电后，账单将显示在这里"
    />

    <div v-else class="bill-list">
      <TransitionGroup name="stagger">
        <div
          v-for="(bill, i) in bills"
          :key="bill.bill_id"
          class="bill-item"
          :style="{ transitionDelay: `${i * 60}ms` }"
          @click="goDetail(bill.bill_id)"
        >
          <div class="bill-item__left">
            <span class="bill-item__no">{{ bill.bill_no }}</span>
            <span class="bill-item__date">{{ bill.bill_date }}</span>
          </div>
          <div class="bill-item__right">
            <span class="bill-item__fee">{{ formatMoney(bill.total_fee) }}</span>
            <AppBadge :color="PAY_STATUS[bill.pay_status]?.color || 'muted'">
              {{ PAY_STATUS[bill.pay_status]?.label || bill.pay_status }}
            </AppBadge>
          </div>
          <span class="bill-item__time">{{ formatDateTime(bill.created_at) }}</span>
        </div>
      </TransitionGroup>
    </div>
  </div>
</template>

<style scoped>
.bill-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.bill-item {
  display: grid;
  grid-template-columns: 1fr auto;
  grid-template-rows: auto auto;
  gap: 4px 16px;
  padding: 18px 22px;
  background: var(--color-bg-elevated);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-lg);
  cursor: pointer;
  transition: all var(--transition-normal);
}

.bill-item:hover {
  box-shadow: var(--shadow-md);
  transform: translateX(4px);
  border-color: var(--color-primary);
}

.bill-item__no {
  font-weight: 700;
  font-size: 0.9375rem;
  font-family: var(--font-mono);
}

.bill-item__date {
  margin-left: 12px;
  font-size: 0.8125rem;
  color: var(--color-text-muted);
}

.bill-item__right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.bill-item__fee {
  font-size: 1.125rem;
  font-weight: 800;
  color: var(--color-primary);
  font-variant-numeric: tabular-nums;
}

.bill-item__time {
  grid-column: 1 / -1;
  font-size: 0.75rem;
  color: var(--color-text-muted);
}

@media (max-width: 640px) {
  .bill-item {
    padding: 14px 16px;
    gap: 8px 12px;
  }

  .bill-item__left {
    grid-column: 1 / -1;
  }

  .bill-item__date {
    display: block;
    margin-left: 0;
    margin-top: 2px;
  }

  .bill-item__right {
    grid-column: 1 / -1;
    justify-content: space-between;
  }

  .bill-item:hover {
    transform: none;
  }
}
</style>

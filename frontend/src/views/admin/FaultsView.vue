<script setup>
import { ref, onMounted } from 'vue'
import { getFaultList, recoverFault } from '@/api/admin'
import { useToast } from '@/composables/useToast'
import { formatDateTime } from '@/utils/format'
import AppCard from '@/components/ui/AppCard.vue'
import AppBadge from '@/components/ui/AppBadge.vue'
import AppButton from '@/components/ui/AppButton.vue'
import AppLoading from '@/components/ui/AppLoading.vue'
import AppEmpty from '@/components/ui/AppEmpty.vue'

const toast = useToast()

const loading = ref(true)
const recovering = ref(null)
const faults = ref([])

async function fetchFaults() {
  loading.value = true
  try {
    faults.value = await getFaultList()
  } catch (e) {
    toast.error(e.message)
  } finally {
    loading.value = false
  }
}

async function handleRecover(pileId) {
  recovering.value = pileId
  try {
    await recoverFault(pileId)
    toast.success('故障已恢复')
    await fetchFaults()
  } catch (e) {
    toast.error(e.message)
  } finally {
    recovering.value = null
  }
}

onMounted(fetchFaults)
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h1 class="page-title">故障管理</h1>
      <p class="page-desc">查看故障记录，恢复故障充电桩</p>
    </div>

    <AppLoading v-if="loading" />

    <AppEmpty
      v-else-if="faults.length === 0"
      title="暂无故障记录"
      description="系统运行正常，没有故障上报"
    />

    <div v-else class="fault-list">
      <AppCard
        v-for="fault in faults"
        :key="fault.fault_id"
        class="fault-card"
      >
        <div class="fault-card__content">
          <div class="fault-card__main">
            <div class="fault-card__header">
              <span class="fault-pile">{{ fault.pile_no }}</span>
              <AppBadge :color="fault.fault_status === 'open' ? 'danger' : 'success'" dot>
                {{ fault.fault_status === 'open' ? '未恢复' : '已恢复' }}
              </AppBadge>
            </div>
            <p class="fault-desc">{{ fault.description || fault.fault_type }}</p>
            <div class="fault-times">
              <span>发生：{{ formatDateTime(fault.occurred_at) }}</span>
              <span v-if="fault.recovered_at">
                恢复：{{ formatDateTime(fault.recovered_at) }}
              </span>
            </div>
          </div>
          <AppButton
            v-if="fault.fault_status === 'open'"
            variant="accent"
            size="sm"
            :loading="recovering === fault.pile_id"
            @click="handleRecover(fault.pile_id)"
          >
            恢复故障
          </AppButton>
        </div>
      </AppCard>
    </div>
  </div>
</template>

<style scoped>
.fault-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.fault-card__content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 20px;
}

.fault-card__header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}

.fault-pile {
  font-size: 1.125rem;
  font-weight: 800;
  color: var(--color-danger);
}

.fault-desc {
  font-size: 0.875rem;
  color: var(--color-text-secondary);
  margin-bottom: 8px;
}

.fault-times {
  display: flex;
  gap: 20px;
  font-size: 0.75rem;
  color: var(--color-text-muted);
  flex-wrap: wrap;
}

@media (max-width: 640px) {
  .fault-card__content {
    flex-direction: column;
    align-items: stretch;
  }

  .fault-card__content :deep(.btn) {
    width: 100%;
  }
}
</style>

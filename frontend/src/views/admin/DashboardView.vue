<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import {
  getPileStatus,
  powerOnPile,
  startPile,
  powerOffPile,
  reportFault,
} from '@/api/admin'
import { useToast } from '@/composables/useToast'
import PileStatusCard from '@/components/PileStatusCard.vue'
import AppLoading from '@/components/ui/AppLoading.vue'
import AppButton from '@/components/ui/AppButton.vue'
import AppModal from '@/components/ui/AppModal.vue'

const router = useRouter()
const toast = useToast()

const loading = ref(true)
const actionLoading = ref(false)
const piles = ref([])
const selectedPile = ref(null)
const showActionModal = ref(false)

let pollTimer = null

async function fetchPiles() {
  try {
    piles.value = await getPileStatus()
  } catch (e) {
    toast.error(e.message)
  } finally {
    loading.value = false
  }
}

function selectPile(pile) {
  selectedPile.value = pile
  showActionModal.value = true
}

function goQueue(pile) {
  router.push(`/admin/piles/${pile.pile_id}`)
}

async function handleAction(action) {
  if (!selectedPile.value) return
  actionLoading.value = true
  try {
    const id = selectedPile.value.pile_id
    switch (action) {
      case 'poweron':
        await powerOnPile(id)
        toast.success('充电桩已上电')
        break
      case 'start':
        await startPile(id)
        toast.success('充电桩已投入运行')
        break
      case 'poweroff':
        await powerOffPile(id)
        toast.success('充电桩已关闭')
        break
      case 'fault':
        await reportFault(id)
        toast.success('故障已上报，系统正在重新调度')
        break
    }
    showActionModal.value = false
    await fetchPiles()
  } catch (e) {
    toast.error(e.message)
  } finally {
    actionLoading.value = false
  }
}

onMounted(() => {
  fetchPiles()
  pollTimer = setInterval(fetchPiles, 5000)
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})
</script>

<template>
  <div class="page">
    <div class="page-header">
      <h1 class="page-title">充电桩监控</h1>
      <p class="page-desc">查看所有充电桩运行状态，管理启停与故障</p>
    </div>

    <AppLoading v-if="loading" text="加载充电桩状态…" />

    <div v-else class="grid-auto">
      <PileStatusCard
        v-for="pile in piles"
        :key="pile.pile_id"
        :pile="pile"
        @click="selectPile"
      />
    </div>

    <!-- 操作弹窗 -->
    <AppModal
      :show="showActionModal"
      :title="`充电桩 ${selectedPile?.pile_no || ''}`"
      @close="showActionModal = false"
    >
      <div v-if="selectedPile" class="action-panel">
        <p class="action-status">
          当前状态：<strong>{{ selectedPile.status }}</strong>
          · 队列 {{ selectedPile.queue_used }}/{{ selectedPile.queue_total }}
        </p>
        <div class="action-buttons">
          <AppButton
            v-if="selectedPile.status === 'off'"
            :loading="actionLoading"
            @click="handleAction('poweron')"
          >
            上电启动
          </AppButton>
          <AppButton
            v-if="selectedPile.status === 'standby'"
            variant="accent"
            :loading="actionLoading"
            @click="handleAction('start')"
          >
            投入运行
          </AppButton>
          <AppButton
            v-if="['standby', 'available', 'charging'].includes(selectedPile.status)"
            variant="secondary"
            :loading="actionLoading"
            @click="handleAction('poweroff')"
          >
            关闭充电桩
          </AppButton>
          <AppButton
            v-if="selectedPile.status !== 'fault' && selectedPile.status !== 'off'"
            variant="danger"
            :loading="actionLoading"
            @click="handleAction('fault')"
          >
            上报故障
          </AppButton>
          <AppButton variant="ghost" @click="goQueue(selectedPile); showActionModal = false">
            查看队列详情 →
          </AppButton>
        </div>
      </div>
    </AppModal>
  </div>
</template>

<style scoped>
.action-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.action-status {
  font-size: 0.875rem;
  color: var(--color-text-secondary);
}

.action-buttons {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
</style>

<script setup>
import AppBadge from '@/components/ui/AppBadge.vue'
import { PILE_STATUS } from '@/utils/constants'
import { formatKwh, formatDuration } from '@/utils/format'

defineProps({
  pile: { type: Object, required: true },
  selected: { type: Boolean, default: false },
})

const emit = defineEmits(['click'])
</script>

<template>
  <div
    class="pile-card"
    :class="[`pile-card--${pile.status}`, { 'pile-card--selected': selected }]"
    @click="emit('click', pile)"
  >
    <div class="pile-card__top">
      <span class="pile-card__no">{{ pile.pile_no }}</span>
      <AppBadge :color="PILE_STATUS[pile.status]?.color || 'muted'" dot>
        {{ PILE_STATUS[pile.status]?.label || pile.status }}
      </AppBadge>
    </div>

    <div class="pile-card__mode" :class="pile.mode === 'F' ? 'mode-fast' : 'mode-slow'">
      {{ pile.mode_label }} · {{ pile.power }} 度/h
    </div>

    <div class="pile-card__queue">
      <div class="queue-bar">
        <div
          class="queue-bar__fill"
          :style="{ width: `${(pile.queue_used / pile.queue_total) * 100}%` }"
        />
      </div>
      <span class="queue-text">占用 {{ pile.queue_used }}/{{ pile.queue_total }}（含充电中）</span>
    </div>

    <div v-if="pile.current_car" class="pile-card__current">
      <span class="current-dot" />
      {{ pile.current_car.car_id }} · 已充 {{ formatKwh(pile.current_car.charged_amount) }}
    </div>

    <div class="pile-card__stats">
      <div class="stat">
        <span class="stat__val">{{ pile.total_charge_num }}</span>
        <span class="stat__label">充电次数</span>
      </div>
      <div class="stat">
        <span class="stat__val">{{ formatKwh(pile.total_charge_capacity) }}</span>
        <span class="stat__label">累计电量</span>
      </div>
      <div class="stat">
        <span class="stat__val">{{ formatDuration(pile.total_charge_time) }}</span>
        <span class="stat__label">累计时长</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.pile-card {
  background: var(--color-bg-elevated);
  border: 1.5px solid var(--color-border-light);
  border-radius: var(--radius-lg);
  padding: 20px;
  cursor: pointer;
  transition: all var(--transition-normal);
}

.pile-card:hover {
  box-shadow: var(--shadow-md);
  transform: translateY(-2px);
}

.pile-card--selected {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-muted);
}

.pile-card--charging {
  border-color: rgba(196, 92, 38, 0.3);
}

.pile-card--fault {
  border-color: rgba(184, 58, 58, 0.3);
  opacity: 0.85;
}

.pile-card__top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.pile-card__no {
  font-size: 1.25rem;
  font-weight: 800;
  letter-spacing: -0.02em;
}

.pile-card__mode {
  font-size: 0.8125rem;
  font-weight: 600;
  margin-bottom: 14px;
}

.mode-fast { color: var(--color-fast); }
.mode-slow { color: var(--color-slow); }

.pile-card__queue {
  margin-bottom: 12px;
}

.queue-bar {
  height: 4px;
  background: var(--color-surface-muted);
  border-radius: 100px;
  overflow: hidden;
  margin-bottom: 4px;
}

.queue-bar__fill {
  height: 100%;
  background: var(--color-primary);
  border-radius: 100px;
  transition: width 0.5s ease;
}

.queue-text {
  font-size: 0.75rem;
  color: var(--color-text-muted);
}

.pile-card__current {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.8125rem;
  color: var(--color-accent);
  font-weight: 600;
  margin-bottom: 14px;
  padding: 8px 12px;
  background: var(--color-accent-muted);
  border-radius: var(--radius-sm);
}

.current-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color-accent);
  animation: charge-pulse 1.5s ease infinite;
}

.pile-card__stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  padding-top: 14px;
  border-top: 1px solid var(--color-border-light);
}

.stat {
  text-align: center;
}

.stat__val {
  display: block;
  font-size: 0.8125rem;
  font-weight: 700;
  color: var(--color-text);
}

.stat__label {
  font-size: 0.6875rem;
  color: var(--color-text-muted);
}
</style>

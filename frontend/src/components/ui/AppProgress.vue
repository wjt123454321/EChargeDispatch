<script setup>
import { computed } from 'vue'

const props = defineProps({
  value: { type: Number, default: 0 },
  max: { type: Number, default: 100 },
  label: { type: String, default: '' },
  animated: { type: Boolean, default: false },
  color: { type: String, default: 'primary' },
})

const percent = computed(() => {
  if (props.max <= 0) return 0
  return Math.min(100, Math.round((props.value / props.max) * 100))
})
</script>

<template>
  <div class="progress">
    <div v-if="label || $slots.label" class="progress__header">
      <slot name="label">
        <span class="progress__label">{{ label }}</span>
      </slot>
      <span class="progress__percent">{{ percent }}%</span>
    </div>
    <div class="progress__track">
      <div
        class="progress__bar"
        :class="[`progress__bar--${color}`, { 'progress__bar--animated': animated }]"
        :style="{ width: `${percent}%` }"
      />
    </div>
  </div>
</template>

<style scoped>
.progress__header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
  font-size: 0.8125rem;
}

.progress__label {
  color: var(--color-text-secondary);
  font-weight: 500;
}

.progress__percent {
  font-weight: 700;
  color: var(--color-primary);
  font-variant-numeric: tabular-nums;
}

.progress__track {
  height: 8px;
  background: var(--color-surface-muted);
  border-radius: 100px;
  overflow: hidden;
}

.progress__bar {
  height: 100%;
  border-radius: 100px;
  transition: width 0.6s cubic-bezier(0.4, 0, 0.2, 1);
}

.progress__bar--primary { background: var(--color-primary); }
.progress__bar--accent { background: var(--color-accent); }
.progress__bar--success { background: var(--color-success); }

.progress__bar--animated {
  background-size: 200% 100%;
  background-image: linear-gradient(
    90deg,
    var(--color-primary) 0%,
    var(--color-primary-light) 50%,
    var(--color-primary) 100%
  );
  animation: shimmer 2s linear infinite;
}
</style>

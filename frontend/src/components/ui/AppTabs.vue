<script setup>
defineProps({
  tabs: { type: Array, required: true }, // { key, label }
  modelValue: { type: String, required: true },
})

const emit = defineEmits(['update:modelValue'])
</script>

<template>
  <div class="tabs">
    <button
      v-for="tab in tabs"
      :key="tab.key"
      class="tabs__item"
      :class="{ 'tabs__item--active': modelValue === tab.key }"
      @click="emit('update:modelValue', tab.key)"
    >
      {{ tab.label }}
    </button>
  </div>
</template>

<style scoped>
.tabs {
  display: inline-flex;
  background: var(--color-surface-muted);
  border-radius: var(--radius-md);
  padding: 4px;
  gap: 2px;
}

.tabs__item {
  padding: 8px 18px;
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--color-text-secondary);
  border-radius: var(--radius-sm);
  transition: all var(--transition-fast);
}

.tabs__item:hover:not(.tabs__item--active) {
  color: var(--color-text);
}

.tabs__item--active {
  background: var(--color-bg-elevated);
  color: var(--color-primary);
  box-shadow: var(--shadow-sm);
}
</style>

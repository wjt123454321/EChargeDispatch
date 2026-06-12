<script setup>
defineProps({
  title: { type: String, default: '暂无数据' },
  description: { type: String, default: '' },
})
</script>

<template>
  <div class="empty">
    <div class="empty__icon">
      <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
        <rect x="8" y="12" width="32" height="28" rx="4" stroke="currentColor" stroke-width="2"/>
        <path d="M16 20h16M16 26h10" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
      </svg>
    </div>
    <p class="empty__title">{{ title }}</p>
    <p v-if="description" class="empty__desc">{{ description }}</p>
    <slot />
  </div>
</template>

<style scoped>
.empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 48px 24px;
  text-align: center;
}

.empty__icon {
  color: var(--color-text-muted);
  opacity: 0.5;
  margin-bottom: 16px;
}

.empty__title {
  font-size: 0.9375rem;
  font-weight: 600;
  color: var(--color-text-secondary);
}

.empty__desc {
  margin-top: 6px;
  font-size: 0.8125rem;
  color: var(--color-text-muted);
  max-width: 280px;
}
</style>

<script setup>
defineProps({
  text: { type: String, default: '加载中…' },
  size: { type: String, default: 'md' },
})
</script>

<template>
  <div class="loading" :class="`loading--${size}`">
    <div class="loading__ring" />
    <p v-if="text" class="loading__text">{{ text }}</p>
  </div>
</template>

<style scoped>
.loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 14px;
  padding: 40px;
}

.loading__ring {
  border-radius: 50%;
  border: 3px solid var(--color-border);
  border-top-color: var(--color-primary);
  animation: spin 0.8s linear infinite;
}

.loading--sm .loading__ring { width: 24px; height: 24px; }
.loading--md .loading__ring { width: 36px; height: 36px; }
.loading--lg .loading__ring { width: 48px; height: 48px; }

.loading__text {
  font-size: 0.875rem;
  color: var(--color-text-muted);
}
</style>

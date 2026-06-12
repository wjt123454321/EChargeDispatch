<script setup>
defineProps({
  title: { type: String, default: '' },
  padding: { type: Boolean, default: true },
  hoverable: { type: Boolean, default: false },
})
</script>

<template>
  <div class="card" :class="{ 'card--hoverable': hoverable, 'card--no-padding': !padding }">
    <div v-if="title || $slots.header" class="card__header">
      <slot name="header">
        <h3 class="card__title">{{ title }}</h3>
      </slot>
      <slot name="actions" />
    </div>
    <div class="card__body">
      <slot />
    </div>
  </div>
</template>

<style scoped>
.card {
  background: var(--color-bg-elevated);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  transition: box-shadow var(--transition-normal), transform var(--transition-normal);
}

.card--hoverable:hover {
  box-shadow: var(--shadow-md);
  transform: translateY(-2px);
}

.card--no-padding .card__body {
  padding: 0;
}

.card__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 22px 0;
}

.card__title {
  font-size: 0.9375rem;
  font-weight: 700;
  color: var(--color-text);
}

.card__body {
  padding: 18px 22px 22px;
}

.card__header + .card__body {
  padding-top: 14px;
}
</style>

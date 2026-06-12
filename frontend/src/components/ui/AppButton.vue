<script setup>
defineProps({
  variant: { type: String, default: 'primary' }, // primary | secondary | ghost | danger | accent
  size: { type: String, default: 'md' }, // sm | md | lg
  loading: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
  block: { type: Boolean, default: false },
  type: { type: String, default: 'button' },
})
</script>

<template>
  <button
    :type="type"
    class="btn"
    :class="[`btn--${variant}`, `btn--${size}`, { 'btn--block': block, 'btn--loading': loading }]"
    :disabled="disabled || loading"
  >
    <span v-if="loading" class="btn__spinner" />
    <span class="btn__content" :class="{ 'btn__content--hidden': loading }">
      <slot />
    </span>
  </button>
</template>

<style scoped>
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  font-weight: 600;
  border-radius: var(--radius-md);
  transition: all var(--transition-fast);
  position: relative;
  white-space: nowrap;
}

.btn:active:not(:disabled) {
  transform: scale(0.97);
}

.btn--sm { padding: 6px 14px; font-size: 0.8125rem; }
.btn--md { padding: 10px 20px; font-size: 0.875rem; }
.btn--lg { padding: 13px 28px; font-size: 0.9375rem; }
.btn--block { width: 100%; }

.btn--primary {
  background: var(--color-primary);
  color: #fff;
}
.btn--primary:hover:not(:disabled) {
  background: var(--color-primary-light);
  box-shadow: var(--shadow-sm);
}

.btn--accent {
  background: var(--color-accent);
  color: #fff;
}
.btn--accent:hover:not(:disabled) {
  background: var(--color-accent-light);
}

.btn--secondary {
  background: var(--color-surface-muted);
  color: var(--color-text);
  border: 1px solid var(--color-border);
}
.btn--secondary:hover:not(:disabled) {
  background: var(--color-border-light);
}

.btn--ghost {
  background: transparent;
  color: var(--color-text-secondary);
}
.btn--ghost:hover:not(:disabled) {
  background: var(--color-primary-muted);
  color: var(--color-primary);
}

.btn--danger {
  background: var(--color-danger);
  color: #fff;
}
.btn--danger:hover:not(:disabled) {
  opacity: 0.9;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn__spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.7s linear infinite;
  position: absolute;
}

.btn--secondary .btn__spinner,
.btn--ghost .btn__spinner {
  border-color: rgba(0, 0, 0, 0.1);
  border-top-color: var(--color-primary);
}

.btn__content--hidden {
  visibility: hidden;
}
</style>

<script setup>
defineProps({
  color: { type: String, default: 'muted' }, // success | warning | danger | info | accent | muted
  dot: { type: Boolean, default: false },
})
</script>

<template>
  <span class="badge" :class="[`badge--${color}`, { 'badge--dot': dot }]">
    <slot />
  </span>
</template>

<style scoped>
.badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 3px 10px;
  font-size: 0.75rem;
  font-weight: 600;
  border-radius: 100px;
  line-height: 1.4;
}

.badge--success { background: rgba(61, 122, 92, 0.12); color: var(--color-success); }
.badge--warning { background: rgba(184, 134, 11, 0.12); color: var(--color-warning); }
.badge--danger { background: rgba(184, 58, 58, 0.12); color: var(--color-danger); }
.badge--info { background: rgba(74, 111, 165, 0.12); color: var(--color-info); }
.badge--accent { background: var(--color-accent-muted); color: var(--color-accent); }
.badge--muted { background: var(--color-surface-muted); color: var(--color-text-muted); }

.badge--dot::before {
  content: '';
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: currentColor;
}
</style>

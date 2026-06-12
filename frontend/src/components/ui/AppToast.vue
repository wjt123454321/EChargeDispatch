<script setup>
import { useToast } from '@/composables/useToast'

const { toasts, dismiss } = useToast()
</script>

<template>
  <Teleport to="body">
    <div class="toast-container">
      <TransitionGroup name="toast">
        <div
          v-for="t in toasts"
          :key="t.id"
          class="toast"
          :class="`toast--${t.type}`"
          @click="dismiss(t.id)"
        >
          {{ t.message }}
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<style scoped>
.toast-container {
  position: fixed;
  top: 20px;
  right: 20px;
  z-index: 2000;
  display: flex;
  flex-direction: column;
  gap: 10px;
  pointer-events: none;
}

.toast {
  pointer-events: auto;
  padding: 12px 20px;
  border-radius: var(--radius-md);
  font-size: 0.875rem;
  font-weight: 500;
  box-shadow: var(--shadow-md);
  cursor: pointer;
  max-width: 360px;
}

.toast--success { background: var(--color-success); color: #fff; }
.toast--error { background: var(--color-danger); color: #fff; }
.toast--warning { background: var(--color-warning); color: #fff; }
.toast--info { background: var(--color-text); color: #fff; }

.toast-enter-active,
.toast-leave-active {
  transition: all 0.3s ease;
}

.toast-enter-from {
  opacity: 0;
  transform: translateX(40px);
}

.toast-leave-to {
  opacity: 0;
  transform: translateX(40px);
}
</style>

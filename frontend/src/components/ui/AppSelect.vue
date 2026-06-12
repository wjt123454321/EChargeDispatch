<script setup>
defineProps({
  modelValue: { type: [String, Number], default: '' },
  label: { type: String, default: '' },
  options: { type: Array, default: () => [] }, // { value, label }
  disabled: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue'])
</script>

<template>
  <label class="select-wrap">
    <span v-if="label" class="select-label">{{ label }}</span>
    <select
      class="select-field"
      :value="modelValue"
      :disabled="disabled"
      @change="emit('update:modelValue', $event.target.value)"
    >
      <option v-for="opt in options" :key="opt.value" :value="opt.value">
        {{ opt.label }}
      </option>
    </select>
  </label>
</template>

<style scoped>
.select-wrap {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.select-label {
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--color-text-secondary);
}

.select-field {
  padding: 11px 14px;
  border: 1.5px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-bg-elevated);
  color: var(--color-text);
  cursor: pointer;
  transition: border-color var(--transition-fast);
}

.select-field:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-muted);
}

.select-field:disabled {
  background: var(--color-surface-muted);
  cursor: not-allowed;
}
</style>

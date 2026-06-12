<script setup>
defineProps({
  modelValue: { type: [String, Number], default: '' },
  label: { type: String, default: '' },
  type: { type: String, default: 'text' },
  placeholder: { type: String, default: '' },
  error: { type: String, default: '' },
  hint: { type: String, default: '' },
  disabled: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue'])
</script>

<template>
  <label class="input-wrap">
    <span v-if="label" class="input-label">{{ label }}</span>
    <input
      class="input-field"
      :class="{ 'input-field--error': error }"
      :type="type"
      :value="modelValue"
      :placeholder="placeholder"
      :disabled="disabled"
      @input="emit('update:modelValue', $event.target.value)"
    />
    <span v-if="error" class="input-error">{{ error }}</span>
    <span v-else-if="hint" class="input-hint">{{ hint }}</span>
  </label>
</template>

<style scoped>
.input-wrap {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.input-label {
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--color-text-secondary);
}

.input-field {
  padding: 11px 14px;
  border: 1.5px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-bg-elevated);
  color: var(--color-text);
  transition: border-color var(--transition-fast), box-shadow var(--transition-fast);
}

.input-field:focus {
  outline: none;
  border-color: var(--color-primary);
  box-shadow: 0 0 0 3px var(--color-primary-muted);
}

.input-field--error {
  border-color: var(--color-danger);
}

.input-field:disabled {
  background: var(--color-surface-muted);
  cursor: not-allowed;
}

.input-error {
  font-size: 0.75rem;
  color: var(--color-danger);
}

.input-hint {
  font-size: 0.75rem;
  color: var(--color-text-muted);
}
</style>

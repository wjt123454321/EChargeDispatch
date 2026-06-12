import { ref } from 'vue'

const toasts = ref([])
let seed = 0

export function useToast() {
  function show(message, type = 'info', duration = 3200) {
    const id = ++seed
    toasts.value.push({ id, message, type })
    setTimeout(() => dismiss(id), duration)
  }

  function dismiss(id) {
    const idx = toasts.value.findIndex((t) => t.id === id)
    if (idx >= 0) toasts.value.splice(idx, 1)
  }

  const success = (msg) => show(msg, 'success')
  const error = (msg) => show(msg, 'error', 4000)
  const warning = (msg) => show(msg, 'warning')
  const info = (msg) => show(msg, 'info')

  return { toasts, show, dismiss, success, error, warning, info }
}

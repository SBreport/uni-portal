import { ref, onUnmounted } from 'vue'

export function useAsyncAction() {
  const loading = ref(false)
  const message = ref('')
  const error = ref('')

  let callId = 0
  let clearTimer: ReturnType<typeof setTimeout> | null = null

  function clearPendingTimer() {
    if (clearTimer) {
      clearTimeout(clearTimer)
      clearTimer = null
    }
  }

  async function execute(
    fn: () => Promise<string | void>,
    successMsg?: string,
    clearAfter = 3000,
  ) {
    const thisCallId = ++callId
    clearPendingTimer()
    loading.value = true
    message.value = ''
    error.value = ''
    try {
      const result = await fn()
      if (thisCallId !== callId) return // stale call, discard
      message.value = result || successMsg || ''
      if (clearAfter > 0 && message.value) {
        clearTimer = setTimeout(() => {
          message.value = ''
          clearTimer = null
        }, clearAfter)
      }
    } catch (e: any) {
      if (thisCallId !== callId) return
      error.value = e.response?.data?.detail || e.message || '오류가 발생했습니다'
    } finally {
      if (thisCallId === callId) {
        loading.value = false
      }
    }
  }

  onUnmounted(() => {
    clearPendingTimer()
    callId++ // invalidate any in-flight calls
  })

  return { loading, message, error, execute }
}

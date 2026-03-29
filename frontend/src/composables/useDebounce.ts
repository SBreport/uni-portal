import { ref, watch, onUnmounted, type Ref } from 'vue'

export function useDebounce<T>(source: Ref<T>, delay = 300): Ref<T> {
  const debounced = ref(source.value) as Ref<T>
  let timer: ReturnType<typeof setTimeout> | null = null

  watch(source, (val) => {
    if (timer) clearTimeout(timer)
    timer = setTimeout(() => {
      debounced.value = val
      timer = null
    }, delay)
  })

  onUnmounted(() => {
    if (timer) clearTimeout(timer)
  })

  return debounced
}

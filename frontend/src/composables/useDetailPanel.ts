import { ref, type Ref } from 'vue'

export function useDetailPanel<T extends { id: number | string }>() {
  const selectedItem: Ref<T | null> = ref(null)
  const detailLoading = ref(false)
  const detailData: Ref<T | null> = ref(null)

  async function openDetail(
    item: T,
    fetchFn: (item: T) => Promise<T>,
    fallback?: T | null,
  ) {
    if (selectedItem.value?.id === item.id) return
    selectedItem.value = item
    detailLoading.value = true
    detailData.value = null
    try {
      detailData.value = await fetchFn(item)
    } catch {
      detailData.value = fallback ?? item
    } finally {
      detailLoading.value = false
    }
  }

  function closeDetail() {
    selectedItem.value = null
    detailData.value = null
  }

  return { selectedItem, detailLoading, detailData, openDetail, closeDetail }
}

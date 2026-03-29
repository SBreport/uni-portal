import { ref, type Ref } from 'vue'

export function useFileUpload<R = any>(uploadFn: (file: File) => Promise<R>) {
  const file = ref<File | null>(null)
  const uploading = ref(false)
  const result: Ref<R | null> = ref(null)
  const error = ref('')

  function onFileSelect(e: Event) {
    const target = e.target as HTMLInputElement
    file.value = target.files?.[0] || null
    result.value = null
    error.value = ''
  }

  async function doUpload() {
    if (!file.value) return
    uploading.value = true
    result.value = null
    error.value = ''
    try {
      result.value = await uploadFn(file.value)
    } catch (e: any) {
      error.value = e.response?.data?.detail || e.message || '업로드 실패'
    } finally {
      uploading.value = false
    }
  }

  function reset() {
    file.value = null
    result.value = null
    error.value = ''
  }

  return { file, uploading, result, error, onFileSelect, doUpload, reset }
}

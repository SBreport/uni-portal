import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { fetchBranches } from '@/api/branches'

export interface Branch {
  id: number
  name: string
  short_name: string
  region_name: string
  is_active: boolean
}

export const useBranchStore = defineStore('branches', () => {
  const branches = ref<Branch[]>([])
  const loaded = ref(false)
  const loading = ref(false)

  async function loadBranches(activeOnly = true) {
    if (loaded.value && !loading.value) return  // already loaded, skip
    if (loading.value) return  // in-progress, skip
    loading.value = true
    try {
      branches.value = await fetchBranches(activeOnly)
      loaded.value = true
    } finally {
      loading.value = false
    }
  }

  function getBranchById(id: number) {
    return branches.value.find(b => b.id === id)
  }

  function getBranchByName(name: string) {
    return branches.value.find(b => b.name === name || b.short_name === name)
  }

  // For backwards compatibility — some views need just {id, name} format
  const branchOptions = computed(() =>
    branches.value.map(b => ({ id: b.id, name: b.name }))
  )

  return { branches, loaded, loading, loadBranches, getBranchById, getBranchByName, branchOptions }
})

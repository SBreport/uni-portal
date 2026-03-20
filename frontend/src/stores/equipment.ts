import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as equipApi from '@/api/equipment'

export interface Branch { id: number; name: string }
export interface Category { id: number; name: string }
export interface EquipmentRow {
  id: number; 지점: string; 카테고리: string; 기기명: string
  수량: number; 사진: string; 비고: string
  [key: string]: any
}

export const useEquipmentStore = defineStore('equipment', () => {
  const branches = ref<Branch[]>([])
  const categories = ref<Category[]>([])
  const rows = ref<EquipmentRow[]>([])
  const loading = ref(false)

  // 필터
  const filterBranch = ref('')
  const filterCategory = ref('')
  const filterSearch = ref('')

  async function loadBranches() {
    const { data } = await equipApi.getBranches()
    branches.value = data
  }

  async function loadCategories() {
    const { data } = await equipApi.getCategories()
    categories.value = data
  }

  async function loadEquipment() {
    loading.value = true
    try {
      const params: Record<string, string> = {}
      if (filterBranch.value) params.branch = filterBranch.value
      if (filterCategory.value) params.category = filterCategory.value
      if (filterSearch.value) params.search = filterSearch.value
      const { data } = await equipApi.getEquipment(params)
      rows.value = data
    } finally {
      loading.value = false
    }
  }

  return {
    branches, categories, rows, loading,
    filterBranch, filterCategory, filterSearch,
    loadBranches, loadCategories, loadEquipment,
  }
})

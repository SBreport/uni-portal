import api from './client'

export interface CatalogItem {
  id: number
  item_type: 'device' | 'material' | 'method'
  category: string
  item_name: string
  sub_option: string | null
  display_name: string
  device_id: number | null
  description: string
  sort_order: number
  is_active: number
  created_at: string
  updated_at: string
}

export function getCatalog(params?: { item_type?: string; category?: string; search?: string }) {
  return api.get<CatalogItem[]>('/treatment-catalog', { params })
}

export function getCatalogItem(id: number) {
  return api.get<CatalogItem>(`/treatment-catalog/${id}`)
}

export function getCategories() {
  return api.get<string[]>('/treatment-catalog/categories')
}

export function createCatalogItem(data: Partial<CatalogItem>) {
  return api.post('/treatment-catalog', data)
}

export function updateCatalogItem(id: number, data: Partial<CatalogItem>) {
  return api.patch(`/treatment-catalog/${id}`, data)
}

export function deleteCatalogItem(id: number) {
  return api.delete(`/treatment-catalog/${id}`)
}

export function autoMatchDevices() {
  return api.post('/treatment-catalog/auto-match')
}

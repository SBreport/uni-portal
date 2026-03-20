import api from './client'

export const getEquipment = (params?: { branch?: string; category?: string; search?: string }) =>
  api.get('/equipment', { params })

export const getBranches = () => api.get('/equipment/branches')
export const getCategories = () => api.get('/equipment/categories')

export const updateEquipment = (id: number, data: Record<string, any>) =>
  api.patch(`/equipment/${id}`, data)

export const savePhotoChanges = (changes: { equipment_id: number; photo_status: boolean }[]) =>
  api.post('/equipment/photo-changes', changes)

// 장비 사전
export const getDeviceInfo = () => api.get('/equipment/device-info')
export const searchDeviceInfo = (q: string) => api.get('/equipment/device-info/search', { params: { q } })
export const matchDeviceInfo = (name: string) => api.get('/equipment/device-info/match', { params: { name } })
export const upsertDeviceInfo = (data: Record<string, any>) => api.post('/equipment/device-info', data)
export const deleteDeviceInfo = (name: string) => api.delete(`/equipment/device-info/${encodeURIComponent(name)}`)

// 동기화
export const syncFromSheets = () => api.post('/equipment/sync')
export const updateDeviceCounts = () => api.post('/equipment/device-info/update-counts')
export const syncDeviceJson = () => api.post('/equipment/device-info/sync-json')

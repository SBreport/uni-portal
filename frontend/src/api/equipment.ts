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

// 장비 컨텍스트 (시술정보 + 이벤트 연계)
export const getEquipmentContext = (branchName: string, equipmentName: string) =>
  api.get('/cafe/equipment-context', { params: { branch_name: branchName, equipment_name: equipmentName } })

// 이벤트 검색
export const searchEvents = (q: string) =>
  api.get('/events/search', { params: { q } })

// 동기화
export const syncFromSheets = () => api.post('/equipment/sync')
export const updateDeviceCounts = () => api.post('/equipment/device-info/update-counts')
export const syncDeviceJson = () => api.post('/equipment/device-info/sync-json')

// DB 파일 관리
export const uploadDb = (formData: FormData) =>
  api.post('/equipment/db-upload', formData, { headers: { 'Content-Type': 'multipart/form-data' }, timeout: 120000 })
export const downloadDb = () =>
  api.get('/equipment/db-download', { responseType: 'blob' })

import api from './client'

export const getPurposes = () => api.get('/encyclopedia/purposes')
export const getBodyParts = () => api.get('/encyclopedia/body-parts')
export const getEquipmentList = () => api.get('/encyclopedia/equipment-list')

export const getByPurpose = (purpose: string) =>
  api.get('/encyclopedia/by-purpose', { params: { purpose } })

export const getByBodyPart = (part: string) =>
  api.get('/encyclopedia/by-body-part', { params: { part } })

export const getByEquipment = (name: string) =>
  api.get('/encyclopedia/by-equipment', { params: { name } })

// 관리
export const refreshEncyclopedia = () =>
  api.post('/encyclopedia/refresh', {}, { timeout: 120000 })

export const getPending = () => api.get('/encyclopedia/pending')
export const getPendingSummary = () => api.get('/encyclopedia/pending/summary')
export const approvePending = (id: number) => api.post(`/encyclopedia/pending/${id}/approve`)
export const dismissPending = (id: number) => api.post(`/encyclopedia/pending/${id}/dismiss`)
export const approveAll = () => api.post('/encyclopedia/pending/approve-all')

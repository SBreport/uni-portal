import api from './client'

export async function getByBranch(branchId: number, periodId?: number) {
  const { data } = await api.get('/explorer/by-branch', {
    params: { branch_id: branchId, ...(periodId != null ? { period_id: periodId } : {}) },
  })
  return data
}
export async function getByCategory(categoryId: number, periodId?: number) {
  const { data } = await api.get('/explorer/by-category', {
    params: { category_id: categoryId, ...(periodId != null ? { period_id: periodId } : {}) },
  })
  return data
}
export async function getByDevice(deviceId: number, periodId?: number) {
  const { data } = await api.get('/explorer/by-device', {
    params: { device_id: deviceId, ...(periodId != null ? { period_id: periodId } : {}) },
  })
  return data
}
export async function search(q: string) {
  const { data } = await api.get('/explorer/search', { params: { q } })
  return data
}
export async function listDevices() {
  const { data } = await api.get('/explorer/devices')
  return data
}
export async function listPapers(params: {
  device_info_id?: number
  q?: string
  status?: string
} = {}) {
  const { data } = await api.get('/papers', { params })
  return data
}
export async function getDevicesSummary() {
  const { data } = await api.get('/papers/devices-summary')
  return data
}
export async function getCategorySummary(periodId?: number) {
  const { data } = await api.get('/explorer/category-summary', {
    params: periodId != null ? { period_id: periodId } : undefined,
  })
  return data
}
export async function getEncyclopediaByBodyPart(part: string) {
  const { data } = await api.get('/encyclopedia/by-body-part', { params: { part } })
  return data
}
export async function getEncyclopediaByPurpose(purpose: string) {
  const { data } = await api.get('/encyclopedia/by-purpose', { params: { purpose } })
  return data
}

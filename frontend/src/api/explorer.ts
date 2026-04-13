import api from './client'

export async function getByBranch(branchId: number) {
  const { data } = await api.get('/explorer/by-branch', { params: { branch_id: branchId } })
  return data
}
export async function getByCategory(categoryId: number) {
  const { data } = await api.get('/explorer/by-category', { params: { category_id: categoryId } })
  return data
}
export async function getByDevice(deviceId: number) {
  const { data } = await api.get('/explorer/by-device', { params: { device_id: deviceId } })
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
export async function getCategorySummary() {
  const { data } = await api.get('/explorer/category-summary')
  return data
}

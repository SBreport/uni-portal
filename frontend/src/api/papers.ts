import api from './client'

export const getPapers = (params?: {
  device_info_id?: number
  treatment_id?: number
  status?: string
  q?: string
}) => api.get('/papers', { params })

export const getPaper = (id: number) => api.get(`/papers/${id}`)

export const getPapersByDevice = (deviceInfoId: number) =>
  api.get(`/papers/by-device/${deviceInfoId}`)

export const getPapersByTreatment = (treatmentId: number) =>
  api.get(`/papers/by-treatment/${treatmentId}`)

export const updatePaper = (id: number, data: Record<string, any>) =>
  api.patch(`/papers/${id}`, data)

export const deletePaper = (id: number) =>
  api.delete(`/papers/${id}`)

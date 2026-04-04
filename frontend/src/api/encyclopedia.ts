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

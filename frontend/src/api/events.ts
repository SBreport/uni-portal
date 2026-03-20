import api from './client'

export const getEvents = () => api.get('/events')
export const getBranches = () => api.get('/events/branches')
export const getCategories = () => api.get('/events/categories')
export const getPeriods = () => api.get('/events/periods')

export const getPriceHistory = (branchName: string, eventName: string) =>
  api.get('/events/price-history', { params: { branch_name: branchName, event_name: eventName } })

export const searchEvents = (q: string, periodId?: number) =>
  api.get('/events/search', { params: { q, period_id: periodId } })

export const getSummary = () => api.get('/events/summary')

export const getTreatments = () => api.get('/events/treatments')
export const updateTreatment = (id: number, data: Record<string, any>) =>
  api.patch(`/events/treatments/${id}`, data)
export const createTreatment = (data: Record<string, any>) =>
  api.post('/events/treatments', data)

// 동기화
export const syncEventsFromUrl = (data: { year: number; start_month: number; end_month: number; source_url: string }) =>
  api.post('/events/sync', data)

export const syncEventsFromFile = (file: File, year: number, startMonth: number, endMonth: number) => {
  const form = new FormData()
  form.append('file', file)
  return api.post(`/events/sync-file?year=${year}&start_month=${startMonth}&end_month=${endMonth}`, form)
}

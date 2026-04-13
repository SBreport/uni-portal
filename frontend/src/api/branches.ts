import api from './client'

export async function fetchBranches(activeOnly = true) {
  const { data } = await api.get('/branches', { params: { active_only: activeOnly } })
  return data
}

export async function fetchAgencyMap(type: 'place' | 'webpage'): Promise<Record<string, string>> {
  const { data } = await api.get('/config/agency-map', { params: { type } })
  return data
}

export async function saveAgencyMap(type: string, data: Record<string, string>) {
  return api.post('/config/agency-map', { type, data })
}

export async function fetchAgencySheets(): Promise<Record<string, string>> {
  const { data } = await api.get('/config/agency-sheets')
  return data
}

export async function saveAgencySheets(data: Record<string, string>): Promise<void> {
  await api.post('/config/agency-sheets', { data })
}

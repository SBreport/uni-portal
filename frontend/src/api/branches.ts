import api from './client'

export async function fetchBranches(activeOnly = true) {
  const { data } = await api.get('/branches', { params: { active_only: activeOnly } })
  return data
}

export async function fetchAgencyMap(type: 'place' | 'webpage'): Promise<Record<string, string>> {
  const { data } = await api.get('/config/agency-map', { params: { type } })
  return data
}

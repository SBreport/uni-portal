import api from './client'

export const getWebpageMonths = () => api.get('/webpage/months')

export const getWebpageRanking = (month: string) =>
  api.get('/webpage/ranking', { params: { month } })

// DB 기반 API
export const getWebpageRankingDB = (year: number, month: number) =>
  api.get('/webpage/ranking-db', { params: { year, month } })

export const syncWebpageToDB = () =>
  api.post('/webpage/sync-to-db', {}, { timeout: 180000 })

export const getWebpageDaily = (params?: { branch_id?: number; date_from?: string; date_to?: string }) =>
  api.get('/webpage/daily', { params })

export const getWebpageRankingDaily = (date: string) =>
  api.get('/webpage/ranking-daily', { params: { date } })

export const getWebpageLastSync = () => api.get('/webpage/last-sync')

export const getWebpageBranchDetail = (branch_name: string, keyword: string, reference_date: string) =>
  api.get('/webpage/branch-detail', { params: { branch_name, keyword, reference_date } })

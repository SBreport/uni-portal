import api from './client'

export const getPlaceMonths = () => api.get('/place/months')

export const getPlaceRanking = (month: string) =>
  api.get('/place/ranking', { params: { month } })

// DB 기반 API (동기화 후 사용)
export const getPlaceRankingDB = (year: number, month: number) =>
  api.get('/place/ranking-db', { params: { year, month } })

export const syncPlaceToDB = (targetMonth?: string) =>
  api.post('/place/sync-to-db', { target_month: targetMonth ?? null }, { timeout: 180000 })

export const getPlaceDaily = (params?: { branch_id?: number; date_from?: string; date_to?: string }) =>
  api.get('/place/daily', { params })

export const getPlaceRankingDaily = (date: string) =>
  api.get('/place/ranking-daily', { params: { date } })

export const getPlaceLastSync = () => api.get('/place/last-sync')

export const getPlaceBranchDetail = (branch_name: string, keyword: string, reference_date: string) =>
  api.get('/place/branch-detail', { params: { branch_name, keyword, reference_date } })

export const cleanupPollution = (dryRun: boolean = true) =>
  api.post('/place/cleanup-pollution', null, { params: { dry_run: dryRun } })

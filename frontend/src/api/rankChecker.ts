import api from './client'

// 키워드 CRUD
export const getKeywords = (branchId?: number) =>
  api.get('/rank-checker/keywords', { params: branchId ? { branch_id: branchId } : {} })

export const createKeyword = (data: {
  branch_id: number
  branch_name: string
  keyword: string
  search_keyword?: string
  place_id: string
  guaranteed_rank?: number
  memo?: string
}) => api.post('/rank-checker/keywords', data)

export const updateKeyword = (id: number, data: Record<string, any>) =>
  api.patch(`/rank-checker/keywords/${id}`, data)

export const deleteKeyword = (id: number) =>
  api.delete(`/rank-checker/keywords/${id}`)

// 순위 체크 실행
export const checkBranch = (branchId: number) =>
  api.post(`/rank-checker/check/${branchId}`, {}, { timeout: 120000 })

export const checkAll = () =>
  api.post('/rank-checker/check-all', {}, { timeout: 300000 })

// 결과 조회
export const getHistory = (branchId: number, days?: number) =>
  api.get(`/rank-checker/history/${branchId}`, { params: days ? { days } : {} })

export const getComparison = (branchId: number, date?: string) =>
  api.get(`/rank-checker/comparison/${branchId}`, { params: date ? { date } : {} })

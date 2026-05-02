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

// 지점 place_id 자동 매칭 (brand_prefix 옵션 — '유앤아이의원' 같은 회사명 prefix)
export const autoMatchBranches = (brandPrefix?: string) =>
  api.post(
    '/rank-checker/auto-match-branches',
    { brand_prefix: brandPrefix || null },
    { timeout: 600000 },  // 10분 — N개 지점 × 0.5초 + 네이버 응답 시간
  )

export const savePlaceIds = (items: { branch_id: number; place_id: string }[]) =>
  api.post('/rank-checker/save-place-ids', items)

// SB_CHECKER DB 임포트
export const importSbDb = (file: File) => {
  const form = new FormData()
  form.append('file', file)
  return api.post('/rank-checker/import-sb-db', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 60000,
  })
}

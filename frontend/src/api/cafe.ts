import api from './client'

// ── 기간 / 지점 ──
export const getPeriods = () => api.get('/cafe/periods')
export const getBranches = () => api.get('/cafe/branches')

export const createBranchPeriod = (year: number, month: number, branchId: number) =>
  api.post('/cafe/branch-periods', { year, month, branch_id: branchId })

export const getBranchPeriodMeta = (bpId: number) =>
  api.get(`/cafe/branch-periods/${bpId}/meta`)

// ── 원고 목록 ──
export const getArticles = (bpId: number) =>
  api.get(`/cafe/branch-periods/${bpId}/articles`)

// ── 원고 상세 ──
export const getArticleDetail = (articleId: number) =>
  api.get(`/cafe/articles/${articleId}`)

export const updateArticle = (articleId: number, data: Record<string, any>) =>
  api.patch(`/cafe/articles/${articleId}`, data)

// ── 상태 ──
export const changeStatus = (articleId: number, newStatus: string, changedBy: string, note = '') =>
  api.post(`/cafe/articles/${articleId}/status`, { new_status: newStatus, changed_by: changedBy, note })

// ── 발행 ──
export const publishArticle = (articleId: number, url: string, publishedBy: string) =>
  api.post(`/cafe/articles/${articleId}/publish`, { url, published_by: publishedBy })

// ── 댓글 ──
export const upsertComment = (articleId: number, slot: number, commentText: string, replyText: string) =>
  api.put(`/cafe/articles/${articleId}/comments/${slot}`, { comment_text: commentText, reply_text: replyText })

// ── 피드백 ──
export const addFeedback = (articleId: number, author: string, content: string) =>
  api.post(`/cafe/articles/${articleId}/feedbacks`, { author, content })

export const getStatusHistory = (articleId: number) =>
  api.get(`/cafe/articles/${articleId}/history`)

// ── 대시보드 ──
export const getSummary = (periodId: number) =>
  api.get(`/cafe/summary/${periodId}`)

// ── 동기화 ──
export const syncCafe = (year: number, month: number, branchFilter = '') =>
  api.post('/cafe/sync', { year, month, branch_filter: branchFilter })

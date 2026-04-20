import api from './client'

// ── 대시보드 타입 ──────────────────────────────────────────────────────────────

export interface WeeklyKpiCurrent {
  week_start: string
  blogDistribution: { ranked: string; keywords: string }
  place: { occupied: string; total: string }
  website: { visible: string; total: string }
  blogExposure: { visible: string; total: string }
  related: { created: string; total: string }
}

export interface WeeklyKpis {
  current: WeeklyKpiCurrent | null
  previous: WeeklyKpiCurrent | null
  has_current: boolean
  has_previous: boolean
}

export interface WeeklyTrendPoint {
  week_start: string
  blog_ranked: number | null
  place_occupied: number | null
  website_visible: number | null
  blog_exposure_visible: number | null
  related_created: number | null
}

export interface RealtimeStats {
  place: { success: number; fail: number; midal: number; total: number; date: string }
  webpage: { visible: number; fail: number; midal: number; total: number; date: string }
}

export interface DashboardData {
  weekly_kpis: WeeklyKpis
  weekly_trend: WeeklyTrendPoint[]
  realtime: RealtimeStats
}

export const getDashboard = (weeks: number = 8) =>
  api.get<DashboardData>('/reports/dashboard', { params: { weeks } })

// ── 보고서 CRUD 타입 ───────────────────────────────────────────────────────────

export interface WeeklyReportSummary {
  id: number
  week_start: string   // "YYYY-MM-DD" (월요일)
  week_end: string     // "YYYY-MM-DD" (일요일)
  title: string
  created_at: string
  updated_at: string
  created_by: number | null
}

export interface WeeklyReport extends WeeklyReportSummary {
  data: Record<string, any>
}

export interface CreateReportPayload {
  week_start: string
  title?: string
  data?: Record<string, any>
}

export interface UpdateReportPayload {
  title?: string
  data?: Record<string, any>
}

export const listWeeklyReports = (limit?: number) =>
  api.get<WeeklyReportSummary[]>('/reports/weekly', { params: limit ? { limit } : {} })

export const getWeeklyReport = (weekStart: string) =>
  api.get<WeeklyReport>(`/reports/weekly/${weekStart}`)

export const createWeeklyReport = (payload: CreateReportPayload) =>
  api.post<WeeklyReport>('/reports/weekly', payload)

export const updateWeeklyReport = (weekStart: string, payload: UpdateReportPayload) =>
  api.put<WeeklyReport>(`/reports/weekly/${weekStart}`, payload)

export const deleteWeeklyReport = (weekStart: string) =>
  api.delete<{ deleted: string }>(`/reports/weekly/${weekStart}`)

// ── 이미지 업로드/삭제 ─────────────────────────────────────────────────────────

export interface UploadImageResponse {
  path: string      // "reports/2026-04-06/place/abc.png"
  url: string       // "/uploads/reports/.../abc.png"
  filename: string
}

export const uploadReportImage = (
  weekStart: string,
  section: string,
  file: File
) => {
  const formData = new FormData()
  formData.append('section', section)
  formData.append('file', file)
  return api.post<UploadImageResponse>(
    `/reports/weekly/${weekStart}/images`,
    formData,
    { headers: { 'Content-Type': 'multipart/form-data' } }
  )
}

export const deleteReportImage = (weekStart: string, path: string) =>
  api.delete(`/reports/weekly/${weekStart}/images`, { params: { path } })

// 공개 조회는 axios client의 기본 interceptor가 토큰을 붙이지만,
// 백엔드 /public/{week_start}은 인증 헤더를 무시하므로 같은 인스턴스 사용 가능
export const getPublicReport = (weekStart: string) =>
  api.get<WeeklyReport>(`/reports/public/${weekStart}`)

export const autofillWeeklyReport = (weekStart: string) =>
  api.post<WeeklyReport>(`/reports/weekly/${weekStart}/autofill`)

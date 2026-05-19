import api from './client'

export interface PendingMigration {
  filename: string
  size: number
  modified_at: string
  lines: number
  summary_top: string
}

export interface MigrationHistory {
  id: number
  filename: string
  applied_at: string
  applied_by: string
  success: number
  summary: string
  backup_path: string
  error_log: string
  sql_hash: string
}

export interface PreviewResult {
  filename: string
  content: string
  line_count: number
}

export interface ApplyResult {
  success: boolean
  summary: string
  backup_path: string
  error: string | null
}

export const getPendingMigrations = () =>
  api.get<PendingMigration[]>('/admin/migrations/pending')

export const previewMigration = (filename: string) =>
  api.get<PreviewResult>(`/admin/migrations/preview/${encodeURIComponent(filename)}`)

export const applyMigration = (filename: string) =>
  api.post<ApplyResult>('/admin/migrations/apply', { filename })

export const getMigrationHistory = () =>
  api.get<MigrationHistory[]>('/admin/migrations/history')

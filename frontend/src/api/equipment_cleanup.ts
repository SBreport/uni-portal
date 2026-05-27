import api from './client'

export interface CleanupSummary {
  duplicate_groups: number
  duplicate_excess_rows: number
  null_mapping: number
}

export interface EquipmentRow {
  id: number
  name: string
  qty: number
  source: string
  note: string
  created_at: string
  variant: string | null
}

export interface VariantSummaryItem {
  variant: string
  count: number
}

export interface VariantSummary {
  distinct_count: number
  items: VariantSummaryItem[]
}

export interface DuplicateGroup {
  branch_id: number
  branch_name: string
  device_info_id: number
  device_info_name: string
  category_name: string
  row_count: number
  total_qty: number
  variant_summary: VariantSummary
  rows: EquipmentRow[]
}

export interface DuplicatesResponse {
  groups: DuplicateGroup[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface MergeRequest {
  branch_id: number
  device_info_id: number
  target_row_id: number
  source_row_ids: number[]
  new_name?: string
}

export interface MergeResult {
  success: boolean
  target_id: number
  merged_count: number
  new_qty: number
  new_name: string
}

export interface RemapRequest {
  branch_id?: number
  force?: boolean
}

export interface RemapResult {
  remapped_count: number
  unmatched_count: number
  total_processed: number
}

export const getCleanupSummary = () =>
  api.get<CleanupSummary>('/admin/equipment-cleanup/summary')

export const getDuplicates = (params: { branch_id?: number; page?: number; page_size?: number }) =>
  api.get<DuplicatesResponse>('/admin/equipment-cleanup/duplicates', { params })

export const mergeEquipment = (data: MergeRequest) =>
  api.post<MergeResult>('/admin/equipment-cleanup/merge', data)

export const remapEquipment = (data: RemapRequest) =>
  api.post<RemapResult>('/admin/equipment-cleanup/remap', data, { timeout: 300000 })

// ── 자동 통합 ──────────────────────────────────────────────────────────────

export interface AutoMergeGroup {
  tier: 1 | 2 | 3
  branch_name: string
  device_info_name: string
  name: string          // 통합 후 대표 이름
  row_ids: number[]
  names: string[]       // 원본 이름들
  qtys: number[]
  total_qty: number
}

export interface AutoMergePreviewResponse {
  tier1_count: number
  tier2_count: number
  tier3_count: number
  total: number
  total_affected_rows: number
  page: number
  page_size: number
  total_pages: number
  groups: AutoMergeGroup[]
}

export interface AutoMergeRequest {
  tiers: number[]
}

export interface AutoMergeResult {
  merged_groups: number
  deleted_rows: number
  total_qty_consolidated: number
}

export const getAutoMergePreview = (params: { page?: number; page_size?: number }) =>
  api.get<AutoMergePreviewResponse>('/admin/equipment-cleanup/auto-merge-preview', { params })

export const executeAutoMerge = (data: AutoMergeRequest) =>
  api.post<AutoMergeResult>('/admin/equipment-cleanup/auto-merge-execute', data, { timeout: 120000 })

// ── 신규 마스터 후보 ────────────────────────────────────────────────────────

export interface NewMasterCandidate {
  name: string
  normalized_name: string
  current_di_id: number | null
  current_di_name: string | null
  branches: string[]
  row_ids: number[]
  total_qty: number
  suggested_category: string
  suggested_primary_category_id: number | null
}

export interface NewMasterCandidatesResponse {
  tier1_candidates: NewMasterCandidate[]
  tier2_candidates: NewMasterCandidate[]
  total_candidates: number
}

export interface NewMasterItem {
  name: string
  category: string
  summary: string
  target: string
  mechanism: string
  aliases: string
  device_type: string
  primary_category_id: number | null
  row_ids: number[]
}

export interface RegisterNewMastersRequest {
  candidates: NewMasterItem[]
}

export interface RegisterNewMastersResult {
  inserted: number
  remapped: number
}

export const getNewMasterCandidates = () =>
  api.get<NewMasterCandidatesResponse>('/admin/equipment-cleanup/new-master-candidates')

export const registerNewMasters = (data: RegisterNewMastersRequest) =>
  api.post<RegisterNewMastersResult>('/admin/equipment-cleanup/register-new-masters', data, { timeout: 120000 })

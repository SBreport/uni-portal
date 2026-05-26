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
}

export interface DuplicateGroup {
  branch_id: number
  branch_name: string
  device_info_id: number
  device_info_name: string
  category_name: string
  row_count: number
  total_qty: number
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

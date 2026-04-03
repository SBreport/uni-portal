import api from './client'

export interface Complaint {
  id: number
  branch_id: number
  branch_name: string
  title: string
  content: string
  category: string
  severity: string
  status: string
  reported_by: string
  assigned_to: string
  resolution: string
  resolved_at: string | null
  created_at: string
  updated_at: string
}

export interface ComplaintLog {
  id: number
  complaint_id: number
  old_status: string
  new_status: string
  changed_by: string
  note: string
  changed_at: string
}

export function getComplaints(params?: { branch_id?: number; status?: string; page?: number }) {
  return api.get<Complaint[]>('/complaints', { params })
}

export function getComplaint(id: number) {
  return api.get<Complaint>(`/complaints/${id}`)
}

export function createComplaint(data: Partial<Complaint>) {
  return api.post('/complaints', data)
}

export function updateComplaint(id: number, data: Partial<Complaint>) {
  return api.patch(`/complaints/${id}`, data)
}

export function changeComplaintStatus(id: number, new_status: string, note = '') {
  return api.post(`/complaints/${id}/status`, { new_status, note })
}

export function getComplaintLogs(id: number) {
  return api.get<ComplaintLog[]>(`/complaints/${id}/logs`)
}

export function getComplaintSummary() {
  return api.get<Record<string, number>>('/complaints/summary/counts')
}

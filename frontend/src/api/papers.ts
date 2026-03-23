import api from './client'

export const getPapers = (params?: {
  device_info_id?: number
  treatment_id?: number
  status?: string
  q?: string
}) => api.get('/papers', { params })

export const getPaper = (id: number) => api.get(`/papers/${id}`)

export const getPapersByDevice = (deviceInfoId: number) =>
  api.get(`/papers/by-device/${deviceInfoId}`)

export const getPapersByTreatment = (treatmentId: number) =>
  api.get(`/papers/by-treatment/${treatmentId}`)

export const updatePaper = (id: number, data: Record<string, any>) =>
  api.patch(`/papers/${id}`, data)

export const deletePaper = (id: number) =>
  api.delete(`/papers/${id}`)

// JSON 파일 업로드 (로컬 분석 결과 일괄 등록)
export const uploadPapersJson = (file: File) => {
  const formData = new FormData()
  formData.append('file', file)
  return api.post('/papers/upload-json', formData, { timeout: 60000 })
}

// 폴더 스캔 (PDF 파일 목록 확인)
export const scanFolder = (folderPath: string) =>
  api.post('/papers/scan-folder', { folder_path: folderPath })

// 하위 폴더 탐색 (폴더 탐색기용)
export const listDirs = (folderPath: string) =>
  api.post('/papers/list-dirs', { folder_path: folderPath })

// 폴더 분석 실행 (paper_analyzer.py 호출)
export const analyzeDir = (folderPath: string, apiKey: string, dryRun = false) =>
  api.post('/papers/analyze-dir', {
    folder_path: folderPath,
    api_key: apiKey,
    dry_run: dryRun,
  }, { timeout: 660000 })  // 11분 (서버 10분 + 여유)

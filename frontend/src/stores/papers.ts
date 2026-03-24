import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as papersApi from '@/api/papers'

export interface Paper {
  id: number
  device_info_id: number | null
  treatment_id: number | null
  doi: string
  title: string
  title_ko: string
  authors: string
  journal: string
  pub_year: number | null
  evidence_level: number
  study_type: string
  sample_size: string
  status: string
  one_line_summary: string
  research_purpose: string
  study_design_detail: string
  key_results: string
  key_findings: string
  conclusion: string
  cautions: string
  quotable_stats: string
  follow_up_period: string
  photo_restriction: string
  keywords: string
  source_url: string
  device_name?: string
  treatment_name?: string
  treatment_brand?: string
  [key: string]: any
}

export interface DeviceSummary {
  id: number
  name: string
  paper_count: number
}

export interface StudyTypeInfo {
  study_type: string
  cnt: number
}

export const usePapersStore = defineStore('papers', () => {
  const papers = ref<Paper[]>([])
  const loading = ref(false)

  // 필터
  const filterSearch = ref('')
  const filterStatus = ref('')
  const filterDeviceId = ref<number | null>(null)
  const filterEvidenceMin = ref<number | null>(null)
  const filterStudyType = ref('')

  // 필터 옵션 데이터
  const deviceOptions = ref<DeviceSummary[]>([])
  const studyTypeOptions = ref<StudyTypeInfo[]>([])

  async function loadPapers() {
    loading.value = true
    try {
      const params: Record<string, any> = {}
      if (filterSearch.value) params.q = filterSearch.value
      if (filterStatus.value) params.status = filterStatus.value
      if (filterDeviceId.value) params.device_info_id = filterDeviceId.value
      if (filterEvidenceMin.value !== null) params.evidence_min = filterEvidenceMin.value
      if (filterStudyType.value) params.study_type = filterStudyType.value
      const { data } = await papersApi.getPapers(params)
      papers.value = data
    } finally {
      loading.value = false
    }
  }

  async function loadFilterOptions() {
    try {
      const [devRes, stRes] = await Promise.all([
        papersApi.getDevicesSummary(),
        papersApi.getStudyTypes(),
      ])
      deviceOptions.value = devRes.data
      studyTypeOptions.value = stRes.data
    } catch { /* 필터 옵션 로딩 실패 시 무시 */ }
  }

  function resetFilters() {
    filterSearch.value = ''
    filterStatus.value = ''
    filterDeviceId.value = null
    filterEvidenceMin.value = null
    filterStudyType.value = ''
    loadPapers()
  }

  return {
    papers, loading,
    filterSearch, filterStatus, filterDeviceId, filterEvidenceMin, filterStudyType,
    deviceOptions, studyTypeOptions,
    loadPapers, loadFilterOptions, resetFilters,
  }
})

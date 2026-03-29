import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import * as cafeApi from '@/api/cafe'

export interface Branch { id: number; name: string; short_name: string }
export interface Period { id: number; year: number; month: number; label: string; is_current: number }
export interface Article {
  id: number; article_order: number; keyword: string; category: string
  equipment_name: string; title: string; body: string; status: string
  published_url: string; published_at: string; published_by: string
  created_at?: string; updated_at?: string
}
export interface ArticleDetail extends Article {
  comments: { slot_number: number; comment_text: string; reply_text: string }[]
  feedbacks: { id: number; author: string; content: string; created_at: string }[]
}
export interface SummaryRow {
  branch_name: string
  smart_manager: string
  writer: string
  total: number
  // 상태별 카운트
  작성대기: number; 작성완료: number; 수정요청: number; 검수완료: number; 발행완료: number; 보류: number
  // 유형별 카운트
  cnt_info: number; cnt_review_type: number; cnt_superset: number
  cnt_info_done: number; cnt_review_done: number; cnt_superset_done: number
  // 메타
  photo_link: string; general_photo_link: string; progress_note: string
}

export const useCafeStore = defineStore('cafe', () => {
  const periods = ref<Period[]>([])
  const branches = ref<Branch[]>([])
  const currentPeriod = ref<Period | null>(null)
  const currentBranch = ref<Branch | null>(null)
  const branchPeriodId = ref<number | null>(null)
  const articles = ref<Article[]>([])
  const currentArticle = ref<ArticleDetail | null>(null)
  const summary = ref<SummaryRow[]>([])
  const loading = ref(false)

  async function loadPeriods() {
    const { data } = await cafeApi.getPeriods()
    periods.value = data
    if (!currentPeriod.value && data.length) {
      currentPeriod.value = data.find((p: Period) => p.is_current) || data[0]
    }
  }

  async function loadBranches() {
    const { data } = await cafeApi.getBranches()
    branches.value = data
  }

  async function selectBranchPeriod(branchId: number, year: number, month: number) {
    const { data } = await cafeApi.createBranchPeriod(year, month, branchId)
    branchPeriodId.value = data.branch_period_id
    await loadArticles()
  }

  async function loadArticles() {
    if (!branchPeriodId.value) return
    loading.value = true
    try {
      const { data } = await cafeApi.getArticles(branchPeriodId.value)
      articles.value = data
    } finally {
      loading.value = false
    }
  }

  async function loadArticleDetail(articleId: number) {
    loading.value = true
    try {
      const { data } = await cafeApi.getArticleDetail(articleId)
      currentArticle.value = data
    } finally {
      loading.value = false
    }
  }

  async function saveArticle(articleId: number, updates: Record<string, any>) {
    await cafeApi.updateArticle(articleId, updates)
    await loadArticleDetail(articleId)
    await loadArticles()
  }

  async function loadSummary() {
    if (!currentPeriod.value) return
    const { data } = await cafeApi.getSummary(currentPeriod.value.id)
    summary.value = data
  }

  return {
    periods, branches, currentPeriod, currentBranch, branchPeriodId,
    articles, currentArticle, summary, loading,
    loadPeriods, loadBranches, selectBranchPeriod, loadArticles,
    loadArticleDetail, saveArticle, loadSummary,
  }
})

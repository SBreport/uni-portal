<script setup lang="ts">
import { ref, onMounted } from 'vue'
import * as blogApi from '@/api/blog'

const summary = ref<any>(null)
const details = ref<any>(null)
const activeCategory = ref('deleted')
const loading = ref(false)

const categories = [
  { key: 'deleted', label: '삭제된 글', color: 'text-red-500 border-red-400' },
  { key: 'cafe_fail', label: '카페 수집불가', color: 'text-amber-500 border-amber-400' },
  { key: 'needs_review', label: '검토 필요', color: 'text-purple-500 border-purple-400' },
  { key: 'no_title', label: '제목 미수집', color: 'text-slate-500 border-slate-400' },
  { key: 'no_branch', label: '지점 미매핑', color: 'text-sky-500 border-sky-400' },
]

async function loadSummary() {
  try {
    const { data } = await blogApi.getDataQuality()
    summary.value = data
  } catch (e) { console.error(e) }
}

async function selectCategory(key: string) {
  activeCategory.value = key
  loading.value = true
  details.value = null
  try {
    const { data } = await blogApi.getDataQualityDetails(key, 100)
    details.value = data
  } catch (e) { console.error(e) }
  finally { loading.value = false }
}

function channelLabel(ch: string) {
  if (ch === 'br') return '브블'
  if (ch === 'opt') return '최블'
  if (ch === 'cafe') return '카페'
  return ch || '-'
}

function channelClass(ch: string) {
  if (ch === 'br') return 'bg-emerald-50 text-emerald-600'
  if (ch === 'opt') return 'bg-violet-50 text-violet-600'
  return 'bg-slate-100 text-slate-500'
}

function statusText(item: any) {
  if (item.scraped_title === '(삭제됨)') return '삭제됨'
  if (item.scraped_title === '(카페-수집불가)') return '수집불가'
  if (item.needs_review) return '검토필요'
  return '—'
}

function statusClass(item: any) {
  if (item.scraped_title === '(삭제됨)') return 'text-red-400'
  if (item.scraped_title === '(카페-수집불가)') return 'text-amber-400'
  if (item.needs_review) return 'text-purple-400'
  return 'text-slate-300'
}

// 블로그 데이터 관리
const notionStatus = ref<any>(null)
const notionSyncing = ref(false)
const scrapeStatus = ref<any>(null)
const scraping = ref(false)
const importingData = ref(false)
const blogActionMsg = ref('')
const blogActionError = ref(false)

function showMsg(msg: string, isError = false) {
  blogActionMsg.value = msg
  blogActionError.value = isError
  setTimeout(() => { blogActionMsg.value = '' }, 5000)
}

async function loadBlogStatus() {
  try {
    const [notion, scrape] = await Promise.all([
      blogApi.getNotionSyncStatus(),
      blogApi.getScrapeTitlesStatus(),
    ])
    notionStatus.value = notion.data
    scrapeStatus.value = scrape.data
  } catch {}
}

async function syncNotion() {
  notionSyncing.value = true
  try {
    const { data } = await blogApi.syncNotion()
    showMsg(data.message || '동기화 완료')
    loadBlogStatus()
  } catch (e: any) { showMsg(e.response?.data?.detail || '실패', true) }
  finally { notionSyncing.value = false }
}

async function runScrape(includeCafe: boolean) {
  scraping.value = true
  try {
    const { data } = await blogApi.scrapeTitles({ limit: 0, delay: 0.3, include_cafe: includeCafe })
    showMsg(`수집 ${data.scraped}건 완료 (${data.scraped}수집 / ${data.failed}실패 / ${data.deleted}삭제)`)
    loadBlogStatus()
    loadSummary()
  } catch (e: any) { showMsg(e.response?.data?.detail || '실패', true) }
  finally { scraping.value = false }
}

async function importData() {
  importingData.value = true
  try {
    const { data } = await blogApi.importBlogData()
    showMsg(data.message || '임포트 완료')
    loadBlogStatus()
  } catch (e: any) { showMsg(e.response?.data?.detail || '실패', true) }
  finally { importingData.value = false }
}

async function uploadCsv(e: Event) {
  const target = e.target as HTMLInputElement
  const file = target.files?.[0]
  if (!file) return
  try {
    const { data } = await blogApi.uploadBlogCsv(file)
    showMsg(data.message || 'CSV 업로드 완료')
    loadBlogStatus()
  } catch (e: any) { showMsg(e.response?.data?.detail || 'CSV 업로드 실패', true) }
  finally { target.value = '' }
}

onMounted(() => {
  loadSummary()
  selectCategory('deleted')
  loadBlogStatus()
})
</script>

<template>
  <div class="max-w-3xl">
    <!-- 헤더 -->
    <div class="flex items-center justify-between mb-3">
      <p class="text-xs text-slate-400">총 {{ summary?.total?.toLocaleString() ?? '-' }}건 기준</p>
      <button @click="loadSummary" class="text-xs text-blue-600 hover:text-blue-800">새로고침</button>
    </div>

    <!-- 카테고리 가로 탭 -->
    <div v-if="summary" class="flex gap-2 mb-4">
      <button
        v-for="cat in categories"
        :key="cat.key"
        @click="selectCategory(cat.key)"
        :class="[
          'px-3 py-2 rounded-lg border text-center transition min-w-0',
          activeCategory === cat.key
            ? 'border-blue-400 bg-blue-50'
            : 'border-slate-200 bg-white hover:bg-slate-50'
        ]"
      >
        <p class="text-lg font-bold" :class="cat.color.split(' ')[0]">
          {{ (summary[cat.key] ?? 0).toLocaleString() }}
        </p>
        <p class="text-[11px] text-slate-500 whitespace-nowrap">{{ cat.label }}</p>
      </button>
    </div>

    <!-- 블로그 데이터 관리 -->
    <div class="border border-slate-200 rounded-lg bg-white p-4 mb-4">
      <h3 class="text-sm font-semibold text-slate-700 mb-3">블로그 데이터 관리</h3>
      <div class="space-y-2">
        <!-- Notion 동기화 -->
        <div class="flex items-center justify-between py-2 px-3 bg-slate-50 rounded">
          <div>
            <p class="text-xs font-medium text-slate-700">블로그 Notion 동기화</p>
            <p v-if="notionStatus?.last_sync" class="text-[10px] text-slate-400">
              {{ notionStatus.last_sync.synced_at?.slice(0, 16) || '-' }}
              · {{ notionStatus.last_sync.sync_type === 'incremental' ? '증분' : '전체' }}
              · 신규 {{ notionStatus.last_sync.new_posts ?? 0 }}건
              · 갱신 {{ notionStatus.last_sync.updated ?? 0 }}건
            </p>
          </div>
          <div class="flex gap-2">
            <button @click="syncNotion" :disabled="notionSyncing"
              class="px-3 py-1 bg-blue-600 text-white text-xs rounded hover:bg-blue-700 disabled:opacity-50">
              {{ notionSyncing ? '동기화 중...' : '증분 동기화' }}
            </button>
          </div>
        </div>
        <!-- 제목 스크래핑 -->
        <div class="flex items-center justify-between py-2 px-3 bg-slate-50 rounded">
          <div>
            <p class="text-xs font-medium text-slate-700">블로그 원고 제목 수집</p>
            <p v-if="scrapeStatus" class="text-[10px] text-slate-400">
              수집 {{ scrapeStatus.already_scraped?.toLocaleString() }}건
              / 남은 블로그 {{ scrapeStatus.remaining_blog }}건 · 카페 {{ scrapeStatus.remaining_cafe }}건
            </p>
          </div>
          <div class="flex gap-2">
            <button @click="runScrape(false)" :disabled="scraping"
              class="px-3 py-1 bg-indigo-600 text-white text-xs rounded hover:bg-indigo-700 disabled:opacity-50">블로그만</button>
            <button @click="runScrape(true)" :disabled="scraping"
              class="px-3 py-1 bg-purple-600 text-white text-xs rounded hover:bg-purple-700 disabled:opacity-50">카페 포함</button>
          </div>
        </div>
        <!-- 데이터 임포트 -->
        <div class="flex items-center justify-between py-2 px-3 bg-slate-50 rounded">
          <div>
            <p class="text-xs font-medium text-slate-700">블로그 데이터 임포트</p>
            <p class="text-[10px] text-slate-400">로컬에서 수집한 데이터를 서버 DB에 반영</p>
          </div>
          <button @click="importData" :disabled="importingData"
            class="px-3 py-1 bg-amber-600 text-white text-xs rounded hover:bg-amber-700 disabled:opacity-50">
            {{ importingData ? '임포트 중...' : '데이터 임포트' }}
          </button>
        </div>
        <!-- CSV 업로드 -->
        <div class="flex items-center justify-between py-2 px-3 bg-slate-50 rounded">
          <div>
            <p class="text-xs font-medium text-slate-700">블로그 게시글 CSV 업로드</p>
            <p class="text-[10px] text-slate-400">노션에서 내보낸 CSV 파일 · 중복 항목은 자동 건너뜀</p>
          </div>
          <label class="px-3 py-1 bg-slate-600 text-white text-xs rounded cursor-pointer hover:bg-slate-700">
            CSV 파일 선택
            <input type="file" accept=".csv" class="hidden" @change="uploadCsv" />
          </label>
        </div>
        <!-- Result message -->
        <div v-if="blogActionMsg" class="text-xs px-3 py-1 rounded"
          :class="blogActionError ? 'bg-red-50 text-red-700' : 'bg-emerald-50 text-emerald-700'">
          {{ blogActionMsg }}
        </div>
      </div>
    </div>

    <!-- 상세 테이블 -->
    <div class="border border-slate-200 rounded-lg overflow-hidden bg-white">
      <div class="px-4 py-2.5 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
        <span class="text-xs font-semibold text-slate-600">
          {{ categories.find(c => c.key === activeCategory)?.label }} 상세
        </span>
        <span v-if="details" class="text-xs text-slate-400">
          {{ details.total?.toLocaleString() }}건 중 {{ details.items?.length }}건 표시
        </span>
      </div>

      <div v-if="loading" class="flex items-center justify-center py-16">
        <div class="w-5 h-5 border-2 border-blue-400 border-t-transparent rounded-full animate-spin"></div>
        <span class="ml-2 text-sm text-slate-400">로딩 중...</span>
      </div>

      <div v-else-if="details?.items?.length" class="overflow-auto" style="max-height: 500px;">
        <div class="divide-y divide-slate-50">
            <div v-for="item in details.items" :key="item.id"
              class="px-3 py-2.5 hover:bg-slate-50 flex items-start gap-2">
              <span class="shrink-0 mt-0.5 px-1.5 py-0.5 rounded-full text-[10px] font-medium"
                :class="channelClass(item.blog_channel)">
                {{ channelLabel(item.blog_channel) }}
              </span>
              <div class="min-w-0 flex-1">
                <a v-if="item.published_url" :href="item.published_url" target="_blank"
                  class="text-xs text-slate-700 hover:text-blue-600 block truncate leading-snug">
                  {{ item.title || item.keyword || '(없음)' }}
                </a>
                <span v-else class="text-xs text-slate-400 block truncate leading-snug">
                  {{ item.title || item.keyword || '(없음)' }}
                </span>
                <div class="flex items-center gap-2 mt-0.5 text-[10px] text-slate-400">
                  <span v-if="item.branch_name">{{ item.branch_name }}</span>
                  <span>{{ item.published_at?.slice(0, 10) || '-' }}</span>
                  <span :class="statusClass(item)">{{ statusText(item) }}</span>
                </div>
              </div>
            </div>
        </div>
      </div>

      <div v-else class="flex items-center justify-center py-16 text-sm text-slate-400">
        해당 항목 없음
      </div>
    </div>
  </div>
</template>

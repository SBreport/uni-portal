<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import * as equipApi from '@/api/equipment'
import * as eventsApi from '@/api/events'
import * as cafeApi from '@/api/cafe'
import * as blogApi from '@/api/blog'
import { useAsyncAction } from '@/composables/useAsyncAction'

const props = defineProps<{ branches: { id: number; name: string }[] }>()

const { loading: syncing, message: syncMsg, error: syncError, execute: executeSync } = useAsyncAction()

// 장비
async function syncEquipment() {
  await executeSync(async () => {
    const { data } = await equipApi.syncFromSheets()
    return `장비 동기화 완료: +${data.added} ↻${data.updated} =${data.skipped}`
  })
}

// 이벤트
const now = new Date()
const evtBiMonth = computed(() => {
  const idx = Math.min(Math.floor((now.getMonth()) / 2), 5)
  const pairs = [[1,2],[3,4],[5,6],[7,8],[9,10],[11,12]]
  return pairs[idx]!
})
const evtYear = ref(now.getFullYear())
const evtStartMonth = computed(() => evtBiMonth.value[0]!)
const evtEndMonth = computed(() => evtBiMonth.value[1]!)
const evtSyncMethod = ref<'url' | 'file'>('url')
const evtSheetUrl = ref('')
const evtFile = ref<File | null>(null)

async function syncEvents() {
  await executeSync(async () => {
    if (evtSyncMethod.value === 'url' && !evtSheetUrl.value) throw new Error('URL을 입력해주세요.')
    if (evtSyncMethod.value === 'file' && !evtFile.value) throw new Error('파일을 선택해주세요.')
    let data: any
    if (evtSyncMethod.value === 'url') {
      data = (await eventsApi.syncEventsFromUrl({ year: evtYear.value, start_month: evtStartMonth.value, end_month: evtEndMonth.value, source_url: evtSheetUrl.value })).data
    } else {
      data = (await eventsApi.syncEventsFromFile(evtFile.value!, evtYear.value, evtStartMonth.value, evtEndMonth.value)).data
    }
    const errors = data.errors || []
    return `이벤트 수집 완료: ${data.processed}개 지점, ${data.total_items?.toLocaleString()}건` + (errors.length ? ` (오류 ${errors.length}건)` : '')
  })
}

function onEvtFileChange(e: Event) {
  const target = e.target as HTMLInputElement
  evtFile.value = target.files?.[0] || null
}

// 카페
const cafeBranch = ref('')
const cafeSheetUrl = ref('')

async function syncCafe() {
  await executeSync(async () => {
    const now = new Date()
    const { data } = await cafeApi.syncCafe(now.getFullYear(), now.getMonth() + 1, cafeBranch.value, cafeSheetUrl.value)
    const errors = data.errors || []
    return `카페 원고 완료: ${data.processed}개 지점, ${data.total_articles}건` + (errors.length ? ` (오류 ${errors.length}건)` : '')
  })
}

// 블로그 Notion 동기화
const notionToken = ref('')
const notionSyncing = ref(false)
const notionSyncResult = ref<any>(null)
const notionSyncStatus = ref<any>(null)
const notionTokenStatus = ref<any>(null)
const notionTokenSaving = ref(false)
const showNotionTokenInput = ref(false)

async function loadNotionSyncStatus() {
  try {
    const [syncRes, tokenRes] = await Promise.all([
      blogApi.getNotionSyncStatus(),
      blogApi.getNotionTokenStatus(),
    ])
    notionSyncStatus.value = syncRes.data?.last_sync || null
    notionTokenStatus.value = tokenRes.data
  } catch (e) {
    console.error(e)
  }
}

async function saveNotionToken() {
  if (!notionToken.value.trim()) return
  notionTokenSaving.value = true
  try {
    const { data } = await blogApi.saveNotionToken(notionToken.value.trim())
    notionTokenStatus.value = { saved: true, masked: data.masked }
    notionToken.value = ''
    showNotionTokenInput.value = false
    notionSyncResult.value = { message: data.message, updated: true }
  } catch (e: any) {
    notionSyncResult.value = { message: e.response?.data?.detail || '토큰 저장 실패' }
  } finally {
    notionTokenSaving.value = false
  }
}

async function syncNotion() {
  notionSyncing.value = true
  notionSyncResult.value = null
  try {
    const token = notionToken.value.trim() || undefined
    const { data } = await blogApi.syncNotion(token)
    notionSyncResult.value = data
    loadNotionSyncStatus()
  } catch (e: any) {
    notionSyncResult.value = { message: e.response?.data?.detail || '동기화 실패' }
  } finally {
    notionSyncing.value = false
  }
}

// 블로그 제목 스크래핑
const scrapeStatus = ref<any>(null)
const scraping = ref(false)
const scrapeResult = ref<any>(null)

async function loadScrapeStatus() {
  try {
    const { data } = await blogApi.getScrapeTitlesStatus()
    scrapeStatus.value = data
  } catch (e) {
    console.error(e)
  }
}

async function runScrape(includeCafe: boolean = false) {
  scraping.value = true
  scrapeResult.value = null
  try {
    const { data } = await blogApi.scrapeTitles({ limit: 0, delay: 0.3, include_cafe: includeCafe })
    scrapeResult.value = data
    loadScrapeStatus()
  } catch (e: any) {
    scrapeResult.value = { message: e.response?.data?.detail || '스크래핑 실패' }
  } finally {
    scraping.value = false
  }
}

// 블로그 데이터 임포트 (로컬 덤프 → 서버 DB)
const importing = ref(false)
const importResult = ref<any>(null)

async function importBlogData() {
  importing.value = true
  importResult.value = null
  try {
    const { data } = await blogApi.importBlogData()
    importResult.value = { ok: true, message: data.message }
    loadScrapeStatus()
  } catch (e: any) {
    importResult.value = { ok: false, message: e.response?.data?.detail || '임포트 실패' }
  } finally {
    importing.value = false
  }
}

// 블로그 CSV 업로드
const blogCsvMsg = ref('')
const blogCsvUploading = ref(false)

async function uploadBlogCsv(e: Event) {
  const target = e.target as HTMLInputElement
  const file = target.files?.[0]
  if (!file) return
  blogCsvUploading.value = true
  blogCsvMsg.value = ''
  try {
    const { data } = await blogApi.uploadBlogCsv(file)
    blogCsvMsg.value = data.output || data.message || '업로드 완료'
  } catch (err: any) {
    blogCsvMsg.value = '오류: ' + (err.response?.data?.detail || err.message)
  } finally {
    blogCsvUploading.value = false
    target.value = ''
  }
}

// DB 파일 관리
const dbUploading = ref(false)
const dbMsg = ref('')
const dbResult = ref<any>(null)

async function uploadDb(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  dbUploading.value = true
  dbMsg.value = ''
  dbResult.value = null
  try {
    const formData = new FormData()
    formData.append('file', file)
    const res = await equipApi.uploadDb(formData)
    dbResult.value = res.data
    dbMsg.value = `DB 업로드 완료 (시술사전: ${res.data.device_info_count}건, 논문: ${res.data.papers_count}건)`
  } catch (e: any) {
    dbMsg.value = '오류: ' + (e.response?.data?.detail || e.message)
  } finally {
    dbUploading.value = false
    input.value = ''
  }
}

async function downloadDb() {
  try {
    const res = await equipApi.downloadDb()
    const blob = new Blob([res.data])
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'equipment.db'
    a.click()
    URL.revokeObjectURL(url)
  } catch (e: any) {
    dbMsg.value = '다운로드 오류: ' + (e.response?.data?.detail || e.message)
  }
}

// Google 인증 파일
const credUploading = ref(false)
const credMsg = ref('')

async function uploadCred(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  credUploading.value = true
  credMsg.value = ''
  try {
    const formData = new FormData()
    formData.append('file', file)
    const res = await equipApi.uploadCredentials(formData)
    credMsg.value = `업로드 완료: ${res.data.client_email} (${res.data.project_id})`
  } catch (e: any) {
    credMsg.value = '오류: ' + (e.response?.data?.detail || e.message)
  } finally {
    credUploading.value = false
    input.value = ''
  }
}

// 데이터 품질 현황
const qualitySummary = ref<any>(null)
const qualityDetails = ref<any>(null)
const qualityDetailCategory = ref('')
const qualityLoading = ref(false)

async function loadQuality() {
  try {
    const { data } = await blogApi.getDataQuality()
    qualitySummary.value = data
  } catch (e) { console.error(e) }
}

async function showDetails(category: string) {
  if (qualityDetailCategory.value === category) {
    qualityDetailCategory.value = ''
    qualityDetails.value = null
    return
  }
  qualityDetailCategory.value = category
  qualityLoading.value = true
  try {
    const { data } = await blogApi.getDataQualityDetails(category, 50)
    qualityDetails.value = data
  } catch (e) { console.error(e) }
  finally { qualityLoading.value = false }
}

onMounted(() => {
  loadNotionSyncStatus()
  loadScrapeStatus()
  loadQuality()
})
</script>

<template>
  <div class="max-w-3xl space-y-2.5">
    <!-- 전역 알림 -->
    <div v-if="syncMsg" class="px-3 py-2 bg-emerald-50 border border-emerald-200 rounded text-sm text-emerald-700">{{ syncMsg }}</div>
    <div v-if="syncError" class="px-3 py-2 bg-red-50 border border-red-200 rounded text-sm text-red-700">{{ syncError }}</div>

    <!-- ═══ E 보유장비 ═══ -->
    <div class="space-y-1.5">
    <div class="text-xs font-bold text-slate-400 tracking-wide pl-1">E 보유장비</div>
    <div class="bg-white border border-slate-200 rounded-lg px-4 py-2.5 hover:border-slate-300 transition-colors">
      <div class="flex items-center gap-3">
        <span class="w-1 self-stretch rounded-full bg-blue-400 flex-shrink-0"></span>
        <div>
          <div class="text-sm font-semibold text-slate-700">보유장비 시트 동기화</div>
          <div class="text-xs text-slate-400">Google Sheets에서 장비 데이터를 가져옵니다</div>
        </div>
        <button @click="syncEquipment" :disabled="syncing"
          class="ml-auto px-4 py-1.5 bg-blue-600 text-white text-xs rounded hover:bg-blue-700 disabled:opacity-50 whitespace-nowrap">
          {{ syncing ? '동기화 중...' : '동기화' }}
        </button>
      </div>
    </div>

    </div>

    <!-- ═══ V 이벤트 ═══ -->
    <div class="space-y-1.5">
    <div class="text-xs font-bold text-slate-400 tracking-wide pl-1">V 이벤트</div>
    <div class="bg-white border border-slate-200 rounded-lg px-4 py-2.5 hover:border-slate-300 transition-colors">
      <div class="flex items-center gap-3">
        <span class="w-1 self-stretch rounded-full bg-violet-400 flex-shrink-0"></span>
        <div>
          <div class="text-sm font-semibold text-slate-700">유앤아이 지점별 이벤트 시트 갱신</div>
          <div class="text-xs text-slate-400">{{ evtYear }}년 {{ evtStartMonth }}~{{ evtEndMonth }}월 이벤트 데이터</div>
        </div>
        <div class="ml-auto flex items-center gap-2 text-xs">
          <label class="flex items-center gap-1"><input type="radio" v-model="evtSyncMethod" value="url" class="w-3 h-3" /> 링크</label>
          <label class="flex items-center gap-1"><input type="radio" v-model="evtSyncMethod" value="file" class="w-3 h-3" /> 파일</label>
          <button @click="syncEvents" :disabled="syncing"
            class="px-4 py-1.5 bg-blue-600 text-white text-xs rounded hover:bg-blue-700 disabled:opacity-50 whitespace-nowrap">
            {{ syncing ? '수집 중...' : '수집' }}
          </button>
        </div>
      </div>
      <div class="mt-2 ml-4">
        <input v-if="evtSyncMethod === 'url'" v-model="evtSheetUrl" placeholder="Google Sheets URL"
          class="w-full px-2.5 py-1.5 border border-slate-300 rounded text-sm focus:border-blue-400 focus:outline-none" />
        <input v-else type="file" accept=".xlsx,.xls" @change="onEvtFileChange"
          class="w-full text-sm text-slate-500 file:mr-2 file:py-1 file:px-2.5 file:rounded file:border-0 file:bg-slate-100 file:text-xs" />
      </div>
    </div>

    </div>

    <!-- ═══ T 시술정보 ═══ -->
    <div class="space-y-1.5">
    <div class="text-xs font-bold text-slate-400 tracking-wide pl-1">T 시술정보</div>
    <div class="bg-white border border-slate-200 rounded-lg px-4 py-2.5 hover:border-slate-300 transition-colors">
      <div class="flex items-center gap-3">
        <span class="w-1 self-stretch rounded-full bg-teal-400 flex-shrink-0"></span>
        <div>
          <div class="text-sm font-semibold text-slate-700">시술사전 · 논문 DB 동기화</div>
          <div class="text-xs text-slate-400">로컬 DB 파일을 서버에 업로드하거나 다운로드합니다</div>
        </div>
        <div class="ml-auto flex gap-2">
          <label class="px-3 py-1.5 bg-blue-600 text-white text-xs rounded cursor-pointer hover:bg-blue-700"
            :class="{ 'opacity-50 pointer-events-none': dbUploading }">
            {{ dbUploading ? '업로드 중...' : 'DB 업로드' }}
            <input type="file" accept=".db" class="hidden" @change="uploadDb" :disabled="dbUploading" />
          </label>
          <button @click="downloadDb" class="px-3 py-1.5 bg-slate-500 text-white text-xs rounded hover:bg-slate-600">DB 다운로드</button>
        </div>
      </div>
      <div v-if="dbMsg" class="mt-2 ml-4 px-2 py-1 rounded text-xs inline-block"
        :class="dbMsg.startsWith('오류') ? 'bg-red-50 text-red-700' : 'bg-emerald-50 text-emerald-700'">{{ dbMsg }}</div>
    </div>

    </div>

    <!-- ═══ C 카페 ═══ -->
    <div class="space-y-1.5">
    <div class="text-xs font-bold text-slate-400 tracking-wide pl-1">C 카페</div>
    <div class="bg-white border border-slate-200 rounded-lg px-4 py-2.5 hover:border-slate-300 transition-colors">
      <div class="flex items-center gap-3">
        <span class="w-1 self-stretch rounded-full bg-orange-400 flex-shrink-0"></span>
        <div>
          <div class="text-sm font-semibold text-slate-700">유앤아이 카페 원고 불러오기</div>
          <div class="text-xs text-slate-400">{{ now.getMonth() + 1 }}월 원고</div>
        </div>
        <div class="ml-auto flex items-center gap-2">
          <select v-model="cafeBranch" class="px-2 py-1 border border-slate-300 rounded text-xs">
            <option value="">전체 지점</option>
            <option v-for="b in props.branches" :key="b.id" :value="b.name">{{ b.name }}</option>
          </select>
          <button @click="syncCafe" :disabled="syncing"
            class="px-4 py-1.5 bg-blue-600 text-white text-xs rounded hover:bg-blue-700 disabled:opacity-50 whitespace-nowrap">
            {{ syncing ? '가져오는 중...' : '가져오기' }}
          </button>
        </div>
      </div>
      <div class="mt-2 ml-4">
        <input v-model="cafeSheetUrl" placeholder="Google Sheets URL"
          class="w-full px-2.5 py-1.5 border border-slate-300 rounded text-sm focus:border-blue-400 focus:outline-none" />
      </div>
    </div>

    </div>

    <!-- ═══ B 블로그 ═══ -->
    <div class="space-y-1.5">
    <div class="text-xs font-bold text-slate-400 tracking-wide pl-1">B 블로그</div>
    <div class="bg-white border border-slate-200 rounded-lg px-4 py-2.5 hover:border-slate-300 transition-colors">
      <div class="flex items-center gap-3">
        <span class="w-1 self-stretch rounded-full bg-sky-400 flex-shrink-0"></span>
        <div>
          <div class="text-sm font-semibold text-slate-700">블로그 Notion 동기화</div>
          <div class="text-xs text-slate-400">
            <template v-if="notionSyncStatus">{{ notionSyncStatus.synced_at?.slice(0, 16) }} · {{ notionSyncStatus.notion_pages?.toLocaleString() }}건</template>
            <template v-else-if="notionTokenStatus?.saved">동기화 기록 없음</template>
            <template v-else>토큰 미등록 — 아래에서 토큰을 저장해주세요</template>
          </div>
        </div>
        <div class="ml-auto flex items-center gap-2">
          <button v-if="notionTokenStatus?.saved" @click="showNotionTokenInput = !showNotionTokenInput"
            class="px-2 py-1 text-slate-400 hover:text-slate-600 text-xs">{{ showNotionTokenInput ? '닫기' : '토큰 변경' }}</button>
          <button @click="syncNotion" :disabled="notionSyncing || (!notionTokenStatus?.saved && !notionToken.trim())"
            class="px-4 py-1.5 bg-slate-700 text-white text-xs rounded hover:bg-slate-800 disabled:opacity-40 whitespace-nowrap">
            {{ notionSyncing ? '동기화 중...' : '증분 동기화' }}
          </button>
        </div>
      </div>
      <div v-if="!notionTokenStatus?.saved || showNotionTokenInput" class="mt-2 ml-4">
        <div class="flex items-center gap-2">
          <input v-model="notionToken" type="password" placeholder="Notion 토큰 (ntn_...)"
            class="flex-1 border border-slate-300 rounded px-2.5 py-1.5 text-sm focus:border-blue-400 focus:outline-none" />
          <button v-if="notionToken.trim()" @click="saveNotionToken" :disabled="notionTokenSaving"
            class="px-3 py-1.5 bg-emerald-600 text-white text-xs rounded hover:bg-emerald-700 disabled:opacity-40 whitespace-nowrap">
            {{ notionTokenSaving ? '저장 중...' : '토큰 저장' }}
          </button>
        </div>
        <p class="text-xs text-slate-400 mt-1">
          <a href="https://www.notion.so/profile/integrations" target="_blank" class="text-blue-500 hover:underline">Notion 내 통합 관리</a>에서
          Internal Integration 생성 후 토큰(ntn_...)을 복사하세요. 대상 DB 페이지에서 연결(Connect)도 필요합니다.
        </p>
      </div>
      <div v-if="notionSyncResult" class="mt-2 ml-4 text-xs px-2 py-1 rounded inline-block"
        :class="notionSyncResult.updated != null ? 'bg-emerald-50 text-emerald-700' : 'bg-red-50 text-red-600'">{{ notionSyncResult.message }}</div>
    </div>

    <!-- B 블로그 원고 제목 수집 -->
    <div class="bg-white border border-slate-200 rounded-lg px-4 py-2.5 hover:border-slate-300 transition-colors">
      <div class="flex items-center gap-3">
        <span class="w-1 self-stretch rounded-full bg-sky-400 flex-shrink-0"></span>
        <div>
          <div class="text-sm font-semibold text-slate-700">블로그 원고 제목 수집</div>
          <div v-if="scrapeStatus" class="text-xs text-slate-400">
            수집 {{ scrapeStatus.already_scraped?.toLocaleString() }}건
            <template v-if="scrapeStatus.remaining > 0">
              / 남은 블로그 <span class="text-amber-600 font-medium">{{ scrapeStatus.remaining_blog?.toLocaleString() }}건</span>
              <template v-if="scrapeStatus.remaining_cafe > 0"> · 카페 {{ scrapeStatus.remaining_cafe?.toLocaleString() }}건</template>
            </template>
          </div>
        </div>
        <div class="ml-auto flex gap-2">
          <button @click="runScrape(false)" :disabled="scraping || !scrapeStatus?.remaining_blog"
            class="px-3 py-1.5 bg-blue-600 text-white text-xs rounded hover:bg-blue-700 disabled:opacity-40 whitespace-nowrap">
            {{ scraping ? '수집 중...' : '블로그만' }}
          </button>
          <button @click="runScrape(true)" :disabled="scraping || !scrapeStatus?.remaining"
            class="px-3 py-1.5 bg-slate-600 text-white text-xs rounded hover:bg-slate-700 disabled:opacity-40 whitespace-nowrap">카페 포함</button>
        </div>
      </div>
      <div v-if="scrapeResult" class="mt-2 ml-4 text-xs px-2 py-1 rounded inline-block"
        :class="scrapeResult.scraped != null ? 'bg-emerald-50 text-emerald-700' : 'bg-red-50 text-red-600'">
        {{ scrapeResult.message }}
        <span v-if="scrapeResult.scraped != null" class="text-slate-500 ml-1">({{ scrapeResult.scraped }}수집 / {{ scrapeResult.failed }}실패 / {{ scrapeResult.deleted }}삭제)</span>
      </div>
    </div>

    <!-- B 블로그 데이터 임포트 -->
    <div class="bg-white border border-slate-200 rounded-lg px-4 py-2.5 hover:border-slate-300 transition-colors">
      <div class="flex items-center gap-3">
        <span class="w-1 self-stretch rounded-full bg-sky-400 flex-shrink-0"></span>
        <div>
          <div class="text-sm font-semibold text-slate-700">블로그 데이터 임포트</div>
          <div class="text-xs text-slate-400">로컬에서 수집한 블로그 데이터를 서버 DB에 반영합니다</div>
        </div>
        <button @click="importBlogData" :disabled="importing"
          class="ml-auto px-4 py-1.5 bg-indigo-600 text-white text-xs rounded hover:bg-indigo-700 disabled:opacity-40 whitespace-nowrap">
          {{ importing ? '임포트 중...' : '데이터 임포트' }}
        </button>
      </div>
      <div v-if="importResult" class="mt-2 ml-4 text-xs px-2 py-1 rounded inline-block"
        :class="importResult.ok ? 'bg-emerald-50 text-emerald-700' : 'bg-red-50 text-red-600'">{{ importResult.message }}</div>
    </div>

    <!-- B 블로그 CSV 업로드 -->
    <div class="bg-white border border-slate-200 rounded-lg px-4 py-2.5 hover:border-slate-300 transition-colors">
      <div class="flex items-center gap-3">
        <span class="w-1 self-stretch rounded-full bg-sky-400 flex-shrink-0"></span>
        <div>
          <div class="text-sm font-semibold text-slate-700">블로그 게시글 CSV 업로드</div>
          <div class="text-xs text-slate-400">노션에서 내보낸 CSV 파일 · 중복 항목은 자동 건너뜀</div>
        </div>
        <label class="ml-auto px-4 py-1.5 bg-blue-600 text-white text-xs rounded cursor-pointer hover:bg-blue-700 whitespace-nowrap"
          :class="{ 'opacity-50 pointer-events-none': blogCsvUploading }">
          {{ blogCsvUploading ? '업로드 중...' : 'CSV 파일 선택' }}
          <input type="file" accept=".csv" class="hidden" @change="uploadBlogCsv" :disabled="blogCsvUploading" />
        </label>
      </div>
      <div v-if="blogCsvMsg" class="mt-2 ml-4 text-xs px-2 py-1 rounded inline-block whitespace-pre-line"
        :class="blogCsvMsg.startsWith('오류') ? 'bg-red-50 text-red-700' : 'bg-emerald-50 text-emerald-700'">{{ blogCsvMsg }}</div>
    </div>

    </div>

    <!-- ═══ 공통 설정 ═══ -->
    <div class="space-y-1.5">
    <div class="text-xs font-bold text-slate-400 tracking-wide pl-1">공통 설정</div>
    <div class="bg-white border border-slate-200 rounded-lg px-4 py-2.5 hover:border-slate-300 transition-colors">
      <div class="flex items-center gap-3">
        <span class="w-1 self-stretch rounded-full bg-amber-400 flex-shrink-0"></span>
        <div>
          <div class="text-sm font-semibold text-slate-700">Google 서비스 인증 파일</div>
          <div class="text-xs text-slate-400">보유장비 · 이벤트 · 카페 시트 동기화에 필요 (최초 1회)</div>
        </div>
        <label class="ml-auto px-4 py-1.5 bg-amber-600 text-white text-xs rounded cursor-pointer hover:bg-amber-700 whitespace-nowrap"
          :class="{ 'opacity-50 pointer-events-none': credUploading }">
          {{ credUploading ? '업로드 중...' : 'credentials.json 업로드' }}
          <input type="file" accept=".json" class="hidden" @change="uploadCred" :disabled="credUploading" />
        </label>
      </div>
      <div v-if="credMsg" class="mt-2 ml-4 px-2 py-1 rounded text-xs inline-block"
        :class="credMsg.startsWith('오류') ? 'bg-red-50 text-red-700' : 'bg-emerald-50 text-emerald-700'">{{ credMsg }}</div>
    </div>
    </div>

    <!-- ── 데이터 품질 현황 ── -->
    <div class="border border-slate-200 rounded-lg overflow-hidden">
      <div class="px-4 py-3 bg-slate-50 border-b border-slate-200">
        <div class="flex items-center justify-between">
          <div>
            <div class="text-sm font-semibold text-slate-700">📊 블로그 데이터 품질</div>
            <div class="text-xs text-slate-400">총 {{ qualitySummary?.total?.toLocaleString() ?? '-' }}건 기준</div>
          </div>
          <button @click="loadQuality" class="text-xs text-blue-600 hover:text-blue-800">새로고침</button>
        </div>
      </div>

      <div v-if="qualitySummary" class="divide-y divide-slate-100">
        <!-- 삭제된 글 -->
        <button @click="showDetails('deleted')"
          class="w-full flex items-center justify-between px-4 py-2.5 hover:bg-slate-50 transition text-left">
          <div class="flex items-center gap-2">
            <span class="w-2 h-2 rounded-full bg-red-400"></span>
            <span class="text-sm text-slate-700">삭제된 글</span>
            <span class="text-xs text-slate-400">블로그가 실제로 삭제되어 404 반환</span>
          </div>
          <span class="text-sm font-bold text-red-500">{{ qualitySummary.deleted?.toLocaleString() }}건</span>
        </button>

        <!-- 카페 수집불가 -->
        <button @click="showDetails('cafe_fail')"
          class="w-full flex items-center justify-between px-4 py-2.5 hover:bg-slate-50 transition text-left">
          <div class="flex items-center gap-2">
            <span class="w-2 h-2 rounded-full bg-amber-400"></span>
            <span class="text-sm text-slate-700">카페 수집불가</span>
            <span class="text-xs text-slate-400">카페 URL은 로그인 필요하여 제목 추출 불가</span>
          </div>
          <span class="text-sm font-bold text-amber-500">{{ qualitySummary.cafe_fail?.toLocaleString() }}건</span>
        </button>

        <!-- 검토 필요 -->
        <button @click="showDetails('needs_review')"
          class="w-full flex items-center justify-between px-4 py-2.5 hover:bg-slate-50 transition text-left">
          <div class="flex items-center gap-2">
            <span class="w-2 h-2 rounded-full bg-purple-400"></span>
            <span class="text-sm text-slate-700">검토 필요</span>
            <span class="text-xs text-slate-400">제목에 URL이 포함되거나 이상 데이터</span>
          </div>
          <span class="text-sm font-bold text-purple-500">{{ qualitySummary.needs_review?.toLocaleString() }}건</span>
        </button>

        <!-- 제목 미수집 -->
        <button @click="showDetails('no_title')"
          class="w-full flex items-center justify-between px-4 py-2.5 hover:bg-slate-50 transition text-left">
          <div class="flex items-center gap-2">
            <span class="w-2 h-2 rounded-full bg-slate-400"></span>
            <span class="text-sm text-slate-700">제목 미수집</span>
            <span class="text-xs text-slate-400">스크래핑 실패 또는 미실행</span>
          </div>
          <span class="text-sm font-bold text-slate-500">{{ qualitySummary.no_title?.toLocaleString() }}건</span>
        </button>

        <!-- 지점 미매핑 -->
        <button @click="showDetails('no_branch')"
          class="w-full flex items-center justify-between px-4 py-2.5 hover:bg-slate-50 transition text-left">
          <div class="flex items-center gap-2">
            <span class="w-2 h-2 rounded-full bg-sky-400"></span>
            <span class="text-sm text-slate-700">지점 미매핑 (유앤아이)</span>
            <span class="text-xs text-slate-400">evt_branches와 연결 안 된 유앤아이 글</span>
          </div>
          <span class="text-sm font-bold text-sky-500">{{ qualitySummary.no_branch?.toLocaleString() }}건</span>
        </button>
      </div>

      <!-- 상세 목록 (클릭 시 펼침) -->
      <div v-if="qualityDetailCategory" class="border-t border-slate-200 bg-white">
        <div class="px-4 py-2 bg-slate-50 text-xs font-semibold text-slate-500 flex justify-between">
          <span>{{ {deleted:'삭제된 글',cafe_fail:'카페 수집불가',needs_review:'검토 필요',no_title:'제목 미수집',no_branch:'지점 미매핑'}[qualityDetailCategory] }} 상세</span>
          <span v-if="qualityDetails">{{ qualityDetails.total }}건 중 {{ qualityDetails.items?.length }}건 표시</span>
        </div>
        <div v-if="qualityLoading" class="px-4 py-4 text-sm text-slate-400 text-center">로딩 중...</div>
        <div v-else-if="qualityDetails?.items?.length" class="max-h-80 overflow-auto">
          <table class="w-full text-xs">
            <thead class="bg-slate-50 sticky top-0">
              <tr>
                <th class="text-left px-3 py-1.5 text-slate-500 font-medium">채널</th>
                <th class="text-left px-3 py-1.5 text-slate-500 font-medium">제목/키워드</th>
                <th class="text-left px-3 py-1.5 text-slate-500 font-medium">지점</th>
                <th class="text-left px-3 py-1.5 text-slate-500 font-medium">날짜</th>
                <th class="text-left px-3 py-1.5 text-slate-500 font-medium">상태</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-50">
              <tr v-for="item in qualityDetails.items" :key="item.id" class="hover:bg-slate-50">
                <td class="px-3 py-1.5">
                  <span class="px-1.5 py-0.5 rounded-full text-[10px] font-medium"
                    :class="item.blog_channel === 'br' ? 'bg-emerald-50 text-emerald-600' : item.blog_channel === 'opt' ? 'bg-violet-50 text-violet-600' : 'bg-slate-100 text-slate-500'">
                    {{ item.blog_channel === 'br' ? '브블' : item.blog_channel === 'opt' ? '최블' : item.blog_channel || '-' }}
                  </span>
                </td>
                <td class="px-3 py-1.5 max-w-xs truncate">
                  <a v-if="item.published_url" :href="item.published_url" target="_blank"
                    class="text-slate-700 hover:text-blue-600">
                    {{ item.title || item.keyword || '(없음)' }}
                  </a>
                  <span v-else class="text-slate-500">{{ item.title || item.keyword || '(없음)' }}</span>
                </td>
                <td class="px-3 py-1.5 text-slate-400">{{ item.branch_name || '-' }}</td>
                <td class="px-3 py-1.5 text-slate-400">{{ item.published_at?.slice(0, 10) || '-' }}</td>
                <td class="px-3 py-1.5">
                  <span v-if="item.scraped_title === '(삭제됨)'" class="text-red-400">삭제됨</span>
                  <span v-else-if="item.scraped_title === '(카페-수집불가)'" class="text-amber-400">수집불가</span>
                  <span v-else-if="item.needs_review" class="text-purple-400">검토필요</span>
                  <span v-else class="text-slate-300">—</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <p v-else class="px-4 py-3 text-xs text-slate-400">데이터 없음</p>
      </div>
    </div>

  </div>
</template>

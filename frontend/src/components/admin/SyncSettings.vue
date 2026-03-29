<script setup lang="ts">
import { ref, computed } from 'vue'
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
</script>

<template>
  <div class="space-y-6">
    <!-- 알림 -->
    <div v-if="syncMsg" class="px-4 py-2 bg-emerald-50 border border-emerald-200 rounded text-sm text-emerald-700">{{ syncMsg }}</div>
    <div v-if="syncError" class="px-4 py-2 bg-red-50 border border-red-200 rounded text-sm text-red-700">{{ syncError }}</div>

    <!-- ① 구글 시트 동기화 -->
    <div class="bg-white border border-slate-200 rounded-lg p-4">
      <div class="flex items-center justify-between mb-3">
        <div>
          <h3 class="text-sm font-bold text-slate-700">구글 장비시트 데이터 동기화</h3>
          <p class="text-xs text-slate-400 mt-0.5">Google Sheets에서 보유장비 데이터를 가져옵니다.</p>
        </div>
        <button @click="syncEquipment" :disabled="syncing"
          class="px-4 py-1.5 bg-blue-600 text-white text-xs rounded hover:bg-blue-700 disabled:opacity-50 whitespace-nowrap">
          {{ syncing ? '동기화 중...' : '장비 동기화' }}
        </button>
      </div>
    </div>

    <!-- ② 이벤트 동기화 -->
    <div class="bg-white border border-slate-200 rounded-lg p-4">
      <div class="flex items-center justify-between mb-2">
        <div>
          <h3 class="text-sm font-bold text-slate-700">유앤아이 지점별 이벤트 데이터 동기화</h3>
          <p class="text-xs text-slate-400 mt-0.5">마지막 갱신: <strong>{{ evtYear }}년 {{ evtStartMonth }}-{{ evtEndMonth }}월</strong></p>
        </div>
        <button @click="syncEvents" :disabled="syncing"
          class="px-4 py-1.5 bg-blue-600 text-white text-xs rounded hover:bg-blue-700 disabled:opacity-50 whitespace-nowrap">
          {{ syncing ? '수집 중...' : '이벤트 수집' }}
        </button>
      </div>
      <div class="flex gap-3 items-center text-xs">
        <label class="flex items-center gap-1">
          <input type="radio" v-model="evtSyncMethod" value="url" /> 링크
        </label>
        <label class="flex items-center gap-1">
          <input type="radio" v-model="evtSyncMethod" value="file" /> 파일
        </label>
        <input v-if="evtSyncMethod === 'url'" v-model="evtSheetUrl" placeholder="Google Sheets URL"
          class="flex-1 px-2 py-1 border border-slate-300 rounded text-xs" />
        <input v-else type="file" accept=".xlsx,.xls" @change="onEvtFileChange"
          class="flex-1 text-xs text-slate-500 file:mr-2 file:py-0.5 file:px-2 file:rounded file:border-0 file:bg-slate-100 file:text-xs" />
      </div>
    </div>

    <!-- ③ 카페 원고 -->
    <div class="bg-white border border-slate-200 rounded-lg p-4">
      <div class="flex items-center justify-between mb-2">
        <h3 class="text-sm font-bold text-slate-700">카페 원고 가져오기</h3>
        <button @click="syncCafe" :disabled="syncing"
          class="px-4 py-1.5 bg-blue-600 text-white text-xs rounded hover:bg-blue-700 disabled:opacity-50 whitespace-nowrap">
          {{ syncing ? '가져오는 중...' : '원고 가져오기' }}
        </button>
      </div>
      <div class="flex gap-3 items-center text-xs">
        <input v-model="cafeSheetUrl" placeholder="Google Sheets URL" class="flex-1 px-2 py-1 border border-slate-300 rounded text-xs" />
        <select v-model="cafeBranch" class="px-2 py-1 border border-slate-300 rounded text-xs">
          <option value="">전체 지점</option>
          <option v-for="b in props.branches" :key="b.id" :value="b.name">{{ b.name }}</option>
        </select>
      </div>
    </div>

    <!-- ④ 시술사전 & 논문 DB 관리 -->
    <div class="bg-white border border-slate-200 rounded-lg p-4">
      <div class="flex items-center justify-between mb-2">
        <div>
          <h3 class="text-sm font-bold text-slate-700">시술사전 · 논문 DB 관리</h3>
          <p class="text-xs text-slate-400 mt-0.5">로컬에서 작업한 시술사전(device_info)과 논문(papers) 데이터를 서버 DB에 병합합니다. 장비·이벤트·카페 등 기존 데이터는 유지됩니다.</p>
        </div>
      </div>

      <div v-if="dbMsg" class="mb-2 px-3 py-1.5 rounded text-xs"
        :class="dbMsg.startsWith('오류') ? 'bg-red-50 border border-red-200 text-red-700' : 'bg-emerald-50 border border-emerald-200 text-emerald-700'">
        {{ dbMsg }}
      </div>

      <div v-if="dbResult" class="mb-2 px-3 py-1.5 bg-slate-50 border border-slate-200 rounded text-xs text-slate-600">
        <span class="font-semibold text-slate-700">{{ dbResult.message }}</span>
        <span class="ml-2">시술사전 {{ dbResult.device_info_count }}건 · 논문 {{ dbResult.papers_count }}건</span>
      </div>

      <div class="flex gap-2">
        <label class="px-3 py-1.5 bg-blue-600 text-white text-xs rounded cursor-pointer hover:bg-blue-700"
          :class="{ 'opacity-50 pointer-events-none': dbUploading }">
          {{ dbUploading ? '업로드 중...' : 'DB 업로드' }}
          <input type="file" accept=".db" class="hidden" @change="uploadDb" :disabled="dbUploading" />
        </label>
        <button @click="downloadDb"
          class="px-3 py-1.5 bg-slate-500 text-white text-xs rounded hover:bg-slate-600">
          DB 다운로드
        </button>
      </div>
    </div>

    <!-- ⑤ 블로그 CSV 업로드 -->
    <div class="bg-white border border-slate-200 rounded-lg p-4">
      <div class="flex items-center justify-between mb-2">
        <div>
          <h3 class="text-sm font-bold text-slate-700">블로그 게시글 CSV 업로드</h3>
          <p class="text-xs text-slate-400 mt-0.5">노션에서 내보낸 블로그 게시글 CSV를 업로드합니다. 기존 데이터와 중복되는 항목은 자동으로 건너뜁니다.</p>
        </div>
      </div>

      <div v-if="blogCsvMsg" class="mb-2 px-3 py-1.5 rounded text-xs whitespace-pre-line"
        :class="blogCsvMsg.startsWith('오류') ? 'bg-red-50 border border-red-200 text-red-700' : 'bg-emerald-50 border border-emerald-200 text-emerald-700'">
        {{ blogCsvMsg }}
      </div>

      <label class="px-3 py-1.5 bg-blue-600 text-white text-xs rounded cursor-pointer hover:bg-blue-700"
        :class="{ 'opacity-50 pointer-events-none': blogCsvUploading }">
        {{ blogCsvUploading ? '업로드 중...' : 'CSV 업로드' }}
        <input type="file" accept=".csv" class="hidden" @change="uploadBlogCsv" :disabled="blogCsvUploading" />
      </label>
    </div>

    <!-- ⑥ Google 인증 -->
    <div class="bg-white border border-slate-200 rounded-lg p-4">
      <div class="flex items-center justify-between">
        <div>
          <h3 class="text-sm font-bold text-slate-700">Google 인증 파일</h3>
          <p class="text-xs text-slate-400 mt-0.5">장비·이벤트·카페 시트 동기화에 필요합니다. 최초 1회 업로드하면 이후 자동 적용됩니다.</p>
        </div>
        <label class="px-3 py-1.5 bg-amber-600 text-white text-xs rounded cursor-pointer hover:bg-amber-700 whitespace-nowrap"
          :class="{ 'opacity-50 pointer-events-none': credUploading }">
          {{ credUploading ? '업로드 중...' : 'credentials.json 업로드' }}
          <input type="file" accept=".json" class="hidden" @change="uploadCred" :disabled="credUploading" />
        </label>
      </div>
      <div v-if="credMsg" class="mt-2 px-3 py-1.5 rounded text-xs"
        :class="credMsg.startsWith('오류') ? 'bg-red-50 border border-red-200 text-red-700' : 'bg-emerald-50 border border-emerald-200 text-emerald-700'">
        {{ credMsg }}
      </div>
    </div>
  </div>
</template>

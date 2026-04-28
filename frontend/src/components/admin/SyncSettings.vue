<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import * as equipApi from '@/api/equipment'
import * as eventsApi from '@/api/events'
import * as cafeApi from '@/api/cafe'
import * as blogApi from '@/api/blog'
import * as placeApi from '@/api/place'
import { useAsyncAction } from '@/composables/useAsyncAction'

const props = defineProps<{ branches: { id: number; name: string }[] }>()

const { loading: syncing, message: syncMsg, error: syncError, execute: executeSync } = useAsyncAction()

// 일간 동기화
const dailyRunning = ref(false)
const dailyResult = ref<any>(null)
const dailyLabels: Record<string, string> = {
  blog_sync: '블로그 노션 동기화',
  place_snapshot: '플레이스 스냅샷',
  webpage_snapshot: '웹페이지 스냅샷',
  title_scrape: '제목 스크래핑',
}

async function runDaily() {
  dailyRunning.value = true
  dailyResult.value = null
  try {
    const { data } = await blogApi.runDailySync()
    dailyResult.value = data
  } catch (e: any) {
    dailyResult.value = { error: { ok: false, message: e.response?.data?.detail || '실행 실패' } }
  } finally {
    dailyRunning.value = false
  }
}

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

// 플레이스 오염 데이터 정리
const cleanupLoading = ref(false)

async function handleCleanupPollution() {
  cleanupLoading.value = true
  try {
    const { data } = await placeApi.cleanupPollution(true)
    if (data.total === 0) {
      alert('정리할 데이터가 없습니다.')
      return
    }
    const msg =
      `place_daily: ${data.affected.place_daily}행, ` +
      `place_branch_monthly: ${data.affected.place_branch_monthly}행, ` +
      `agency_map_history: ${data.affected.agency_map_history}행\n` +
      `총 ${data.total}행이 삭제됩니다. 계속하시겠습니까?`
    if (!confirm(msg)) return
    const { data: result } = await placeApi.cleanupPollution(false)
    alert(`정리 완료: 총 ${result.total}행 삭제됨`)
  } catch (e: any) {
    alert('오류: ' + (e.response?.data?.detail || '정리 실패'))
  } finally {
    cleanupLoading.value = false
  }
}

onMounted(() => {})
</script>

<template>
  <div class="max-w-3xl space-y-2.5">
    <!-- 전역 알림 -->
    <div v-if="syncMsg" class="px-3 py-2 bg-emerald-50 border border-emerald-200 rounded text-sm text-emerald-700">{{ syncMsg }}</div>
    <div v-if="syncError" class="px-3 py-2 bg-red-50 border border-red-200 rounded text-sm text-red-700">{{ syncError }}</div>

    <!-- 일간 동기화 -->
    <div class="border border-blue-200 rounded-lg bg-blue-50 p-4 mb-4">
      <div class="flex items-center justify-between">
        <div>
          <h3 class="text-sm font-bold text-blue-800">일간 동기화</h3>
          <p class="text-xs text-blue-500 mt-0.5">블로그 노션 동기화 + 플레이스/웹페이지 스냅샷 + 제목 스크래핑</p>
        </div>
        <button @click="runDaily" :disabled="dailyRunning"
          class="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50">
          {{ dailyRunning ? '실행 중...' : '전체 실행' }}
        </button>
      </div>
      <!-- Results display after running -->
      <div v-if="dailyResult" class="mt-3 space-y-1 text-xs">
        <div v-for="(val, key) in dailyResult" :key="key" class="flex items-center gap-2">
          <span :class="val.ok ? 'text-emerald-600' : 'text-red-500'">{{ val.ok ? '✓' : '✗' }}</span>
          <span class="text-slate-600">{{ dailyLabels[key] || key }}</span>
          <span class="text-slate-400">{{ val.message || '' }}</span>
        </div>
      </div>
    </div>

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

    <!-- ═══ 데이터 정리 ═══ -->
    <div class="space-y-1.5">
    <div class="text-xs font-bold text-slate-400 tracking-wide pl-1">데이터 정리</div>
    <div class="bg-white border border-slate-200 rounded-lg px-4 py-2.5 hover:border-slate-300 transition-colors">
      <div class="flex items-center gap-3">
        <span class="w-1 self-stretch rounded-full bg-amber-500 flex-shrink-0"></span>
        <div>
          <div class="text-sm font-semibold text-slate-700">플레이스 오염 데이터 정리</div>
          <div class="text-xs text-slate-500">시트 입력 오류로 들어온 (휴식) 패턴 데이터를 제거합니다.</div>
        </div>
        <button @click="handleCleanupPollution" :disabled="cleanupLoading"
          class="ml-auto px-4 py-1.5 bg-amber-600 text-white text-sm rounded hover:bg-amber-700 disabled:opacity-40 transition whitespace-nowrap">
          {{ cleanupLoading ? '처리 중...' : '오염 데이터 검사' }}
        </button>
      </div>
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

  </div>
</template>

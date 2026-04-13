<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import * as equipApi from '@/api/equipment'
import * as eventsApi from '@/api/events'
import * as cafeApi from '@/api/cafe'
import * as blogApi from '@/api/blog'
import { fetchAgencyMap, saveAgencyMap } from '@/api/branches'
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

// 실행사 매핑 관리
const agencyTab = ref<'place' | 'webpage'>('place')
const agencyMaps = ref<{ place: Record<string, string>; webpage: Record<string, string> }>({ place: {}, webpage: {} })
const currentAgencyMap = computed(() => agencyMaps.value[agencyTab.value])
const savingAgency = ref(false)
const agencySaveMsg = ref('')
const agencySaveError = ref(false)

async function loadAgencyMaps() {
  try {
    const [place, webpage] = await Promise.all([
      fetchAgencyMap('place').catch(() => ({})),
      fetchAgencyMap('webpage').catch(() => ({})),
    ])
    agencyMaps.value.place = { ...place }
    agencyMaps.value.webpage = { ...webpage }
  } catch {}
}

async function saveAgencyMapHandler() {
  savingAgency.value = true
  agencySaveMsg.value = ''
  agencySaveError.value = false
  try {
    await saveAgencyMap(agencyTab.value, currentAgencyMap.value)
    agencySaveMsg.value = '저장 완료'
  } catch (e: any) {
    agencySaveError.value = true
    agencySaveMsg.value = e.response?.data?.detail || '저장 실패'
  } finally {
    savingAgency.value = false
    setTimeout(() => { agencySaveMsg.value = '' }, 3000)
  }
}

onMounted(() => { loadAgencyMaps() })

// ── 실행사 매핑 신규 computed / methods ──────────────────────────

// 현재 양쪽 탭에서 사용 중인 실행사 이름 목록
const agencyNames = computed(() => {
  const names = new Set<string>()
  for (const map of [agencyMaps.value.place, agencyMaps.value.webpage]) {
    for (const v of Object.values(map)) {
      if (v?.trim()) names.add(v.trim())
    }
  }
  // 직접 추가한 이름도 포함
  if (newAgencyName.value.trim()) names.add(newAgencyName.value.trim())
  return [...names].sort()
})

// 현재 탭의 실행사별 그룹
const agencyGroups = computed(() => {
  const map = currentAgencyMap.value
  const groups: Record<string, string[]> = {}
  const unassigned: string[] = []

  const allBranches = Object.keys(map).sort()

  for (const branch of allBranches) {
    const agency = map[branch]?.trim()
    if (agency) {
      if (!groups[agency]) groups[agency] = []
      groups[agency].push(branch)
    } else {
      unassigned.push(branch)
    }
  }

  return { groups, unassigned }
})

// 새 실행사 이름 입력
const newAgencyName = ref('')

function addAgency() {
  const name = newAgencyName.value.trim()
  if (!name) return
  // 이름은 agencyNames computed 에 반영됨 — 실제 저장은 지점 배정 시
  newAgencyName.value = ''
}

// 지점을 특정 실행사에 배정
function assignBranch(branch: string, agency: string) {
  agencyMaps.value[agencyTab.value][branch] = agency
  assigningBranch.value = null
}

// 지점 배정 해제
function unassignBranch(branch: string) {
  agencyMaps.value[agencyTab.value][branch] = ''
}

// 실행사 전체 삭제 (소속 지점 모두 미배정)
function removeAgency(agencyNameToRemove: string) {
  const map = agencyMaps.value[agencyTab.value]
  for (const branch of Object.keys(map)) {
    if (map[branch]?.trim() === agencyNameToRemove) {
      map[branch] = ''
    }
  }
}

// 미배정 지점 드롭다운 상태
const assigningBranch = ref<string | null>(null)

function toggleAssigning(branch: string) {
  assigningBranch.value = assigningBranch.value === branch ? null : branch
}

// 바깥 클릭 시 드롭다운 닫기
function handleClickOutside(e: MouseEvent) {
  if (assigningBranch.value && !(e.target as HTMLElement).closest('[data-agency-dropdown]')) {
    assigningBranch.value = null
  }
}
onMounted(() => document.addEventListener('click', handleClickOutside, true))
onUnmounted(() => document.removeEventListener('click', handleClickOutside, true))
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

    <!-- ═══ 실행사 매핑 ═══ -->
    <div class="space-y-1.5">
    <div class="text-xs font-bold text-slate-400 tracking-wide pl-1">실행사 매핑</div>
    <div class="border border-slate-200 rounded-lg overflow-hidden">

      <!-- 헤더: 제목 + 탭 -->
      <div class="px-4 py-3 bg-slate-50 border-b flex justify-between items-center">
        <div>
          <div class="text-sm font-semibold text-slate-700">실행사 매핑</div>
          <div class="text-xs text-slate-400">플레이스/웹페이지 지점별 실행사 배정</div>
        </div>
        <div class="flex gap-2">
          <button @click="agencyTab = 'place'"
            :class="agencyTab === 'place' ? 'bg-blue-600 text-white' : 'bg-white text-slate-600'"
            class="px-3 py-1 text-xs rounded border">플레이스</button>
          <button @click="agencyTab = 'webpage'"
            :class="agencyTab === 'webpage' ? 'bg-blue-600 text-white' : 'bg-white text-slate-600'"
            class="px-3 py-1 text-xs rounded border">웹페이지</button>
        </div>
      </div>

      <div class="p-4 space-y-4">

        <!-- 데이터 없음 안내 -->
        <div v-if="Object.keys(currentAgencyMap).length === 0"
          class="text-xs text-slate-400 py-4 text-center">
          등록된 매핑이 없습니다. 데이터를 먼저 로드해주세요.
        </div>

        <template v-else>

          <!-- 새 실행사 추가 -->
          <div class="flex items-center gap-2 pb-3 border-b border-slate-100">
            <span class="text-xs text-slate-500 whitespace-nowrap">새 실행사 추가</span>
            <input
              v-model="newAgencyName"
              @keydown.enter="addAgency"
              placeholder="실행사 이름"
              class="flex-1 px-2.5 py-1 border border-slate-300 rounded text-xs focus:border-blue-400 focus:outline-none"
            />
            <button @click="addAgency"
              class="px-3 py-1 bg-slate-600 text-white text-xs rounded hover:bg-slate-700 whitespace-nowrap">
              추가
            </button>
          </div>

          <!-- 실행사별 그룹 -->
          <div class="space-y-3">
            <div
              v-for="(branches, agencyName) in agencyGroups.groups"
              :key="agencyName"
              class="border-l-2 border-blue-300 pl-3"
            >
              <!-- 실행사 헤더 -->
              <div class="flex items-center justify-between mb-1.5">
                <span class="text-xs font-semibold text-slate-700">
                  {{ agencyName }}
                  <span class="ml-1 font-normal text-slate-400">({{ branches.length }}개 지점)</span>
                </span>
                <button @click="removeAgency(agencyName)"
                  title="실행사 삭제 (지점 미배정 처리)"
                  class="text-xs text-slate-400 hover:text-red-500 px-1.5 py-0.5 rounded hover:bg-red-50 transition-colors">
                  −
                </button>
              </div>
              <!-- 지점 칩 — 클릭 시 실행사 변경 드롭다운 -->
              <div class="flex flex-wrap gap-1">
                <div
                  v-for="branch in branches"
                  :key="branch"
                  class="relative"
                  data-agency-dropdown
                >
                  <button
                    @click="toggleAssigning(branch)"
                    class="inline-flex items-center gap-1 px-2 py-0.5 text-xs rounded-full bg-blue-50 text-blue-700 border border-blue-200 hover:bg-blue-100 transition-colors cursor-pointer"
                  >
                    {{ branch }}
                    <span class="text-blue-400 text-[10px]">▾</span>
                  </button>
                  <!-- 실행사 변경 드롭다운 -->
                  <div
                    v-if="assigningBranch === branch"
                    class="absolute top-full left-0 mt-1 z-20 bg-white border border-slate-200 rounded shadow-md py-1 min-w-max"
                  >
                    <button
                      v-for="name in agencyNames.filter(n => n !== agencyName)"
                      :key="name"
                      @click="assignBranch(branch, name)"
                      class="block w-full text-left px-3 py-1.5 text-xs text-slate-700 hover:bg-blue-50 hover:text-blue-700"
                    >
                      {{ name }}
                    </button>
                    <button
                      @click="unassignBranch(branch); assigningBranch = null"
                      class="block w-full text-left px-3 py-1.5 text-xs text-red-500 hover:bg-red-50 border-t border-slate-100"
                    >
                      배정 해제
                    </button>
                  </div>
                </div>
              </div>
            </div>

            <!-- 미배정 섹션 -->
            <div v-if="agencyGroups.unassigned.length > 0" class="border-l-2 border-amber-300 pl-3">
              <div class="text-xs font-semibold text-slate-500 mb-1.5">
                미배정
                <span class="ml-1 font-normal text-slate-400">({{ agencyGroups.unassigned.length }}개 지점)</span>
              </div>
              <div class="flex flex-wrap gap-1">
                <div
                  v-for="branch in agencyGroups.unassigned"
                  :key="branch"
                  class="relative"
                  data-agency-dropdown
                >
                  <button
                    @click="toggleAssigning(branch)"
                    class="inline-flex items-center px-2 py-0.5 text-xs rounded-full bg-amber-50 text-amber-700 border border-amber-200 hover:bg-amber-100 transition-colors"
                  >
                    {{ branch }} ▾
                  </button>
                  <!-- 실행사 선택 드롭다운 -->
                  <div
                    v-if="assigningBranch === branch"
                    class="absolute top-full left-0 mt-1 z-20 bg-white border border-slate-200 rounded shadow-md py-1 min-w-max"
                  >
                    <div v-if="agencyNames.length === 0"
                      class="px-3 py-1.5 text-xs text-slate-400">
                      실행사가 없습니다
                    </div>
                    <button
                      v-for="name in agencyNames"
                      :key="name"
                      @click="assignBranch(branch, name)"
                      class="block w-full text-left px-3 py-1.5 text-xs text-slate-700 hover:bg-blue-50 hover:text-blue-700"
                    >
                      {{ name }}
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>

        </template>

        <!-- 저장 버튼 -->
        <div class="flex items-center gap-2 pt-2 border-t border-slate-100">
          <button @click="saveAgencyMapHandler" :disabled="savingAgency"
            class="px-4 py-1.5 bg-blue-600 text-white text-xs rounded hover:bg-blue-700 disabled:opacity-50">
            {{ savingAgency ? '저장 중...' : '저장' }}
          </button>
          <span v-if="agencySaveMsg" class="text-xs"
            :class="agencySaveError ? 'text-red-500' : 'text-emerald-500'">
            {{ agencySaveMsg }}
          </span>
        </div>

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

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import api from '@/api/client'

interface SyncLogEntry {
  id: number
  sync_type: string
  added: number
  skipped: number
  conflicts: number
  detail: string | null
  synced_at: string
  triggered_by: string | null
  is_failed: number
}

interface IngestionError {
  branch?: string
  event?: string
  error: string
}

interface IngestionLog {
  id: number
  period_label: string
  status: string
  total_branches: number
  total_items: number
  error_log: IngestionError[]
  completed_at: string
}

// ── 상수 ──
const PAGE_SIZE = 8

const TYPE_LABEL: Record<string, string> = {
  event_sync: '이벤트',
  equipment_sync: '보유장비',
  cafe_sync: '카페',
  blog_notion_sync: '블로그',
  place_sheets_to_db: '플레이스',
  webpage_sheets_to_db: '웹페이지',
}

const TYPE_COLOR: Record<string, string> = {
  event_sync: 'bg-violet-100 text-violet-700',
  equipment_sync: 'bg-teal-100 text-teal-700',
  cafe_sync: 'bg-orange-100 text-orange-700',
  blog_notion_sync: 'bg-indigo-100 text-indigo-700',
  place_sheets_to_db: 'bg-blue-100 text-blue-700',
  webpage_sheets_to_db: 'bg-green-100 text-green-700',
}

// ── 상태 ──
const logs = ref<SyncLogEntry[]>([])
const loading = ref(true)
const error = ref('')
const expanded = ref<Set<number>>(new Set())
const currentPage = ref(1)

// 이벤트 ingestion-log 상세
const evtDetailOpen = ref<Set<number>>(new Set())
const evtDetailLoading = ref<Set<number>>(new Set())
const evtDetailData = ref<Map<number, IngestionLog>>(new Map())
const evtDetailError = ref<Map<number, string>>(new Map())

// 실패 항목 필터 검색어 (entryId → 검색어)
const evtErrorFilter = ref<Map<number, string>>(new Map())

// 실패 항목 필터링 (검색어 적용, 최대 30건)
const EVT_ERROR_LIMIT = 30

function getFilteredErrors(entryId: number, errorLog: IngestionError[]): { items: IngestionError[]; total: number; overflow: number } {
  const q = (evtErrorFilter.value.get(entryId) ?? '').trim().toLowerCase()
  const filtered = q
    ? errorLog.filter(item => item.error.toLowerCase().includes(q) || (item.branch ?? '').toLowerCase().includes(q))
    : errorLog
  const total = filtered.length
  const items = filtered.slice(0, EVT_ERROR_LIMIT)
  return { items, total, overflow: Math.max(0, total - EVT_ERROR_LIMIT) }
}

function setErrorFilter(entryId: number, val: string) {
  const m = new Map(evtErrorFilter.value)
  m.set(entryId, val)
  evtErrorFilter.value = m
}

function downloadErrors(entryId: number) {
  const data = evtDetailData.value.get(entryId)
  if (!data) return
  const lines: string[] = []
  lines.push(`# 이벤트 동기화 실패 항목`)
  lines.push(`# 기간: ${data.period_label}`)
  lines.push(`# 지점 수: ${data.total_branches}, 총 항목: ${data.total_items}`)
  lines.push(`# 실패 건수: ${data.error_log.length}`)
  lines.push(`# 완료 시각: ${data.completed_at}`)
  lines.push('')
  lines.push('지점\t항목\t사유')
  for (const item of data.error_log) {
    lines.push(`${item.branch ?? ''}\t${item.event ?? ''}\t${item.error}`)
  }
  // BOM 포함 — 엑셀에서 한글 깨짐 방지
  const blob = new Blob(['﻿' + lines.join('\n')], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  const ts = (data.completed_at || new Date().toISOString()).slice(0, 10)
  a.href = url
  a.download = `event-sync-errors-${ts}.txt`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

// 스크롤 컨테이너 ref
const scrollContainer = ref<HTMLElement | null>(null)

// ── 페이지네이션 ──
const totalPages = computed(() =>
  Math.max(1, Math.ceil(logs.value.length / PAGE_SIZE))
)

const pagedLogs = computed(() => {
  const start = (currentPage.value - 1) * PAGE_SIZE
  return logs.value.slice(start, start + PAGE_SIZE)
})

function goPage(n: number) {
  if (n < 1 || n > totalPages.value) return
  currentPage.value = n
  // 스크롤 맨 위로
  if (scrollContainer.value) {
    scrollContainer.value.scrollTop = 0
  }
}

// ── 실패 파싱 ──
const FAIL_RE = /실패\s*(\d+)\s*건/

function parseFailCount(detail: string | null): number {
  if (!detail) return 0
  const m = detail.match(FAIL_RE)
  return m ? parseInt(m[1], 10) : 0
}

function cardClass(entry: SyncLogEntry): string {
  if (entry.is_failed === 1) {
    return 'bg-red-50 border-red-200 hover:border-red-300'
  }
  const fc = parseFailCount(entry.detail)
  if (fc > 0) {
    return 'bg-amber-50 border-amber-200 hover:border-amber-300'
  }
  return 'bg-white border-slate-200 hover:border-slate-300'
}

function dividerClass(entry: SyncLogEntry): string {
  if (entry.is_failed === 1) return 'border-red-200'
  if (parseFailCount(entry.detail) > 0) return 'border-amber-200'
  return 'border-slate-100'
}

// ── 표시 헬퍼 ──
function typeLabel(syncType: string): string {
  return TYPE_LABEL[syncType] ?? syncType
}

function typeBadgeClass(syncType: string): string {
  return TYPE_COLOR[syncType] ?? 'bg-slate-100 text-slate-600'
}

function formatDate(iso: string): string {
  if (!iso) return '-'
  const d = new Date(iso)
  const mm = String(d.getMonth() + 1).padStart(2, '0')
  const dd = String(d.getDate()).padStart(2, '0')
  const hh = String(d.getHours()).padStart(2, '0')
  const min = String(d.getMinutes()).padStart(2, '0')
  return `${mm}/${dd} ${hh}:${min}`
}

// sync_type별로 conflicts 컬럼의 의미가 다름
// - equipment_sync: 시트 기준 업데이트 건수
// - event_sync / cafe_sync: 실패 건수 (이미 별도 amber 뱃지로 표시되므로 결과 줄에선 생략)
// - 그 외: 의미 없음 (0)
function conflictsLabel(syncType: string): string | null {
  if (syncType === 'equipment_sync') return '업데이트'
  return null
}

function resultText(entry: SyncLogEntry): string {
  if (entry.is_failed) {
    const failParts = ['실패']
    if (entry.added > 0) failParts.push(`완료 ${entry.added}건`)
    return failParts.join(' · ')
  }
  const parts = [`완료 ${entry.added.toLocaleString()}건`]
  if (entry.skipped > 0) parts.push(`스킵 ${entry.skipped}건`)
  if (entry.conflicts > 0) {
    const label = conflictsLabel(entry.sync_type)
    if (label) parts.push(`${label} ${entry.conflicts}건`)
  }
  return parts.join(' · ')
}

function triggerTooltip(triggered_by: string | null): string {
  return triggered_by === 'auto' ? '자동 실행' : '수동 실행'
}

function canExpand(entry: SyncLogEntry): boolean {
  return !!entry.detail
}

function toggleExpand(id: number) {
  if (expanded.value.has(id)) {
    expanded.value.delete(id)
  } else {
    expanded.value.add(id)
  }
}

// ── 이벤트 ingestion-log 상세 ──
function isEvtDetailOpen(id: number): boolean {
  return evtDetailOpen.value.has(id)
}

async function toggleEvtDetail(entryId: number, e: Event) {
  e.stopPropagation()
  if (evtDetailOpen.value.has(entryId)) {
    evtDetailOpen.value.delete(entryId)
    return
  }
  evtDetailOpen.value.add(entryId)
  // 이미 데이터 있으면 재사용
  if (evtDetailData.value.has(entryId)) return

  evtDetailLoading.value.add(entryId)
  evtDetailError.value.delete(entryId)
  try {
    const res = await api.get('/events/ingestion-logs/latest')
    evtDetailData.value.set(entryId, res.data)
  } catch (err: any) {
    evtDetailError.value.set(entryId, err.response?.data?.detail || '조회 실패')
  } finally {
    evtDetailLoading.value.delete(entryId)
  }
}

const ERROR_CATEGORIES: Array<{ label: string; match: (e: string) => boolean }> = [
  { label: '가격 정보 없음', match: (e) => e.includes('가격 정보 없음') },
  { label: 'DB에 지점 없음', match: (e) => e.includes('DB에 지점 없음') },
  { label: '이벤트가 > 정상가', match: (e) => e.includes('이벤트가') && e.includes('정상가') },
  { label: '가격 이상', match: (e) => e.includes('이상') },
]

function categorize(errorLog: IngestionError[]): Array<{ label: string; count: number }> {
  const counts: Record<string, number> = {}
  for (const item of errorLog) {
    let matched = '기타'
    for (const cat of ERROR_CATEGORIES) {
      if (cat.match(item.error)) {
        matched = cat.label
        break
      }
    }
    counts[matched] = (counts[matched] ?? 0) + 1
  }
  return Object.entries(counts)
    .map(([label, count]) => ({ label, count }))
    .sort((a, b) => b.count - a.count)
}

// ── 데이터 로드 ──
async function fetchLogs() {
  try {
    const res = await api.get('/admin/sync-log?limit=50')
    const newData: SyncLogEntry[] = res.data

    // 1페이지에 있을 때만 자동 갱신 (다른 페이지는 갱신 없음)
    const wasOnFirstPage = currentPage.value === 1
    logs.value = newData

    // 완전 실패만 기본 펼침 (부분 실패는 amber 뱃지로 강조됨, 자동 펼치면 다른 카드 가림)
    // 사용자가 이미 펼친 항목은 유지
    const newExpanded = new Set<number>(expanded.value)
    for (const entry of newData) {
      if (entry.is_failed) {
        newExpanded.add(entry.id)
      }
    }
    expanded.value = newExpanded

    // 총 페이지가 줄어서 현재 페이지가 범위 밖이면 조정
    if (currentPage.value > totalPages.value) {
      currentPage.value = totalPages.value
    }

    error.value = ''
  } catch (e: any) {
    error.value = e.response?.data?.detail || '로그 조회 실패'
  } finally {
    loading.value = false
  }
}

async function refresh() {
  loading.value = true
  await fetchLogs()
}
defineExpose({ refresh })

// ── 폴링 (30초) ──
let pollTimer: ReturnType<typeof setInterval> | null = null

function startPolling() {
  pollTimer = setInterval(() => {
    if (document.visibilityState === 'visible') {
      fetchLogs()
    }
  }, 30_000)
}

onMounted(() => {
  fetchLogs()
  startPolling()
})

onUnmounted(() => {
  if (pollTimer !== null) clearInterval(pollTimer)
})
</script>

<template>
  <div class="bg-white border border-slate-200 rounded-lg flex flex-col max-h-[calc(100vh-8rem)]">
    <!-- 헤더 -->
    <div class="flex items-center justify-between px-3 py-2 border-b border-slate-100 flex-shrink-0">
      <span class="text-sm font-semibold text-slate-700">동기화 로그</span>
      <div class="flex items-center gap-2">
        <!-- 페이지 컨트롤 -->
        <div v-if="logs.length > 0" class="flex items-center gap-1">
          <button
            @click="goPage(currentPage - 1)"
            :disabled="currentPage === 1"
            class="px-1.5 py-0.5 text-xs rounded hover:bg-slate-100 text-slate-500 disabled:opacity-30 disabled:cursor-default"
          >&lt;</button>
          <span class="text-xs tabular-nums text-slate-500 min-w-[3rem] text-center">
            {{ currentPage }} / {{ totalPages }}
          </span>
          <button
            @click="goPage(currentPage + 1)"
            :disabled="currentPage === totalPages"
            class="px-1.5 py-0.5 text-xs rounded hover:bg-slate-100 text-slate-500 disabled:opacity-30 disabled:cursor-default"
          >&gt;</button>
        </div>
        <!-- 새로고침 -->
        <button
          @click="refresh"
          :disabled="loading"
          class="p-1 rounded hover:bg-slate-100 text-slate-400 hover:text-slate-600 disabled:opacity-40 transition-colors"
          title="새로고침"
        >
          <svg class="w-3.5 h-3.5" :class="{ 'animate-spin': loading }" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
        </button>
      </div>
    </div>

    <!-- 스크롤 영역 -->
    <div ref="scrollContainer" class="overflow-y-auto flex-1">
      <!-- Loading -->
      <div v-if="loading && logs.length === 0" class="px-3 py-5 text-center text-xs text-slate-400">
        불러오는 중...
      </div>

      <!-- Error -->
      <div v-else-if="error" class="px-3 py-3 text-xs text-red-600 bg-red-50">
        {{ error }}
      </div>

      <!-- Empty -->
      <div v-else-if="logs.length === 0" class="px-3 py-5 text-center text-xs text-slate-400">
        로그 없음
      </div>

      <!-- 카드 리스트 -->
      <div v-else class="flex flex-col gap-1.5 p-1.5">
        <div
          v-for="entry in pagedLogs"
          :key="entry.id"
          class="rounded border select-none"
          :class="[cardClass(entry), canExpand(entry) ? 'cursor-pointer' : '']"
          :title="triggerTooltip(entry.triggered_by)"
          @click="canExpand(entry) ? toggleExpand(entry.id) : undefined"
        >
          <!-- 카드 헤더 줄 -->
          <div class="flex items-center justify-between px-2.5 py-2 gap-2">
            <span class="text-[11px] tabular-nums text-slate-400 flex-shrink-0">
              {{ formatDate(entry.synced_at) }}
            </span>
            <span
              class="text-[11px] px-1.5 py-0.5 rounded font-medium flex-shrink-0"
              :class="typeBadgeClass(entry.sync_type)"
            >{{ typeLabel(entry.sync_type) }}</span>
          </div>

          <!-- 결과 줄 + 실패 뱃지 -->
          <div class="px-2.5 pb-2 flex items-center gap-1.5 flex-wrap">
            <span
              class="text-[11px] leading-none"
              :class="entry.is_failed ? 'text-red-600' : 'text-slate-600'"
            >{{ resultText(entry) }}</span>
            <span
              v-if="parseFailCount(entry.detail) > 0"
              class="bg-amber-100 text-amber-700 px-1.5 py-0.5 text-[10px] rounded leading-none flex-shrink-0"
            >⚠ 실패 {{ parseFailCount(entry.detail) }}건</span>
          </div>

          <!-- 상세 펼침 영역 -->
          <div
            v-if="entry.detail && expanded.has(entry.id)"
            class="border-t"
            :class="dividerClass(entry)"
            @click.stop
          >
            <!-- detail 텍스트 -->
            <div class="px-2.5 py-2 text-[11px] text-slate-500 whitespace-pre-wrap break-all">
              {{ entry.detail }}
            </div>

            <!-- 이벤트 카드 전용: 상세 보기 버튼 -->
            <div v-if="entry.sync_type === 'event_sync'" class="px-2.5 pb-2">
              <button
                @click="toggleEvtDetail(entry.id, $event)"
                class="text-[11px] text-violet-600 hover:text-violet-800 underline underline-offset-2"
              >
                {{ isEvtDetailOpen(entry.id) ? '상세 닫기 ▴' : '상세 보기 ▾' }}
              </button>

              <!-- 상세 내용 -->
              <div v-if="isEvtDetailOpen(entry.id)" class="mt-1.5 border-t border-violet-100 pt-1.5">
                <!-- 로딩 -->
                <div v-if="evtDetailLoading.has(entry.id)" class="text-[11px] text-slate-400">
                  불러오는 중...
                </div>
                <!-- 에러 -->
                <div v-else-if="evtDetailError.has(entry.id)" class="text-[11px] text-red-500">
                  {{ evtDetailError.get(entry.id) }}
                </div>
                <!-- 데이터 -->
                <div v-else-if="evtDetailData.has(entry.id)" class="flex flex-col gap-1.5">
                  <div class="text-[11px] text-slate-500">
                    {{ evtDetailData.get(entry.id)!.period_label }} /
                    {{ evtDetailData.get(entry.id)!.total_branches }}개 지점 /
                    총 {{ evtDetailData.get(entry.id)!.total_items }}건
                  </div>
                  <!-- 에러 분류 통계 -->
                  <div v-if="evtDetailData.get(entry.id)!.error_log.length > 0">
                    <div class="text-[10px] font-medium text-slate-500 mb-0.5">에러 분류</div>
                    <div
                      v-for="cat in categorize(evtDetailData.get(entry.id)!.error_log)"
                      :key="cat.label"
                      class="text-[11px] text-slate-600 pl-2"
                    >
                      - {{ cat.label }}: {{ cat.count }}건
                    </div>
                  </div>
                  <!-- 실패 항목 (검색 + 최대 30건) -->
                  <div v-if="evtDetailData.get(entry.id)!.error_log.length > 0">
                    <div class="flex items-center justify-between mt-1 mb-0.5">
                      <div class="text-[10px] font-medium text-slate-500">
                        실패 항목 (전체 {{ evtDetailData.get(entry.id)!.error_log.length }}건)
                      </div>
                      <button
                        @click="downloadErrors(entry.id)"
                        class="text-[10px] px-1.5 py-0.5 bg-violet-50 hover:bg-violet-100 text-violet-700 rounded border border-violet-200"
                        title="전체 실패 항목을 TXT로 다운로드 (탭 구분, 엑셀 호환)"
                      >전체 다운로드</button>
                    </div>
                    <!-- 검색 박스 -->
                    <input
                      type="text"
                      :value="evtErrorFilter.get(entry.id) ?? ''"
                      @input="setErrorFilter(entry.id, ($event.target as HTMLInputElement).value)"
                      placeholder="실패 항목 필터..."
                      class="w-full text-[10px] px-1.5 py-0.5 border border-slate-200 rounded bg-white text-slate-600 placeholder-slate-300 mb-1 focus:outline-none focus:border-slate-400"
                    />
                    <!-- 필터링된 항목 — v-for로 단일 객체 alias 만들기 (Vue는 v-if as 미지원) -->
                    <template v-for="filtered in [getFilteredErrors(entry.id, evtDetailData.get(entry.id)!.error_log)]" :key="'errlist'">
                      <div
                        v-for="(item, idx) in filtered.items"
                        :key="idx"
                        class="text-[11px] text-slate-600 pl-2 truncate"
                      >
                        - {{ item.branch ?? '?' }}: {{ item.error }}
                      </div>
                      <div v-if="filtered.overflow > 0" class="text-[10px] text-slate-400 pl-2 mt-0.5">
                        외 {{ filtered.overflow }}건 더 있음
                      </div>
                      <div v-if="filtered.total === 0" class="text-[10px] text-slate-400 pl-2">
                        일치하는 항목 없음
                      </div>
                    </template>
                  </div>
                  <div v-else class="text-[11px] text-slate-400">에러 없음</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

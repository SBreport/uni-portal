<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { listWeeklyReports, createWeeklyReport, type WeeklyReportSummary } from '@/api/reports'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import ReportDetailView from '@/components/reports/ReportDetailView.vue'
import ReportsDashboard from '@/components/reports/ReportsDashboard.vue'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

// ── 권한 ──
const canEdit = computed(() => ['admin', 'editor'].includes(auth.role))

// ── 뷰 분기 ──
const isDetailView = computed(() => !!route.query.week)

// ── 보고서 목록 ──
const loading = ref(false)
const error = ref('')
const reports = ref<WeeklyReportSummary[]>([])
const existingWeekSet = computed(() => new Set(reports.value.map(r => r.week_start)))

async function loadReports() {
  loading.value = true
  error.value = ''
  try {
    const res = await listWeeklyReports()
    reports.value = res.data
  } catch (e: any) {
    error.value = e.response?.data?.detail || '보고서 목록을 불러오지 못했습니다.'
  } finally {
    loading.value = false
  }
}

// ── 날짜 유틸 ──
function getMondayOf(d: Date): Date {
  const day = d.getDay() // 0=일, 1=월, ... 6=토
  const diff = day === 0 ? -6 : 1 - day
  const m = new Date(d)
  m.setDate(d.getDate() + diff)
  m.setHours(0, 0, 0, 0)
  return m
}

function formatDate(d: Date): string {
  const y = d.getFullYear()
  const mo = String(d.getMonth() + 1).padStart(2, '0')
  const da = String(d.getDate()).padStart(2, '0')
  return `${y}-${mo}-${da}`
}

function formatMonday(d: Date): string {
  const mo = String(d.getMonth() + 1).padStart(2, '0')
  const da = String(d.getDate()).padStart(2, '0')
  return `${mo}/${da}`
}

function defaultReportTitle(weekStart: string): string {
  // "YY년 M월 W주 상위노출 결과 보고서" — week_start 기준 자동 계산, 사용자 수정 가능
  const [y, m, dd] = weekStart.split('-').map(Number)
  const d = new Date(y, m - 1, dd)
  const yy = String(d.getFullYear()).slice(-2)
  const month = d.getMonth() + 1
  // 해당 월의 첫 월요일 기준 몇 번째 주
  const firstDay = new Date(d.getFullYear(), d.getMonth(), 1)
  const wd = firstDay.getDay()  // 0=일, 1=월, ... 6=토
  const daysToFirstMon = wd === 0 ? 1 : wd === 1 ? 0 : 8 - wd
  const firstMonday = new Date(firstDay)
  firstMonday.setDate(firstDay.getDate() + daysToFirstMon)
  const diffDays = Math.floor((d.getTime() - firstMonday.getTime()) / 86400000)
  const week = Math.max(1, Math.floor(diffDays / 7) + 1)
  return `${yy}년 ${month}월 ${week}주 상위노출 결과 보고서`
}

// ── 월 네비 ──
const today = new Date()
today.setHours(0, 0, 0, 0)
const viewYear = ref(today.getFullYear())
const viewMonth = ref(today.getMonth()) // 0-indexed

const viewMonthLabel = computed(() => `${viewYear.value}년 ${viewMonth.value + 1}월`)

function prevMonth() {
  if (viewMonth.value === 0) {
    viewYear.value--
    viewMonth.value = 11
  } else {
    viewMonth.value--
  }
}

function nextMonth() {
  if (viewMonth.value === 11) {
    viewYear.value++
    viewMonth.value = 0
  } else {
    viewMonth.value++
  }
}

// ── 캘린더 그리드 계산 ──
// 해당 월의 첫날이 포함된 주의 월요일 ~ 마지막날이 포함된 주의 일요일
interface CalendarWeek {
  monday: Date
  days: Date[]
  weekLabel: string // "MM/DD"
}

const calendarWeeks = computed<CalendarWeek[]>(() => {
  const firstDay = new Date(viewYear.value, viewMonth.value, 1)
  const lastDay = new Date(viewYear.value, viewMonth.value + 1, 0)

  const startMonday = getMondayOf(firstDay)
  // 마지막날의 일요일 = 마지막날 + (7 - 요일) % 7 일 (단, 일요일=0이면 +0)
  const lastDayOfWeek = lastDay.getDay()
  const endSunday = new Date(lastDay)
  const daysToAdd = lastDayOfWeek === 0 ? 0 : 7 - lastDayOfWeek
  endSunday.setDate(lastDay.getDate() + daysToAdd)

  const weeks: CalendarWeek[] = []
  const cursor = new Date(startMonday)

  while (cursor <= endSunday) {
    const monday = new Date(cursor)
    const days: Date[] = []
    for (let i = 0; i < 7; i++) {
      days.push(new Date(cursor))
      cursor.setDate(cursor.getDate() + 1)
    }
    weeks.push({
      monday,
      days,
      weekLabel: formatMonday(monday),
    })
  }

  return weeks
})

function isToday(d: Date): boolean {
  return d.toDateString() === today.toDateString()
}

function isCurrentMonth(d: Date): boolean {
  return d.getMonth() === viewMonth.value && d.getFullYear() === viewYear.value
}

// ── 주차 클릭 ──
const hoveredWeek = ref<string | null>(null)

function onWeekClick(monday: Date) {
  const weekStart = formatDate(monday)
  const exists = existingWeekSet.value.has(weekStart)

  if (exists) {
    router.push({ path: '/reports', query: { week: weekStart } })
    return
  }

  if (!canEdit.value) {
    return
  }

  if (!confirm(`${weekStart} 주차 보고서를 새로 작성하시겠습니까?`)) return
  createAndNavigate(weekStart)
}

async function createAndNavigate(weekStart: string) {
  try {
    await createWeeklyReport({
      week_start: weekStart,
      title: defaultReportTitle(weekStart),
      data: {
        basic: { notice: '상위노출 보장 상품의 경우, 보장 기간은 25일입니다.' },
      },
    })
    await loadReports()
    router.push({ path: '/reports', query: { week: weekStart } })
  } catch (e: any) {
    if (e.response?.status === 409) {
      // 이미 존재 → 그냥 이동
      router.push({ path: '/reports', query: { week: weekStart } })
    } else {
      alert(e.response?.data?.detail || '보고서 생성 실패')
    }
  }
}

// ── 뷰 모드 (캘린더 / 목록) ──
const viewMode = ref<'calendar' | 'list'>('calendar')

// ── 오늘 버튼 ──
function goToday() {
  viewYear.value = today.getFullYear()
  viewMonth.value = today.getMonth()
}

const isThisMonth = computed(() =>
  viewYear.value === today.getFullYear() && viewMonth.value === today.getMonth()
)

// ── 목록 뷰 헬퍼 ──
function formatUpdatedAt(s: string): string {
  if (!s) return ''
  return s.slice(0, 10).replace(/-/g, '.')
}

// ── 오늘 주차 작성 버튼 ──
function goToThisWeek() {
  const weekStart = formatDate(getMondayOf(today))
  const exists = existingWeekSet.value.has(weekStart)
  if (exists) {
    router.push({ path: '/reports', query: { week: weekStart } })
  } else {
    createAndNavigate(weekStart)
  }
}

// ── 목록 뷰 진입 시 로드 ──
onMounted(() => {
  if (!isDetailView.value) {
    loadReports()
  }
})

// query 변경 감지 (뒤로가기 등)
watch(isDetailView, (val) => {
  if (!val) {
    loadReports()
  }
})
</script>

<template>
  <!-- ═══════════════════════════════════════ 상세 뷰 -->
  <ReportDetailView
    v-if="isDetailView"
    :week-start="route.query.week as string"
  />

  <!-- ═══════════════════════════════════════ 목록 뷰 (캘린더 피커) -->
  <div v-else class="flex flex-col overflow-hidden" style="height: calc(100vh - 48px)">

    <!-- ROW 1: 상단바 -->
    <div class="flex flex-wrap items-center gap-x-4 gap-y-1 px-5 pt-3 pb-2 shrink-0">
      <h1 class="text-lg font-bold text-slate-800 shrink-0">주간 보고서</h1>

      <!-- 월 네비 -->
      <div class="flex items-center gap-1">
        <button
          @click="prevMonth"
          class="w-7 h-7 flex items-center justify-center rounded-md border border-slate-200 text-slate-400 hover:bg-slate-50 transition text-xs"
        >&lt;</button>
        <span class="px-2 text-sm font-medium text-slate-700 min-w-[120px] text-center tabular-nums">
          {{ viewMonthLabel }}
        </span>
        <button
          @click="nextMonth"
          class="w-7 h-7 flex items-center justify-center rounded-md border border-slate-200 text-slate-400 hover:bg-slate-50 transition text-xs"
        >&gt;</button>
        <button
          @click="goToday"
          :disabled="isThisMonth"
          class="ml-1 text-xs px-3 py-1 rounded border border-slate-300 text-slate-600 hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed shrink-0"
        >오늘</button>
      </div>

      <!-- 캘린더/목록 스위처 + 이번 주 작성 버튼 -->
      <div class="flex items-center gap-2">
        <div class="flex items-center border border-slate-200 rounded overflow-hidden shrink-0">
          <button
            @click="viewMode = 'calendar'"
            class="px-2.5 py-1 text-xs transition-colors"
            :class="viewMode === 'calendar' ? 'bg-slate-800 text-white' : 'text-slate-500 hover:bg-slate-50'"
          >캘린더</button>
          <button
            @click="viewMode = 'list'"
            class="px-2.5 py-1 text-xs transition-colors"
            :class="viewMode === 'list' ? 'bg-slate-800 text-white' : 'text-slate-500 hover:bg-slate-50'"
          >목록</button>
        </div>
        <button
          v-if="canEdit"
          @click="goToThisWeek"
          class="text-xs px-3 py-1 rounded bg-blue-600 text-white hover:bg-blue-700 shrink-0 font-medium"
        >이번 주 작성</button>
      </div>
    </div>

    <!-- 에러 바 -->
    <div v-if="error" class="mx-5 mb-2 p-2 bg-red-50 border border-red-200 rounded-lg text-xs text-red-600 shrink-0">
      {{ error }}
    </div>

    <!-- 본문 -->
    <div class="flex-1 overflow-y-auto px-5 pb-3">

      <!-- 로딩 -->
      <div v-if="loading" class="flex items-center justify-center py-12">
        <LoadingSpinner message="불러오는 중..." />
      </div>

      <div v-else class="max-w-4xl mx-auto space-y-4">
        <!-- 캘린더 -->
        <div v-if="viewMode === 'calendar'">
          <div class="bg-white border border-slate-200 rounded-lg overflow-hidden">

            <!-- 요일 헤더 -->
            <div class="grid grid-cols-8 border-b border-slate-200 bg-slate-50">
              <div class="px-2 py-1.5 text-[10px] text-slate-400 text-center"></div>
              <div
                v-for="day in ['월','화','수','목','금','토','일']"
                :key="day"
                class="px-2 py-1.5 text-[10px] font-medium text-slate-500 text-center"
              >{{ day }}</div>
            </div>

            <!-- 주 행 -->
            <div
              v-for="week in calendarWeeks"
              :key="week.weekLabel"
              class="grid grid-cols-8 border-b border-slate-100 last:border-b-0 cursor-pointer transition-colors"
              :class="hoveredWeek === week.weekLabel ? 'bg-blue-50/60' : 'bg-white'"
              @mouseenter="hoveredWeek = week.weekLabel"
              @mouseleave="hoveredWeek = null"
              @click="onWeekClick(week.monday)"
            >
              <!-- 주차 라벨 (MM/DD) — 작성됨이면 볼드+파랑으로 강조 -->
              <div class="flex items-center justify-center px-2 py-2">
                <span
                  class="text-[10px] tabular-nums"
                  :class="existingWeekSet.has(formatDate(week.monday))
                    ? 'text-blue-600 font-semibold'
                    : 'text-slate-400'"
                >{{ week.weekLabel }}</span>
              </div>

              <!-- 7개 날짜 셀 -->
              <div
                v-for="(day, idx) in week.days"
                :key="idx"
                class="relative flex items-center justify-center px-2 py-2"
              >
                <!-- 날짜 숫자 -->
                <span
                  class="text-xs tabular-nums"
                  :class="[
                    isToday(day)
                      ? 'w-5 h-5 rounded-full bg-blue-600 text-white flex items-center justify-center font-medium'
                      : isCurrentMonth(day)
                        ? 'text-slate-700'
                        : 'text-slate-300'
                  ]"
                >{{ day.getDate() }}</span>
              </div>
            </div>

          </div>

          <!-- 범례 -->
          <div class="flex items-center gap-3 mt-2 px-1">
            <span class="text-[10px] text-blue-600 font-semibold tabular-nums">03/30</span>
            <span class="text-[10px] text-slate-400">작성됨</span>
            <span class="text-slate-200 mx-1">·</span>
            <span class="text-[10px] text-slate-400 tabular-nums">04/20</span>
            <span class="text-[10px] text-slate-400">미작성</span>
            <span class="text-[10px] text-slate-400 ml-auto">행 클릭으로 주차 선택</span>
          </div>
        </div>

        <!-- 목록 뷰 -->
        <div v-else>
          <div v-if="reports.length === 0" class="text-center py-12 text-xs text-slate-400">
            작성된 보고서가 없습니다.
          </div>
          <div v-else class="bg-white border border-slate-200 rounded-lg overflow-hidden">
            <div
              v-for="r in reports"
              :key="r.week_start"
              @click="router.push({ path: '/reports', query: { week: r.week_start } })"
              class="grid grid-cols-[auto_1fr_auto] gap-3 items-center px-4 py-2.5 border-b border-slate-100 last:border-b-0 cursor-pointer hover:bg-blue-50/60 transition-colors"
            >
              <span class="text-[11px] text-slate-500 tabular-nums shrink-0">
                {{ r.week_start.replace(/-/g, '.').slice(2) }} – {{ r.week_end.replace(/-/g, '.').slice(5) }}
              </span>
              <span class="text-xs text-slate-700 truncate">{{ r.title || '(제목 없음)' }}</span>
              <span class="text-[10px] text-slate-400 tabular-nums shrink-0">
                {{ formatUpdatedAt(r.updated_at) }}
              </span>
            </div>
          </div>
        </div>

        <!-- 대시보드 (항상 표시) -->
        <ReportsDashboard />
      </div>

    </div>
  </div>
</template>

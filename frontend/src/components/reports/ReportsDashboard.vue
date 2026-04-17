<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js'
import { Line, Doughnut } from 'vue-chartjs'
import { getDashboard, type DashboardData, type WeeklyKpiCurrent, type WeeklyTrendPoint } from '@/api/reports'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, ArcElement, Title, Tooltip, Legend)

// ── 데이터 로드 ───────────────────────────────────────────────────────────────

const loading = ref(true)
const error = ref('')
const dashboardData = ref<DashboardData | null>(null)

async function load() {
  loading.value = true
  error.value = ''
  try {
    const res = await getDashboard(8)
    dashboardData.value = res.data
  } catch (e: any) {
    error.value = e.response?.data?.detail || '대시보드를 불러오지 못했습니다.'
  } finally {
    loading.value = false
  }
}

onMounted(load)

// ── 편의 computed ─────────────────────────────────────────────────────────────

const kpis = computed(() => dashboardData.value?.weekly_kpis ?? null)
const trend = computed(() => dashboardData.value?.weekly_trend ?? [])
const realtime = computed(() => dashboardData.value?.realtime ?? null)

// ── KPI 카드 정의 ─────────────────────────────────────────────────────────────

interface KpiCard {
  key: string
  label: string
  value: string
  reference: string
  delta: string
  deltaClass: string
  trend: (number | null)[]
  trendColor: string
}

function computeDelta(curStr: string, prevStr: string): { label: string; cls: string } {
  const cur = parseInt(curStr || '', 10)
  const prev = parseInt(prevStr || '', 10)
  if (isNaN(prev)) return { label: '전주 데이터 없음', cls: 'text-slate-300' }
  if (isNaN(cur)) return { label: '전주 데이터 없음', cls: 'text-slate-300' }
  const diff = cur - prev
  if (diff > 0) return { label: `▲ +${diff} (전주 ${prev})`, cls: 'text-blue-500' }
  if (diff < 0) return { label: `▼ ${diff} (전주 ${prev})`, cls: 'text-red-500' }
  return { label: `– 0 (전주 ${prev})`, cls: 'text-slate-400' }
}

function deltaToColor(cls: string): string {
  if (cls.includes('blue')) return '#3b82f6'
  if (cls.includes('red')) return '#ef4444'
  return '#94a3b8'
}

function extractTrend(
  points: WeeklyTrendPoint[],
  field: keyof Omit<WeeklyTrendPoint, 'week_start'>,
): (number | null)[] {
  return points.map((p) => p[field] as number | null)
}

const kpiCards = computed<KpiCard[]>(() => {
  const cur = kpis.value?.current ?? null
  const prev = kpis.value?.previous ?? null
  const trendPoints = trend.value

  const defs: Array<{
    key: string
    label: string
    primaryVal: string
    referenceText: string
    curPrimary: string
    prevPrimary: string
    trendField: keyof Omit<WeeklyTrendPoint, 'week_start'>
  }> = [
    {
      key: 'blog',
      label: '블로그 상위노출',
      primaryVal: cur?.blogDistribution.ranked ?? '',
      referenceText: cur?.blogDistribution.keywords ? `타겟 ${cur.blogDistribution.keywords}` : '',
      curPrimary: cur?.blogDistribution.ranked ?? '',
      prevPrimary: prev?.blogDistribution.ranked ?? '',
      trendField: 'blog_ranked',
    },
    {
      key: 'place',
      label: '플레이스 점유',
      primaryVal: cur?.place.occupied ?? '',
      referenceText: cur?.place.total ? `총 ${cur.place.total}` : '',
      curPrimary: cur?.place.occupied ?? '',
      prevPrimary: prev?.place.occupied ?? '',
      trendField: 'place_occupied',
    },
    {
      key: 'website',
      label: '웹사이트 노출',
      primaryVal: cur?.website.visible ?? '',
      referenceText: cur?.website.total ? `총 ${cur.website.total}` : '',
      curPrimary: cur?.website.visible ?? '',
      prevPrimary: prev?.website.visible ?? '',
      trendField: 'website_visible',
    },
    {
      key: 'exposure',
      label: '블로그 노출',
      primaryVal: cur?.blogExposure.visible ?? '',
      referenceText: cur?.blogExposure.total ? `총 ${cur.blogExposure.total}` : '',
      curPrimary: cur?.blogExposure.visible ?? '',
      prevPrimary: prev?.blogExposure.visible ?? '',
      trendField: 'blog_exposure_visible',
    },
    {
      key: 'related',
      label: '함께찾는 생성',
      primaryVal: cur?.related.created ?? '',
      referenceText: cur?.related.total ? `총 ${cur.related.total}` : '',
      curPrimary: cur?.related.created ?? '',
      prevPrimary: prev?.related.created ?? '',
      trendField: 'related_created',
    },
  ]

  return defs.map((d) => {
    const delta = computeDelta(d.curPrimary, d.prevPrimary)
    const trendColor = deltaToColor(delta.cls)
    const trendData = extractTrend(trendPoints, d.trendField)
    return {
      key: d.key,
      label: d.label,
      value: d.primaryVal && d.primaryVal !== '' ? d.primaryVal : '—',
      reference: d.referenceText,
      delta: delta.label,
      deltaClass: delta.cls,
      trend: trendData,
      trendColor,
    }
  })
})

// ── 스파크라인 옵션 ────────────────────────────────────────────────────────────

const sparkOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { display: false },
    tooltip: { enabled: false },
  },
  scales: {
    x: { display: false },
    y: { display: false, beginAtZero: false },
  },
  elements: {
    point: { radius: 0 },
    line: { borderWidth: 1.5, tension: 0.2 },
  },
} as const

function makeSparkData(trendData: (number | null)[], color: string) {
  return {
    labels: trendData.map((_, i) => String(i)),
    datasets: [
      {
        data: trendData,
        borderColor: color,
        backgroundColor: color,
        fill: false,
        spanGaps: true,
      },
    ],
  }
}

// ── 도넛 차트 ─────────────────────────────────────────────────────────────────

const placeDoughnut = computed(() => {
  const p = realtime.value?.place
  return {
    labels: ['점유', '이탈', '미측정'],
    datasets: [
      {
        data: p ? [p.success, p.fail, p.midal] : [0, 0, 0],
        backgroundColor: ['#2563eb', '#ef4444', '#cbd5e1'],
        borderWidth: 0,
      },
    ],
  }
})

const webpageDoughnut = computed(() => {
  const w = realtime.value?.webpage
  return {
    labels: ['노출', '이탈', '미측정'],
    datasets: [
      {
        data: w ? [w.visible, w.fail, w.midal] : [0, 0, 0],
        backgroundColor: ['#10b981', '#ef4444', '#cbd5e1'],
        borderWidth: 0,
      },
    ],
  }
})

const doughnutOptions = {
  responsive: true,
  maintainAspectRatio: false,
  cutout: '65%',
  plugins: {
    legend: { display: false },
    tooltip: { enabled: true },
  },
}
</script>

<template>
  <section class="mt-4 space-y-3">
    <!-- 헤더 -->
    <div class="px-1">
      <h2 class="text-sm font-bold text-slate-700">대시보드</h2>
    </div>

    <!-- 로딩 placeholder -->
    <template v-if="loading">
      <div class="h-24 bg-slate-100 animate-pulse rounded-lg" />
      <div class="h-36 bg-slate-100 animate-pulse rounded-lg" />
    </template>

    <!-- 에러 -->
    <div
      v-else-if="error"
      class="px-3 py-2 bg-red-50 border border-red-200 rounded text-xs text-red-700"
    >
      {{ error }}
    </div>

    <!-- 정상 렌더 -->
    <template v-else-if="dashboardData">

      <!-- 1층: KPI 카드 5칸 (스파크라인 내장) -->
      <div class="grid grid-cols-5 gap-2">
        <div
          v-for="kpi in kpiCards"
          :key="kpi.key"
          class="bg-white border border-slate-200 rounded-lg p-3 flex flex-col"
        >
          <div class="text-[10px] text-slate-500">{{ kpi.label }}</div>

          <div class="flex items-baseline gap-2 mt-1">
            <span class="text-2xl font-bold text-slate-800 tabular-nums">{{ kpi.value }}</span>
            <span v-if="kpi.reference" class="text-[10px] text-slate-400">{{ kpi.reference }}</span>
          </div>

          <div class="text-[10px] mt-0.5 tabular-nums" :class="kpi.deltaClass">
            {{ kpi.delta }}
          </div>

          <div class="h-10 mt-2">
            <Line
              v-if="kpi.trend.filter(v => v !== null).length >= 2"
              :data="makeSparkData(kpi.trend, kpi.trendColor)"
              :options="sparkOptions"
            />
            <div v-else class="h-full flex items-center justify-center text-[10px] text-slate-300">
              추이 데이터 축적 중
            </div>
          </div>
        </div>
      </div>

      <!-- 2층: 실시간 도넛 2개 -->
      <div class="grid grid-cols-2 gap-3">
        <!-- 플레이스 -->
        <div class="bg-white border border-slate-200 rounded-lg p-3">
          <div class="flex items-center justify-between mb-2">
            <h3 class="text-xs font-semibold text-slate-700">플레이스 현황</h3>
            <span class="text-[10px] text-slate-400 tabular-nums">
              {{ realtime?.place.date ?? '—' }}
            </span>
          </div>
          <div
            v-if="!realtime || realtime.place.total === 0"
            class="text-center py-6 text-xs text-slate-400"
          >
            데이터 없음
          </div>
          <div v-else class="flex items-center gap-3">
            <div class="w-28 h-28 shrink-0">
              <Doughnut :data="placeDoughnut" :options="doughnutOptions" />
            </div>
            <dl class="text-xs space-y-1 flex-1">
              <div class="flex justify-between">
                <dt class="text-slate-500">점유</dt>
                <dd class="font-semibold text-blue-600 tabular-nums">{{ realtime.place.success }}</dd>
              </div>
              <div class="flex justify-between">
                <dt class="text-slate-500">이탈</dt>
                <dd class="font-semibold text-red-500 tabular-nums">{{ realtime.place.fail }}</dd>
              </div>
              <div class="flex justify-between">
                <dt class="text-slate-500">미측정</dt>
                <dd class="font-semibold text-slate-400 tabular-nums">{{ realtime.place.midal }}</dd>
              </div>
              <div class="flex justify-between border-t border-slate-100 pt-1 mt-1">
                <dt class="text-slate-500">총</dt>
                <dd class="font-semibold text-slate-700 tabular-nums">{{ realtime.place.total }}</dd>
              </div>
            </dl>
          </div>
        </div>

        <!-- 웹사이트 -->
        <div class="bg-white border border-slate-200 rounded-lg p-3">
          <div class="flex items-center justify-between mb-2">
            <h3 class="text-xs font-semibold text-slate-700">웹사이트 현황</h3>
            <span class="text-[10px] text-slate-400 tabular-nums">
              {{ realtime?.webpage.date ?? '—' }}
            </span>
          </div>
          <div
            v-if="!realtime || realtime.webpage.total === 0"
            class="text-center py-6 text-xs text-slate-400"
          >
            데이터 없음
          </div>
          <div v-else class="flex items-center gap-3">
            <div class="w-28 h-28 shrink-0">
              <Doughnut :data="webpageDoughnut" :options="doughnutOptions" />
            </div>
            <dl class="text-xs space-y-1 flex-1">
              <div class="flex justify-between">
                <dt class="text-slate-500">노출</dt>
                <dd class="font-semibold text-emerald-600 tabular-nums">{{ realtime.webpage.visible }}</dd>
              </div>
              <div class="flex justify-between">
                <dt class="text-slate-500">이탈</dt>
                <dd class="font-semibold text-red-500 tabular-nums">{{ realtime.webpage.fail }}</dd>
              </div>
              <div class="flex justify-between">
                <dt class="text-slate-500">미측정</dt>
                <dd class="font-semibold text-slate-400 tabular-nums">{{ realtime.webpage.midal }}</dd>
              </div>
              <div class="flex justify-between border-t border-slate-100 pt-1 mt-1">
                <dt class="text-slate-500">총</dt>
                <dd class="font-semibold text-slate-700 tabular-nums">{{ realtime.webpage.total }}</dd>
              </div>
            </dl>
          </div>
        </div>
      </div>

    </template>
  </section>
</template>

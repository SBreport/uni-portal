<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
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

const logs = ref<SyncLogEntry[]>([])
const loading = ref(true)
const error = ref('')
const expanded = ref<Set<number>>(new Set())

// sync_type → 라벨 매핑
const TYPE_LABEL: Record<string, string> = {
  event_sync: '이벤트',
  equipment_sync: '보유장비',
  cafe_sync: '카페',
  blog_notion_sync: '블로그',
  place_sheets_to_db: '플레이스',
  webpage_sheets_to_db: '웹페이지',
}

// sync_type → 뱃지 색상
const TYPE_COLOR: Record<string, string> = {
  event_sync: 'bg-violet-100 text-violet-700',
  equipment_sync: 'bg-teal-100 text-teal-700',
  cafe_sync: 'bg-orange-100 text-orange-700',
  blog_notion_sync: 'bg-indigo-100 text-indigo-700',
  place_sheets_to_db: 'bg-blue-100 text-blue-700',
  webpage_sheets_to_db: 'bg-green-100 text-green-700',
}

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

function resultText(entry: SyncLogEntry): string {
  const parts = [`완료 ${entry.added}건`]
  if (entry.skipped > 0) parts.push(`스킵 ${entry.skipped}건`)
  if (entry.conflicts > 0) parts.push(`충돌 ${entry.conflicts}건`)
  return parts.join(', ')
}

function toggleExpand(id: number) {
  if (expanded.value.has(id)) {
    expanded.value.delete(id)
  } else {
    expanded.value.add(id)
  }
}

async function fetchLogs() {
  try {
    const res = await api.get('/admin/sync-log?limit=50')
    logs.value = res.data
    // 실패 행은 기본 펼침
    const newExpanded = new Set<number>()
    for (const entry of res.data) {
      if (entry.is_failed) newExpanded.add(entry.id)
    }
    expanded.value = newExpanded
    error.value = ''
  } catch (e: any) {
    error.value = e.response?.data?.detail || '로그 조회 실패'
  } finally {
    loading.value = false
  }
}

// 외부에서 refresh() 호출 가능하도록 노출
async function refresh() {
  loading.value = true
  await fetchLogs()
}
defineExpose({ refresh })

// 30초 폴링 (탭 활성 시에만)
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
  <div class="bg-white border border-slate-200 rounded-lg">
    <!-- 헤더 -->
    <div class="flex items-center justify-between px-4 py-2.5 border-b border-slate-100">
      <span class="text-sm font-semibold text-slate-700">동기화 로그</span>
      <div class="flex items-center gap-3">
        <span class="text-xs text-slate-400">최근 50건</span>
        <button
          @click="refresh"
          :disabled="loading"
          class="p-1 rounded hover:bg-slate-100 text-slate-400 hover:text-slate-600 disabled:opacity-40 transition-colors"
          title="새로고침"
        >
          <svg class="w-4 h-4" :class="{ 'animate-spin': loading }" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
              d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
        </button>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading && logs.length === 0" class="px-4 py-6 text-center text-xs text-slate-400">
      불러오는 중...
    </div>

    <!-- Error -->
    <div v-else-if="error" class="px-4 py-4 text-xs text-red-600 bg-red-50">
      {{ error }}
    </div>

    <!-- Empty -->
    <div v-else-if="logs.length === 0" class="px-4 py-6 text-center text-xs text-slate-400">
      로그 없음
    </div>

    <!-- Success: 테이블 -->
    <div v-else class="overflow-auto max-h-96">
      <table class="text-xs whitespace-nowrap">
        <thead>
          <tr class="bg-slate-50 border-b border-slate-100 sticky top-0 z-10">
            <th class="text-left pl-3 pr-2 py-2 font-medium text-slate-500">시각</th>
            <th class="text-left px-2 py-2 font-medium text-slate-500">종류</th>
            <th class="text-left px-2 py-2 font-medium text-slate-500">트리거</th>
            <th class="text-left px-2 py-2 font-medium text-slate-500">결과</th>
            <th class="pl-2 pr-3 py-2 font-medium text-slate-500 text-center">상세</th>
          </tr>
        </thead>
        <tbody>
          <template v-for="entry in logs" :key="entry.id">
            <tr
              class="border-b border-slate-100 hover:bg-blue-50/30"
              :class="entry.is_failed ? 'bg-red-50' : ''"
            >
              <!-- 시각 -->
              <td class="pl-3 pr-2 py-1.5 text-slate-500 tabular-nums">{{ formatDate(entry.synced_at) }}</td>

              <!-- 종류 뱃지 -->
              <td class="px-2 py-1.5">
                <span
                  class="inline-block px-1.5 py-0.5 rounded text-xs font-medium"
                  :class="typeBadgeClass(entry.sync_type)"
                >{{ typeLabel(entry.sync_type) }}</span>
              </td>

              <!-- 트리거 -->
              <td class="px-2 py-1.5">
                <span class="inline-block px-1.5 py-0.5 rounded text-xs bg-slate-100 text-slate-500">
                  {{ entry.triggered_by === 'auto' ? '자동' : '수동' }}
                </span>
              </td>

              <!-- 결과 -->
              <td class="px-2 py-1.5" :class="entry.is_failed ? 'text-red-600' : 'text-slate-600'">
                {{ entry.is_failed ? '실패' : resultText(entry) }}
              </td>

              <!-- 펼치기 버튼 -->
              <td class="pl-2 pr-3 py-1.5 text-center">
                <button
                  v-if="entry.detail"
                  @click="toggleExpand(entry.id)"
                  class="text-slate-400 hover:text-slate-600"
                >
                  <svg class="w-3.5 h-3.5 transition-transform" :class="expanded.has(entry.id) ? 'rotate-180' : ''"
                    fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
                  </svg>
                </button>
                <span v-else class="text-slate-200">—</span>
              </td>
            </tr>

            <!-- 상세 펼침 행 -->
            <tr v-if="entry.detail && expanded.has(entry.id)"
              :key="`${entry.id}-detail`"
              class="border-b border-slate-100"
              :class="entry.is_failed ? 'bg-red-50' : 'bg-slate-50'"
            >
              <td colspan="5" class="pl-6 pr-3 py-2 text-xs text-slate-500 whitespace-pre-wrap break-all">
                {{ entry.detail }}
              </td>
            </tr>
          </template>
        </tbody>
      </table>
    </div>
  </div>
</template>

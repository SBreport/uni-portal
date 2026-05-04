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
  if (entry.is_failed) {
    const failParts = [`실패`]
    if (entry.added > 0) failParts.push(`완료 ${entry.added}건`)
    return failParts.join(' · ')
  }
  const parts = [`완료 ${entry.added}건`]
  if (entry.skipped > 0) parts.push(`스킵 ${entry.skipped}건`)
  if (entry.conflicts > 0) parts.push(`충돌 ${entry.conflicts}건`)
  return parts.join(' · ')
}

function triggerTooltip(triggered_by: string | null): string {
  return triggered_by === 'auto' ? '자동 실행' : '수동 실행'
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
    const res = await api.get('/admin/sync-log?limit=30')
    logs.value = res.data
    // 실패 항목은 기본 펼침
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
  <div class="bg-white border border-slate-200 rounded-lg flex flex-col max-h-[calc(100vh-8rem)]">
    <!-- 헤더 -->
    <div class="flex items-center justify-between px-3 py-2 border-b border-slate-100 flex-shrink-0">
      <span class="text-sm font-semibold text-slate-700">동기화 로그</span>
      <div class="flex items-center gap-2">
        <span class="text-xs text-slate-400">최근 30건</span>
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
    <div class="overflow-y-auto flex-1">
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
          v-for="entry in logs"
          :key="entry.id"
          class="rounded border cursor-pointer select-none"
          :class="entry.is_failed
            ? 'bg-red-50 border-red-200 hover:border-red-300'
            : 'bg-white border-slate-200 hover:border-slate-300'"
          :title="triggerTooltip(entry.triggered_by)"
          @click="entry.detail ? toggleExpand(entry.id) : undefined"
        >
          <!-- 카드 본문 -->
          <div class="flex items-center justify-between px-2.5 py-2 gap-2">
            <!-- 시각 -->
            <span class="text-[11px] tabular-nums text-slate-400 flex-shrink-0">
              {{ formatDate(entry.synced_at) }}
            </span>
            <!-- 종류 뱃지 -->
            <span
              class="text-[11px] px-1.5 py-0.5 rounded font-medium flex-shrink-0"
              :class="typeBadgeClass(entry.sync_type)"
            >{{ typeLabel(entry.sync_type) }}</span>
          </div>
          <!-- 결과 줄 -->
          <div class="px-2.5 pb-2 text-[11px] leading-none"
            :class="entry.is_failed ? 'text-red-600' : 'text-slate-600'">
            {{ resultText(entry) }}
          </div>

          <!-- 상세 (펼침) -->
          <div
            v-if="entry.detail && expanded.has(entry.id)"
            class="px-2.5 pb-2 text-[11px] text-slate-500 whitespace-pre-wrap break-all border-t"
            :class="entry.is_failed ? 'border-red-200' : 'border-slate-100'"
          >{{ entry.detail }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

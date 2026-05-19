<script setup lang="ts">
import { ref, onMounted } from 'vue'
import * as migrationsApi from '@/api/migrations'
import type { PendingMigration, MigrationHistory, PreviewResult } from '@/api/migrations'

// ── 서브탭 ────────────────────────────────────────────────────────────────
type SubTab = 'pending' | 'history'
const subTab = ref<SubTab>('pending')

// ── 데이터 ────────────────────────────────────────────────────────────────
const pending = ref<PendingMigration[]>([])
const history = ref<MigrationHistory[]>([])
const loadingPending = ref(false)
const loadingHistory = ref(false)

// ── 미리보기 모달 ─────────────────────────────────────────────────────────
const previewVisible = ref(false)
const previewData = ref<PreviewResult | null>(null)
const previewLoading = ref(false)

// ── 확인 모달 ─────────────────────────────────────────────────────────────
const confirmVisible = ref(false)
const confirmFilename = ref('')

// ── 적용 중 ───────────────────────────────────────────────────────────────
const applying = ref(false)

// ── 결과 메시지 ───────────────────────────────────────────────────────────
const resultMsg = ref('')
const resultError = ref(false)
const resultDetail = ref('')

function showResult(msg: string, isError: boolean, detail = '') {
  resultMsg.value = msg
  resultError.value = isError
  resultDetail.value = detail
  setTimeout(() => { resultMsg.value = '' }, 8000)
}

// ── 로드 ─────────────────────────────────────────────────────────────────
async function loadPending() {
  loadingPending.value = true
  try {
    const { data } = await migrationsApi.getPendingMigrations()
    pending.value = data
  } catch (e: any) {
    showResult(e.response?.data?.detail || '대기 목록 로딩 실패', true)
  } finally {
    loadingPending.value = false
  }
}

async function loadHistory() {
  loadingHistory.value = true
  try {
    const { data } = await migrationsApi.getMigrationHistory()
    history.value = data
  } catch (e: any) {
    showResult(e.response?.data?.detail || '이력 로딩 실패', true)
  } finally {
    loadingHistory.value = false
  }
}

async function refresh() {
  if (subTab.value === 'pending') {
    await loadPending()
  } else {
    await loadHistory()
  }
}

function switchTab(tab: SubTab) {
  subTab.value = tab
  if (tab === 'pending' && pending.value.length === 0) loadPending()
  if (tab === 'history' && history.value.length === 0) loadHistory()
}

// ── 미리보기 ─────────────────────────────────────────────────────────────
async function openPreview(filename: string) {
  previewVisible.value = true
  previewData.value = null
  previewLoading.value = true
  try {
    const { data } = await migrationsApi.previewMigration(filename)
    previewData.value = data
  } catch (e: any) {
    previewVisible.value = false
    showResult(e.response?.data?.detail || '미리보기 실패', true)
  } finally {
    previewLoading.value = false
  }
}

// ── 적용 확인 ─────────────────────────────────────────────────────────────
function askApply(filename: string) {
  confirmFilename.value = filename
  confirmVisible.value = true
}

async function confirmApply() {
  confirmVisible.value = false
  applying.value = true
  const filename = confirmFilename.value
  try {
    const { data } = await migrationsApi.applyMigration(filename)
    showResult(`적용 완료 — ${data.summary}`, false, `백업: ${data.backup_path}`)
    await loadPending()
    await loadHistory()
    if (subTab.value === 'pending' && pending.value.length === 0) {
      subTab.value = 'history'
    }
  } catch (e: any) {
    const detail = e.response?.data?.detail || '마이그레이션 실패'
    showResult('적용 실패', true, detail)
  } finally {
    applying.value = false
  }
}

// ── 파일 크기 포맷 ────────────────────────────────────────────────────────
function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  return `${(bytes / 1024).toFixed(1)} KB`
}

onMounted(() => {
  loadPending()
})
</script>

<template>
  <div class="h-full flex flex-col">
    <!-- 헤더 -->
    <div class="shrink-0 flex items-center justify-between mb-3">
      <h3 class="text-sm font-semibold text-slate-700">DB 마이그레이션</h3>
      <button
        @click="refresh"
        :disabled="loadingPending || loadingHistory"
        class="text-xs text-blue-600 hover:text-blue-800 disabled:opacity-50"
      >
        새로고침
      </button>
    </div>

    <!-- 결과 메시지 -->
    <div
      v-if="resultMsg"
      class="shrink-0 mb-3 px-3 py-2 rounded text-xs"
      :class="resultError ? 'bg-red-50 text-red-700 border border-red-200' : 'bg-emerald-50 text-emerald-700 border border-emerald-200'"
    >
      <p class="font-medium">{{ resultMsg }}</p>
      <p v-if="resultDetail" class="mt-0.5 font-mono text-[11px] opacity-75 break-all">{{ resultDetail }}</p>
    </div>

    <!-- 서브탭 -->
    <div class="shrink-0 flex gap-1 mb-3">
      <button
        @click="switchTab('pending')"
        :class="[
          'px-3 py-1.5 text-xs rounded border transition',
          subTab === 'pending'
            ? 'bg-blue-600 text-white border-blue-600'
            : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50'
        ]"
      >
        대기 중
        <span
          v-if="pending.length > 0"
          class="ml-1 px-1.5 py-0.5 rounded-full text-[10px] font-bold"
          :class="subTab === 'pending' ? 'bg-blue-400 text-white' : 'bg-amber-100 text-amber-700'"
        >{{ pending.length }}</span>
      </button>
      <button
        @click="switchTab('history')"
        :class="[
          'px-3 py-1.5 text-xs rounded border transition',
          subTab === 'history'
            ? 'bg-blue-600 text-white border-blue-600'
            : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50'
        ]"
      >
        적용 이력
      </button>
    </div>

    <!-- 본문: 스크롤 영역 -->
    <div class="flex-1 min-h-0 overflow-y-auto">

      <!-- 대기 중 탭 -->
      <div v-if="subTab === 'pending'">
        <!-- 로딩 -->
        <div v-if="loadingPending" class="flex items-center gap-2 py-12 justify-center text-slate-400 text-sm">
          <div class="w-4 h-4 border-2 border-blue-400 border-t-transparent rounded-full animate-spin"></div>
          로딩 중...
        </div>

        <!-- 빈 상태 -->
        <div v-else-if="pending.length === 0" class="flex flex-col items-center justify-center py-16 text-slate-400 gap-2">
          <svg class="w-8 h-8 opacity-40" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
              d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <p class="text-sm">대기 중인 마이그레이션 없음</p>
        </div>

        <!-- 목록 -->
        <div v-else class="flex flex-col gap-2">
          <div
            v-for="item in pending"
            :key="item.filename"
            class="border border-slate-200 rounded-lg bg-white p-3"
          >
            <div class="flex items-start justify-between gap-3">
              <div class="min-w-0 flex-1">
                <p class="font-mono text-xs font-semibold text-slate-800 truncate">{{ item.filename }}</p>
                <p class="text-[11px] text-slate-400 mt-0.5">
                  {{ item.lines }}줄 · {{ formatSize(item.size) }} · {{ item.modified_at }} 작성
                </p>
                <p v-if="item.summary_top" class="text-[11px] text-slate-500 mt-1 line-clamp-2 whitespace-pre-line">
                  {{ item.summary_top }}
                </p>
              </div>
              <div class="shrink-0 flex gap-1.5">
                <button
                  @click="openPreview(item.filename)"
                  class="px-2.5 py-1 text-xs text-slate-600 border border-slate-200 rounded hover:bg-slate-50 transition"
                >
                  미리보기
                </button>
                <button
                  @click="askApply(item.filename)"
                  :disabled="applying"
                  class="px-2.5 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 transition"
                >
                  {{ applying && confirmFilename === item.filename ? '적용 중...' : '적용' }}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 적용 이력 탭 -->
      <div v-if="subTab === 'history'">
        <!-- 로딩 -->
        <div v-if="loadingHistory" class="flex items-center gap-2 py-12 justify-center text-slate-400 text-sm">
          <div class="w-4 h-4 border-2 border-blue-400 border-t-transparent rounded-full animate-spin"></div>
          로딩 중...
        </div>

        <!-- 빈 상태 -->
        <div v-else-if="history.length === 0" class="flex flex-col items-center justify-center py-16 text-slate-400 gap-2">
          <p class="text-sm">적용 이력 없음</p>
        </div>

        <!-- 목록 -->
        <div v-else class="flex flex-col gap-2">
          <div
            v-for="item in history"
            :key="item.id"
            class="border rounded-lg bg-white p-3"
            :class="item.success ? 'border-slate-200' : 'border-red-200 bg-red-50'"
          >
            <div class="flex items-start justify-between gap-3">
              <div class="min-w-0 flex-1">
                <div class="flex items-center gap-2 mb-0.5">
                  <!-- 성공/실패 아이콘 -->
                  <span v-if="item.success" class="text-emerald-500 text-sm leading-none">✓</span>
                  <span v-else class="text-red-500 text-sm leading-none">✗</span>
                  <p class="font-mono text-xs font-semibold text-slate-800 truncate">{{ item.filename }}</p>
                </div>
                <p class="text-[11px] text-slate-400">
                  {{ item.applied_at?.slice(0, 16) }} · {{ item.applied_by || '-' }}
                </p>
                <p v-if="item.summary" class="text-[11px] text-slate-600 mt-0.5">
                  {{ item.summary }}
                </p>
                <p v-if="item.error_log" class="text-[11px] text-red-600 mt-0.5 font-mono break-all">
                  {{ item.error_log }}
                </p>
                <p v-if="item.backup_path" class="text-[11px] text-slate-400 mt-0.5 font-mono break-all">
                  백업: {{ item.backup_path }}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

    </div><!-- /본문 스크롤 영역 -->

    <!-- 미리보기 모달 -->
    <Teleport to="body">
      <div
        v-if="previewVisible"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
        @click.self="previewVisible = false"
      >
        <div class="bg-white rounded-lg shadow-xl flex flex-col w-[700px] max-w-[95vw] max-h-[80vh]">
          <div class="shrink-0 flex items-center justify-between px-4 py-3 border-b border-slate-200">
            <p class="font-mono text-sm font-semibold text-slate-700 truncate">
              {{ previewData?.filename ?? '...' }}
            </p>
            <div class="flex items-center gap-3">
              <span v-if="previewData" class="text-[11px] text-slate-400">{{ previewData.line_count }}줄</span>
              <button @click="previewVisible = false" class="text-slate-400 hover:text-slate-600 text-lg leading-none">×</button>
            </div>
          </div>
          <div class="flex-1 min-h-0 overflow-y-auto p-4">
            <div v-if="previewLoading" class="flex justify-center py-12 text-slate-400">
              <div class="w-5 h-5 border-2 border-blue-400 border-t-transparent rounded-full animate-spin"></div>
            </div>
            <pre v-else-if="previewData" class="text-[11px] text-slate-700 font-mono whitespace-pre-wrap break-words leading-relaxed">{{ previewData.content }}</pre>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- 적용 확인 모달 -->
    <Teleport to="body">
      <div
        v-if="confirmVisible"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
      >
        <div class="bg-white rounded-lg shadow-xl w-[480px] max-w-[95vw] p-5">
          <h4 class="text-sm font-semibold text-slate-800 mb-2">마이그레이션 적용</h4>
          <p class="font-mono text-xs text-blue-700 bg-blue-50 px-2 py-1 rounded mb-3 break-all">
            {{ confirmFilename }}
          </p>
          <p class="text-xs text-slate-600 mb-1">
            적용 전 DB 자동 백업이 생성됩니다. 실패 시 자동으로 복원됩니다.
          </p>
          <p class="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded px-2 py-1.5 mb-4">
            이 작업은 운영 DB에 직접 적용됩니다. 계속 진행하시겠습니까?
          </p>
          <div class="flex justify-end gap-2">
            <button
              @click="confirmVisible = false"
              class="px-4 py-1.5 text-xs text-slate-600 border border-slate-200 rounded hover:bg-slate-50"
            >
              취소
            </button>
            <button
              @click="confirmApply"
              class="px-4 py-1.5 text-xs bg-blue-600 text-white rounded hover:bg-blue-700"
            >
              적용
            </button>
          </div>
        </div>
      </div>
    </Teleport>

  </div>
</template>

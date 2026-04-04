<script setup lang="ts">
import { ref, onMounted } from 'vue'
import * as encApi from '@/api/encyclopedia'

const refreshing = ref(false)
const refreshResult = ref<any>(null)
const pendingItems = ref<any[]>([])
const pendingSummary = ref<any>({ total: 0, new: 0, removed: 0, recommend: 0 })
const approving = ref(false)
const error = ref('')
const successMsg = ref('')

async function loadPendingSummary() {
  try {
    const { data } = await encApi.getPendingSummary()
    pendingSummary.value = data
  } catch { /* ignore */ }
}

async function loadPending() {
  try {
    const { data } = await encApi.getPending()
    pendingItems.value = data
  } catch { /* ignore */ }
}

async function handleRefresh() {
  if (!confirm('태그 재추출 + 신규/삭제 감지를 실행합니다. 시간이 걸릴 수 있습니다.')) return
  refreshing.value = true
  refreshResult.value = null
  error.value = ''
  try {
    const { data } = await encApi.refreshEncyclopedia()
    refreshResult.value = data
    flashSuccess('갱신 완료')
    await loadPendingSummary()
    await loadPending()
  } catch (e: any) {
    error.value = e.response?.data?.detail || '갱신 실패'
  } finally {
    refreshing.value = false
  }
}

async function handleApprove(id: number) {
  await encApi.approvePending(id)
  pendingItems.value = pendingItems.value.filter(p => p.id !== id)
  await loadPendingSummary()
}

async function handleDismiss(id: number) {
  await encApi.dismissPending(id)
  pendingItems.value = pendingItems.value.filter(p => p.id !== id)
  await loadPendingSummary()
}

async function handleApproveAll() {
  if (!confirm('추천 태그가 있는 항목을 모두 승인합니다.')) return
  approving.value = true
  try {
    const { data } = await encApi.approveAll()
    flashSuccess(`${data.approved}건 승인 완료`)
    await loadPending()
    await loadPendingSummary()
  } catch { /* ignore */ }
  finally { approving.value = false }
}

function flashSuccess(msg: string) {
  successMsg.value = msg
  setTimeout(() => { successMsg.value = '' }, 3000)
}

onMounted(() => { loadPendingSummary(); loadPending() })
</script>

<template>
  <div>
    <!-- 메시지 -->
    <div v-if="error" class="mb-3 p-2 bg-red-50 border border-red-200 rounded text-xs text-red-600">{{ error }}</div>
    <div v-if="successMsg" class="mb-3 p-2 bg-green-50 border border-green-200 rounded text-xs text-green-600">{{ successMsg }}</div>

    <!-- 상단: 갱신 버튼 + 요약 -->
    <div class="flex items-center gap-3 mb-4 flex-wrap">
      <button @click="handleRefresh" :disabled="refreshing"
        class="px-3 py-1.5 text-xs font-medium bg-slate-600 text-white rounded hover:bg-slate-700 disabled:opacity-50 transition">
        {{ refreshing ? '갱신 중...' : '백과사전 갱신 (태그 재추출 + 감지)' }}
      </button>
      <div class="flex gap-2 text-xs">
        <span v-if="pendingSummary.new" class="px-2 py-0.5 bg-green-50 text-green-600 rounded">신규 {{ pendingSummary.new }}</span>
        <span v-if="pendingSummary.removed" class="px-2 py-0.5 bg-red-50 text-red-500 rounded">삭제 {{ pendingSummary.removed }}</span>
        <span v-if="pendingSummary.recommend" class="px-2 py-0.5 bg-blue-50 text-blue-600 rounded">추천 {{ pendingSummary.recommend }}</span>
        <span v-if="pendingSummary.total === 0" class="text-slate-400">대기 항목 없음</span>
      </div>
    </div>

    <!-- 갱신 결과 -->
    <div v-if="refreshResult" class="mb-4 p-3 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-600">
      태그 {{ refreshResult.extract?.total_tags?.toLocaleString() }}건 추출 (커버리지 {{ refreshResult.extract?.coverage }}) |
      신규 {{ refreshResult.diff?.new_items }}건 |
      삭제 {{ refreshResult.diff?.removed_items }}건 |
      추천 {{ refreshResult.diff?.untagged_recommended }}건 |
      미분류 {{ refreshResult.diff?.untagged_unknown }}건
    </div>

    <!-- 대기 항목 목록 -->
    <div v-if="pendingItems.length > 0" class="border border-slate-200 rounded-lg overflow-hidden">
      <div class="flex items-center justify-between px-3 py-2 bg-slate-50 border-b border-slate-200">
        <span class="text-xs font-bold text-slate-700">대기 항목 ({{ pendingItems.length }}건)</span>
        <button v-if="pendingItems.some(p => p.action === 'recommend')"
          @click="handleApproveAll" :disabled="approving"
          class="text-[10px] px-2.5 py-1 bg-green-500 text-white rounded hover:bg-green-600 disabled:opacity-50 transition">
          {{ approving ? '처리 중...' : '추천 전체 승인' }}
        </button>
      </div>
      <div class="max-h-96 overflow-y-auto">
        <div v-for="p in pendingItems" :key="p.id"
          class="flex items-center gap-2 px-3 py-2 border-b border-slate-50 text-xs hover:bg-slate-50/50">
          <span class="w-10 shrink-0 font-bold"
            :class="{ 'text-green-600': p.action === 'new', 'text-red-500': p.action === 'removed', 'text-blue-600': p.action === 'recommend' }">
            {{ p.action === 'new' ? '신규' : p.action === 'removed' ? '삭제' : '추천' }}
          </span>
          <span class="flex-1 text-slate-700 truncate" :title="p.source_name">{{ p.source_name }}</span>
          <span v-if="p.raw_category" class="text-[10px] text-slate-400 shrink-0 max-w-24 truncate">{{ p.raw_category }}</span>
          <span v-if="p.recommended_tags" class="text-[10px] text-blue-500 shrink-0 max-w-56 truncate" :title="p.recommended_tags">
            {{ p.recommended_tags }}
          </span>
          <button @click="handleApprove(p.id)" class="text-[10px] px-2 py-0.5 bg-green-50 text-green-600 rounded hover:bg-green-100 shrink-0">승인</button>
          <button @click="handleDismiss(p.id)" class="text-[10px] px-2 py-0.5 bg-slate-100 text-slate-400 rounded hover:bg-slate-200 shrink-0">무시</button>
        </div>
      </div>
    </div>
    <div v-else class="text-sm text-slate-400 py-8 text-center">
      대기 중인 항목이 없습니다. 이벤트 동기화 후 "백과사전 갱신"을 실행하면 신규/삭제/추천 항목이 표시됩니다.
    </div>
  </div>
</template>

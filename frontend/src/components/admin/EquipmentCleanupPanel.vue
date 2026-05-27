<script setup lang="ts">
import { ref, onMounted } from 'vue'
import * as cleanupApi from '@/api/equipment_cleanup'
import type {
  CleanupSummary,
  DuplicateGroup,
  EquipmentRow,
} from '@/api/equipment_cleanup'
import { getBranches } from '@/api/equipment'

// ── variant 유틸 ─────────────────────────────────────────────────────────

const VARIANT_COLORS = [
  { bg: 'bg-blue-100', text: 'text-blue-700' },
  { bg: 'bg-emerald-100', text: 'text-emerald-700' },
  { bg: 'bg-purple-100', text: 'text-purple-700' },
  { bg: 'bg-amber-100', text: 'text-amber-700' },
  { bg: 'bg-rose-100', text: 'text-rose-700' },
  { bg: 'bg-cyan-100', text: 'text-cyan-700' },
]

function variantColor(variant: string | null): { bg: string; text: string } {
  if (!variant) return { bg: 'bg-slate-100', text: 'text-slate-500' }
  let hash = 0
  for (let i = 0; i < variant.length; i++) {
    hash = (hash * 31 + variant.charCodeAt(i)) & 0xffffffff
  }
  return VARIANT_COLORS[Math.abs(hash) % VARIANT_COLORS.length]
}

// ── 요약 통계 ────────────────────────────────────────────────────────────
const summary = ref<CleanupSummary | null>(null)
const summaryLoading = ref(false)

async function loadSummary() {
  summaryLoading.value = true
  try {
    const { data } = await cleanupApi.getCleanupSummary()
    summary.value = data
  } catch (e) {
    console.error(e)
  } finally {
    summaryLoading.value = false
  }
}

// ── 지점 목록 ────────────────────────────────────────────────────────────
const branches = ref<{ id: number; name: string }[]>([])
const selectedBranch = ref<number | null>(null)

async function loadBranches() {
  try {
    const { data } = await getBranches()
    branches.value = data
  } catch (e) {
    console.error(e)
  }
}

// ── 중복 그룹 ────────────────────────────────────────────────────────────
const groups = ref<DuplicateGroup[]>([])
const totalGroups = ref(0)
const currentPage = ref(1)
const totalPages = ref(1)
const PAGE_SIZE = 20
const listLoading = ref(false)

async function loadDuplicates(page = 1) {
  listLoading.value = true
  currentPage.value = page
  try {
    const { data } = await cleanupApi.getDuplicates({
      branch_id: selectedBranch.value ?? undefined,
      page,
      page_size: PAGE_SIZE,
    })
    groups.value = data.groups
    totalGroups.value = data.total
    totalPages.value = data.total_pages
    // 병합 상태 초기화
    mergeState.value = {}
  } catch (e) {
    showMsg('중복 목록 로딩 실패', true)
  } finally {
    listLoading.value = false
  }
}

function refresh() {
  loadSummary()
  loadDuplicates(1)
}

// ── 통합 상태 (그룹별) ───────────────────────────────────────────────────
// key: `${branch_id}_${device_info_id}`
interface MergeState {
  selected: Set<number>  // 체크된 row id들
  targetId: number | null
  newName: string
  merging: boolean
}

const mergeState = ref<Record<string, MergeState>>({})

function stateKey(g: DuplicateGroup) {
  return `${g.branch_id}_${g.device_info_id}`
}

function getState(g: DuplicateGroup): MergeState {
  const k = stateKey(g)
  if (!mergeState.value[k]) {
    mergeState.value[k] = {
      selected: new Set(g.rows.map(r => r.id)),
      targetId: g.rows[0]?.id ?? null,
      newName: g.device_info_name || g.rows[0]?.name || '',
      merging: false,
    }
  }
  return mergeState.value[k]
}

function toggleRow(g: DuplicateGroup, rowId: number) {
  const s = getState(g)
  if (s.selected.has(rowId)) {
    s.selected.delete(rowId)
  } else {
    s.selected.add(rowId)
  }
}

function isAllSelected(g: DuplicateGroup) {
  const s = getState(g)
  return g.rows.every(r => s.selected.has(r.id))
}

function toggleAll(g: DuplicateGroup) {
  const s = getState(g)
  if (isAllSelected(g)) {
    g.rows.forEach(r => s.selected.delete(r.id))
  } else {
    g.rows.forEach(r => s.selected.add(r.id))
  }
}

// ── 통합 모달 ────────────────────────────────────────────────────────────
const confirmGroup = ref<DuplicateGroup | null>(null)
const confirmVisible = ref(false)

// variant 경고 모달
const variantWarnGroup = ref<DuplicateGroup | null>(null)
const variantWarnRows = ref<EquipmentRow[]>([])
const variantWarnVisible = ref(false)

function askMerge(g: DuplicateGroup) {
  const s = getState(g)
  const selectedRows = g.rows.filter(r => s.selected.has(r.id))
  if (selectedRows.length < 2) {
    showMsg('통합할 row를 2개 이상 선택하세요.', true)
    return
  }
  // target은 선택된 중 첫 번째
  s.targetId = selectedRows[0].id

  // 다른 variant가 섞여 있는지 확인
  const variants = new Set(selectedRows.map(r => r.variant ?? null))
  if (variants.size > 1) {
    // 경고 모달 먼저
    variantWarnGroup.value = g
    variantWarnRows.value = selectedRows
    variantWarnVisible.value = true
    return
  }

  confirmGroup.value = g
  confirmVisible.value = true
}

function proceedAfterVariantWarn() {
  variantWarnVisible.value = false
  if (!variantWarnGroup.value) return
  confirmGroup.value = variantWarnGroup.value
  confirmVisible.value = true
  variantWarnGroup.value = null
  variantWarnRows.value = []
}

async function confirmMerge() {
  const g = confirmGroup.value
  if (!g) return
  const s = getState(g)
  if (!s.targetId) return

  const selectedIds = [...s.selected]
  const sourceIds = selectedIds.filter(id => id !== s.targetId)
  if (sourceIds.length === 0) {
    showMsg('target 외에 병합할 row가 없습니다.', true)
    confirmVisible.value = false
    return
  }

  confirmVisible.value = false
  s.merging = true

  try {
    const { data } = await cleanupApi.mergeEquipment({
      branch_id: g.branch_id,
      device_info_id: g.device_info_id,
      target_row_id: s.targetId,
      source_row_ids: sourceIds,
      new_name: s.newName || undefined,
    })
    showMsg(`통합 완료 — "${data.new_name}" ${data.new_qty}대 (${data.merged_count}개 row 병합)`, false)
    await loadDuplicates(currentPage.value)
    await loadSummary()
  } catch (e: any) {
    showMsg(e.response?.data?.detail || '통합 실패', true)
  } finally {
    s.merging = false
  }
}

// ── variant 자동 선택 ────────────────────────────────────────────────────

/** 가장 많은 variant 그룹만 자동 선택 (null은 "미명시" 취급) */
function autoSelectByVariant(g: DuplicateGroup) {
  const s = getState(g)
  // variant별 row 목록 집계
  const buckets = new Map<string, number[]>()
  for (const row of g.rows) {
    const key = row.variant ?? '__미명시__'
    if (!buckets.has(key)) buckets.set(key, [])
    buckets.get(key)!.push(row.id)
  }
  // 가장 많은 bucket 선택
  let bestKey = ''
  let bestCount = 0
  for (const [k, ids] of buckets) {
    if (ids.length > bestCount) {
      bestCount = ids.length
      bestKey = k
    }
  }
  if (!bestKey) return
  s.selected.clear()
  for (const id of buckets.get(bestKey)!) {
    s.selected.add(id)
  }
  s.targetId = buckets.get(bestKey)![0]
}

// ── 재매핑 ───────────────────────────────────────────────────────────────
const remapLoading = ref(false)
const remapForce = ref(false)

async function runRemap() {
  remapLoading.value = true
  try {
    const { data } = await cleanupApi.remapEquipment({
      branch_id: selectedBranch.value ?? undefined,
      force: remapForce.value,
    })
    showMsg(
      `재매핑 완료 — ${data.remapped_count}건 매핑, ${data.unmatched_count}건 미매칭 (총 ${data.total_processed}건)`,
      false,
    )
    await loadSummary()
    await loadDuplicates(currentPage.value)
  } catch (e: any) {
    showMsg(e.response?.data?.detail || '재매핑 실패', true)
  } finally {
    remapLoading.value = false
  }
}

// ── 알림 메시지 ─────────────────────────────────────────────────────────
const msg = ref('')
const msgError = ref(false)
let msgTimer: ReturnType<typeof setTimeout> | null = null

function showMsg(text: string, isError: boolean) {
  msg.value = text
  msgError.value = isError
  if (msgTimer) clearTimeout(msgTimer)
  msgTimer = setTimeout(() => { msg.value = '' }, 8000)
}

// ── 유틸 ─────────────────────────────────────────────────────────────────
function selectedCount(g: DuplicateGroup): number {
  return getState(g).selected.size
}

function selectedQty(g: DuplicateGroup): number {
  const s = getState(g)
  return g.rows.filter(r => s.selected.has(r.id)).reduce((acc, r) => acc + r.qty, 0)
}

function pageNumbers() {
  const total = totalPages.value
  const cur = currentPage.value
  if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1)
  const pages: (number | '...')[] = [1]
  if (cur > 3) pages.push('...')
  for (let i = Math.max(2, cur - 1); i <= Math.min(total - 1, cur + 1); i++) pages.push(i)
  if (cur < total - 2) pages.push('...')
  pages.push(total)
  return pages
}

onMounted(() => {
  loadSummary()
  loadDuplicates(1)
  loadBranches()
})
</script>

<template>
  <div class="h-full flex flex-col">

    <!-- 요약 바 -->
    <div class="shrink-0 flex items-center gap-4 mb-3 px-3 py-2 bg-slate-50 border border-slate-200 rounded text-xs">
      <template v-if="summaryLoading">
        <span class="text-slate-400">통계 로딩 중...</span>
      </template>
      <template v-else-if="summary">
        <span class="text-slate-600">
          중복 그룹
          <span class="font-semibold text-amber-600 ml-1">{{ summary.duplicate_groups.toLocaleString() }}건</span>
        </span>
        <span class="text-slate-300">|</span>
        <span class="text-slate-600">
          초과 row
          <span class="font-semibold text-orange-600 ml-1">{{ summary.duplicate_excess_rows.toLocaleString() }}건</span>
        </span>
        <span class="text-slate-300">|</span>
        <span class="text-slate-600">
          미매핑
          <span class="font-semibold text-red-600 ml-1">{{ summary.null_mapping.toLocaleString() }}건</span>
        </span>
      </template>
    </div>

    <!-- 툴바 -->
    <div class="shrink-0 flex items-center gap-2 mb-3">
      <!-- 지점 필터 -->
      <select
        v-model="selectedBranch"
        class="text-xs border border-slate-200 rounded px-2 py-1.5 bg-white text-slate-700"
        @change="loadDuplicates(1)"
      >
        <option :value="null">전체 지점</option>
        <option v-for="b in branches" :key="b.id" :value="b.id">{{ b.name }}</option>
      </select>

      <!-- 재매핑 -->
      <div class="flex items-center gap-1.5 ml-auto">
        <label class="flex items-center gap-1 text-xs text-slate-500 cursor-pointer select-none">
          <input v-model="remapForce" type="checkbox" class="w-3 h-3" />
          강제 전체 재매핑
        </label>
        <button
          @click="runRemap"
          :disabled="remapLoading"
          class="px-3 py-1.5 text-xs rounded border bg-white text-slate-700 border-slate-300 hover:bg-slate-50 disabled:opacity-50"
        >
          {{ remapLoading ? '재매핑 중...' : '재매핑 실행' }}
        </button>
        <button
          @click="refresh"
          :disabled="listLoading"
          class="px-3 py-1.5 text-xs rounded border bg-white text-slate-700 border-slate-300 hover:bg-slate-50 disabled:opacity-50"
        >
          재검색
        </button>
      </div>
    </div>

    <!-- 메시지 -->
    <div
      v-if="msg"
      class="shrink-0 mb-3 px-3 py-2 rounded text-xs border"
      :class="msgError
        ? 'bg-red-50 text-red-700 border-red-200'
        : 'bg-emerald-50 text-emerald-700 border-emerald-200'"
    >
      {{ msg }}
    </div>

    <!-- 목록 헤더 -->
    <div v-if="!listLoading && totalGroups > 0" class="shrink-0 flex items-center justify-between mb-2">
      <span class="text-xs text-slate-500">
        중복 그룹 총 <span class="font-medium text-slate-700">{{ totalGroups.toLocaleString() }}</span>건
        ({{ currentPage }} / {{ totalPages }} 페이지)
      </span>
    </div>

    <!-- 본문 스크롤 영역 -->
    <div class="flex-1 min-h-0 overflow-y-auto">

      <!-- 로딩 -->
      <div v-if="listLoading" class="flex items-center justify-center h-24 text-sm text-slate-400">
        로딩 중...
      </div>

      <!-- 비어있음 -->
      <div v-else-if="groups.length === 0" class="flex items-center justify-center h-24 text-sm text-slate-400">
        중복 그룹이 없습니다.
      </div>

      <!-- 그룹 목록 -->
      <div v-else class="flex flex-col gap-3">
        <div
          v-for="g in groups"
          :key="`${g.branch_id}_${g.device_info_id}`"
          class="border border-slate-200 rounded bg-white"
        >
          <!-- 그룹 헤더 -->
          <div class="px-3 py-2 bg-slate-50 border-b border-slate-200 rounded-t">
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2 text-xs">
                <span class="font-semibold text-slate-700">{{ g.branch_name }}</span>
                <span class="text-slate-400">/</span>
                <span class="font-medium text-slate-700">{{ g.device_info_name }}</span>
                <span
                  v-if="g.category_name"
                  class="px-1.5 py-0.5 rounded text-[10px] bg-slate-100 text-slate-500"
                >{{ g.category_name }}</span>
              </div>
              <div class="text-xs text-slate-500">
                총 <span class="font-semibold text-slate-700">{{ g.total_qty }}대</span>
                <span class="ml-1 text-slate-400">({{ g.row_count }}개 row)</span>
              </div>
            </div>
            <!-- variant 요약 -->
            <div
              v-if="g.variant_summary && g.variant_summary.distinct_count > 0"
              class="flex items-center flex-wrap gap-1 mt-1.5"
            >
              <span class="text-[10px] text-slate-400">변형:</span>
              <template v-for="item in g.variant_summary.items" :key="item.variant">
                <span
                  class="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[10px] font-medium"
                  :class="[variantColor(item.variant === '미명시' ? null : item.variant).bg, variantColor(item.variant === '미명시' ? null : item.variant).text]"
                >
                  {{ item.variant }}<span v-if="item.count > 1" class="opacity-70"> ×{{ item.count }}</span>
                </span>
              </template>
            </div>
          </div>

          <!-- row 목록 -->
          <div class="px-3 py-2">
            <!-- 전체 선택 -->
            <div class="flex items-center gap-2 mb-2">
              <label class="flex items-center gap-1.5 text-[11px] text-slate-500 cursor-pointer select-none">
                <input
                  type="checkbox"
                  :checked="isAllSelected(g)"
                  @change="toggleAll(g)"
                  class="w-3 h-3"
                />
                전체 선택
              </label>
              <span v-if="selectedCount(g) > 0" class="text-[11px] text-slate-400">
                {{ selectedCount(g) }}개 선택 ({{ selectedQty(g) }}대)
              </span>
            </div>

            <!-- 개별 row -->
            <div class="flex flex-col gap-1 mb-3">
              <label
                v-for="row in g.rows"
                :key="row.id"
                class="flex items-center gap-2 px-2 py-1.5 rounded cursor-pointer select-none hover:bg-slate-50 border border-transparent"
                :class="getState(g).selected.has(row.id) ? 'border-blue-200 bg-blue-50' : ''"
              >
                <input
                  type="checkbox"
                  :checked="getState(g).selected.has(row.id)"
                  @change="toggleRow(g, row.id)"
                  class="w-3 h-3 shrink-0"
                />
                <span class="text-[11px] text-slate-400 font-mono shrink-0">id={{ row.id }}</span>
                <span class="text-xs font-medium text-slate-700 flex-1 truncate">{{ row.name }}</span>
                <!-- variant 뱃지 -->
                <span
                  class="shrink-0 px-1.5 py-0.5 rounded text-[10px] font-medium"
                  :class="[variantColor(row.variant).bg, variantColor(row.variant).text]"
                >{{ row.variant ?? '미명시' }}</span>
                <span class="text-[11px] text-slate-500 shrink-0">{{ row.qty }}대</span>
                <span
                  class="shrink-0 px-1.5 py-0.5 rounded text-[10px] bg-slate-100 text-slate-500"
                >{{ row.source }}</span>
                <span v-if="row.note" class="text-[11px] text-slate-400 shrink-0 truncate max-w-[100px]">
                  {{ row.note }}
                </span>
              </label>
            </div>

            <!-- 통합할 이름 + 버튼 -->
            <div class="flex items-center gap-2 flex-wrap">
              <span class="text-[11px] text-slate-500 shrink-0">통합 이름:</span>
              <input
                :value="getState(g).newName"
                @input="getState(g).newName = ($event.target as HTMLInputElement).value"
                type="text"
                class="flex-1 text-xs border border-slate-200 rounded px-2 py-1 min-w-0"
                :placeholder="g.device_info_name"
              />
              <!-- 같은 variant 자동 선택 버튼 (variant 2종 이상일 때만 표시) -->
              <button
                v-if="g.variant_summary && g.variant_summary.distinct_count > 1"
                @click="autoSelectByVariant(g)"
                class="shrink-0 px-2.5 py-1 text-xs rounded border border-slate-300 bg-white text-slate-600 hover:bg-slate-50"
                title="가장 많은 variant 그룹만 자동 선택"
              >
                같은 변형만 선택
              </button>
              <button
                @click="askMerge(g)"
                :disabled="getState(g).merging || selectedCount(g) < 2"
                class="shrink-0 px-3 py-1 text-xs rounded border bg-blue-600 text-white border-blue-600 hover:bg-blue-700 disabled:opacity-40 disabled:cursor-not-allowed"
              >
                {{ getState(g).merging ? '처리 중...' : '선택 row 합치기' }}
              </button>
            </div>
          </div>
        </div>

        <!-- 페이지네이션 -->
        <div class="flex items-center justify-center gap-1 py-3">
          <button
            @click="loadDuplicates(currentPage - 1)"
            :disabled="currentPage <= 1 || listLoading"
            class="px-2 py-1 text-xs rounded border border-slate-200 text-slate-600 hover:bg-slate-50 disabled:opacity-40"
          >
            이전
          </button>
          <template v-for="p in pageNumbers()" :key="p">
            <span v-if="p === '...'" class="px-1 text-xs text-slate-400">...</span>
            <button
              v-else
              @click="loadDuplicates(p as number)"
              :disabled="listLoading"
              class="px-2 py-1 text-xs rounded border transition"
              :class="p === currentPage
                ? 'bg-blue-600 text-white border-blue-600'
                : 'border-slate-200 text-slate-600 hover:bg-slate-50'"
            >
              {{ p }}
            </button>
          </template>
          <button
            @click="loadDuplicates(currentPage + 1)"
            :disabled="currentPage >= totalPages || listLoading"
            class="px-2 py-1 text-xs rounded border border-slate-200 text-slate-600 hover:bg-slate-50 disabled:opacity-40"
          >
            다음
          </button>
        </div>
      </div>
    </div>
  </div>

  <!-- variant 다름 경고 모달 -->
  <Teleport to="body">
    <div
      v-if="variantWarnVisible && variantWarnGroup"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
      @click.self="variantWarnVisible = false"
    >
      <div class="bg-white rounded-lg shadow-xl w-[420px] p-5">
        <h3 class="text-sm font-semibold text-amber-700 mb-3">서로 다른 변형 정보 경고</h3>

        <p class="text-xs text-slate-600 mb-3">
          선택한 row들이 서로 다른 변형(브랜드/기술/묶음) 정보를 가지고 있습니다.
          통합하면 변형 정보 구분이 손실됩니다.
        </p>

        <div class="mb-4 flex flex-col gap-1">
          <div
            v-for="row in variantWarnRows"
            :key="row.id"
            class="flex items-center gap-2 px-2 py-1 rounded bg-slate-50 text-xs"
          >
            <span class="text-slate-500 font-mono">id={{ row.id }}</span>
            <span class="flex-1 truncate text-slate-700">{{ row.name }}</span>
            <span
              class="shrink-0 px-1.5 py-0.5 rounded text-[10px] font-medium"
              :class="[variantColor(row.variant).bg, variantColor(row.variant).text]"
            >{{ row.variant ?? '미명시' }}</span>
          </div>
        </div>

        <p class="text-xs text-amber-600 mb-4">
          정말 이 row들을 하나로 합치시겠습니까?
        </p>

        <div class="flex justify-end gap-2">
          <button
            @click="variantWarnVisible = false"
            class="px-3 py-1.5 text-xs rounded border border-slate-200 text-slate-600 hover:bg-slate-50"
          >
            취소
          </button>
          <button
            @click="proceedAfterVariantWarn"
            class="px-3 py-1.5 text-xs rounded bg-amber-600 text-white hover:bg-amber-700"
          >
            그래도 통합
          </button>
        </div>
      </div>
    </div>
  </Teleport>

  <!-- 통합 확인 모달 -->
  <Teleport to="body">
    <div
      v-if="confirmVisible && confirmGroup"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
      @click.self="confirmVisible = false"
    >
      <div class="bg-white rounded-lg shadow-xl w-96 p-5">
        <h3 class="text-sm font-semibold text-slate-800 mb-3">통합 확인</h3>

        <div class="text-xs text-slate-600 mb-4 space-y-1">
          <p>
            <span class="font-medium">{{ confirmGroup.branch_name }}</span> /
            <span class="font-medium">{{ confirmGroup.device_info_name }}</span>
          </p>
          <p class="text-slate-400">
            선택한 {{ selectedCount(confirmGroup) }}개 row를 하나로 통합합니다.
          </p>
          <p class="mt-2">
            통합 이름:
            <span class="font-semibold text-slate-800">
              {{ getState(confirmGroup).newName || confirmGroup.device_info_name }}
            </span>
          </p>
          <p>
            합산 수량:
            <span class="font-semibold text-slate-800">{{ selectedQty(confirmGroup) }}대</span>
          </p>
          <p class="text-amber-600 mt-2">
            source row {{ selectedCount(confirmGroup) - 1 }}개가 삭제됩니다. 되돌릴 수 없습니다.
          </p>
        </div>

        <div class="flex justify-end gap-2">
          <button
            @click="confirmVisible = false"
            class="px-3 py-1.5 text-xs rounded border border-slate-200 text-slate-600 hover:bg-slate-50"
          >
            취소
          </button>
          <button
            @click="confirmMerge"
            class="px-3 py-1.5 text-xs rounded bg-blue-600 text-white hover:bg-blue-700"
          >
            통합 실행
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

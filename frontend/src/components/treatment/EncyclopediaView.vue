<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import * as encApi from '@/api/encyclopedia'

const auth = useAuthStore()
const isAdmin = computed(() => auth.role === 'admin')

// ── 탭: 목적별 / 부위별 / 장비별 ──
type Tab = 'purpose' | 'body' | 'equipment'
const activeTab = ref<Tab>('purpose')

// ── 목록 데이터 ──
const purposes = ref<any[]>([])
const bodyParts = ref<any[]>([])
const equipmentList = ref<any[]>([])
const loading = ref(false)

// ── 상세 데이터 ──
type DetailMode = 'list' | 'detail'
const mode = ref<DetailMode>('list')
const detailData = ref<any>(null)
const detailLoading = ref(false)
const detailTitle = ref('')
const detailType = ref<Tab>('purpose')

// ── 초기 로드 ──
async function loadLists() {
  loading.value = true
  try {
    const [p, b, e] = await Promise.all([
      encApi.getPurposes(),
      encApi.getBodyParts(),
      encApi.getEquipmentList(),
    ])
    purposes.value = p.data
    bodyParts.value = b.data
    equipmentList.value = e.data
  } catch { /* ignore */ }
  finally { loading.value = false }
}

// ── 상세 조회 ──
async function openPurpose(name: string) {
  mode.value = 'detail'
  detailType.value = 'purpose'
  detailTitle.value = name
  detailLoading.value = true
  try {
    const { data } = await encApi.getByPurpose(name)
    detailData.value = data
  } catch { detailData.value = null }
  finally { detailLoading.value = false }
}

async function openBodyPart(part: string) {
  mode.value = 'detail'
  detailType.value = 'body'
  detailTitle.value = part
  detailLoading.value = true
  try {
    const { data } = await encApi.getByBodyPart(part)
    detailData.value = data
  } catch { detailData.value = null }
  finally { detailLoading.value = false }
}

async function openEquipment(name: string) {
  mode.value = 'detail'
  detailType.value = 'equipment'
  detailTitle.value = name
  detailLoading.value = true
  try {
    const { data } = await encApi.getByEquipment(name)
    detailData.value = data
  } catch { detailData.value = null }
  finally { detailLoading.value = false }
}

function goBack() {
  mode.value = 'list'
  detailData.value = null
}

function formatPrice(val: number | null): string {
  if (!val) return '-'
  if (val >= 10000) return Math.round(val / 10000) + '만원'
  return val.toLocaleString() + '원'
}

function priceRange(min: number | null, max: number | null): string {
  if (!min && !max) return '-'
  if (min === max) return formatPrice(min)
  return `${formatPrice(min)} ~ ${formatPrice(max)}`
}

// ── 관리자: 갱신 + pending ──
const refreshing = ref(false)
const refreshResult = ref<any>(null)
const pendingItems = ref<any[]>([])
const pendingSummary = ref<any>({ total: 0 })
const showPending = ref(false)
const approving = ref(false)

async function loadPendingSummary() {
  try {
    const { data } = await encApi.getPendingSummary()
    pendingSummary.value = data
  } catch { /* ignore */ }
}

async function handleRefresh() {
  if (!confirm('태그 재추출 + 신규/삭제 감지를 실행합니다.')) return
  refreshing.value = true
  refreshResult.value = null
  try {
    const { data } = await encApi.refreshEncyclopedia()
    refreshResult.value = data
    await loadPendingSummary()
    await loadLists()
  } catch { /* ignore */ }
  finally { refreshing.value = false }
}

async function loadPending() {
  showPending.value = true
  try {
    const { data } = await encApi.getPending()
    pendingItems.value = data
  } catch { /* ignore */ }
}

async function handleApprove(id: number) {
  await encApi.approvePending(id)
  pendingItems.value = pendingItems.value.filter(p => p.id !== id)
  pendingSummary.value.total = Math.max(0, pendingSummary.value.total - 1)
}

async function handleDismiss(id: number) {
  await encApi.dismissPending(id)
  pendingItems.value = pendingItems.value.filter(p => p.id !== id)
  pendingSummary.value.total = Math.max(0, pendingSummary.value.total - 1)
}

async function handleApproveAll() {
  if (!confirm('추천 태그가 있는 항목을 모두 승인합니다.')) return
  approving.value = true
  try {
    const { data } = await encApi.approveAll()
    pendingItems.value = pendingItems.value.filter(p => p.action !== 'recommend')
    await loadPendingSummary()
    alert(`${data.approved}건 승인 완료`)
  } catch { /* ignore */ }
  finally { approving.value = false }
}

onMounted(() => { loadLists(); loadPendingSummary() })
</script>

<template>
  <div>
    <!-- 관리자 패널 -->
    <div v-if="isAdmin" class="mb-4 flex items-center gap-2 flex-wrap">
      <button @click="handleRefresh" :disabled="refreshing"
        class="px-3 py-1.5 text-xs font-medium bg-slate-600 text-white rounded hover:bg-slate-700 disabled:opacity-50 transition">
        {{ refreshing ? '갱신 중...' : '백과사전 갱신' }}
      </button>
      <button v-if="pendingSummary.total > 0" @click="loadPending"
        class="px-3 py-1.5 text-xs font-medium bg-amber-500 text-white rounded hover:bg-amber-600 transition">
        대기 항목 {{ pendingSummary.total }}건
      </button>
      <span v-if="refreshResult" class="text-[11px] text-slate-400">
        추출 {{ refreshResult.extract?.total_tags?.toLocaleString() }}태그 |
        신규 {{ refreshResult.diff?.new_items }}건 |
        삭제 {{ refreshResult.diff?.removed_items }}건 |
        추천 {{ refreshResult.diff?.untagged_recommended }}건
      </span>
    </div>

    <!-- pending 목록 (모달 대신 인라인) -->
    <div v-if="showPending && pendingItems.length > 0" class="mb-4 border border-amber-200 rounded-lg overflow-hidden">
      <div class="flex items-center justify-between px-3 py-2 bg-amber-50 border-b border-amber-200">
        <span class="text-xs font-bold text-amber-700">대기 항목 ({{ pendingItems.length }}건)</span>
        <div class="flex gap-2">
          <button @click="handleApproveAll" :disabled="approving"
            class="text-[10px] px-2 py-0.5 bg-green-500 text-white rounded hover:bg-green-600 disabled:opacity-50">
            {{ approving ? '처리 중...' : '추천 전체 승인' }}
          </button>
          <button @click="showPending = false" class="text-[10px] text-slate-400 hover:underline">닫기</button>
        </div>
      </div>
      <div class="max-h-64 overflow-y-auto">
        <div v-for="p in pendingItems" :key="p.id"
          class="flex items-center gap-2 px-3 py-1.5 border-b border-amber-50 text-xs hover:bg-amber-50/50">
          <span class="w-12 shrink-0 font-medium"
            :class="{ 'text-green-600': p.action === 'new', 'text-red-500': p.action === 'removed', 'text-blue-600': p.action === 'recommend' }">
            {{ p.action === 'new' ? '신규' : p.action === 'removed' ? '삭제' : '추천' }}
          </span>
          <span class="flex-1 text-slate-700 truncate">{{ p.source_name }}</span>
          <span v-if="p.raw_category" class="text-[10px] text-slate-400 shrink-0">{{ p.raw_category }}</span>
          <span v-if="p.recommended_tags" class="text-[10px] text-blue-500 shrink-0 max-w-48 truncate">{{ p.recommended_tags }}</span>
          <button @click="handleApprove(p.id)" class="text-[10px] text-green-600 hover:underline shrink-0">승인</button>
          <button @click="handleDismiss(p.id)" class="text-[10px] text-slate-400 hover:underline shrink-0">무시</button>
        </div>
      </div>
    </div>

    <!-- 목록 모드 -->
    <template v-if="mode === 'list'">
      <!-- 탭 -->
      <div class="flex gap-3 mb-4 border-b border-slate-200">
        <button v-for="tab in [
          { key: 'purpose', label: '목적별' },
          { key: 'body', label: '부위별' },
          { key: 'equipment', label: '장비별' },
        ]" :key="tab.key" @click="activeTab = tab.key as Tab"
          :class="['pb-2 text-sm font-medium border-b-2 transition',
            activeTab === tab.key ? 'border-blue-600 text-blue-600' : 'border-transparent text-slate-400 hover:text-slate-600']">
          {{ tab.label }}
        </button>
      </div>

      <div v-if="loading" class="text-sm text-slate-400 py-8 text-center">로딩 중...</div>

      <!-- ═══ 목적별 ═══ -->
      <template v-else-if="activeTab === 'purpose'">
        <div class="grid grid-cols-3 gap-2">
          <button v-for="p in purposes" :key="p.name" @click="openPurpose(p.name)"
            class="flex items-center justify-between px-4 py-3 bg-white border border-slate-200 rounded-lg hover:border-blue-300 hover:bg-blue-50/50 transition text-left">
            <span class="text-sm font-medium text-slate-700">{{ p.name }}</span>
            <span class="text-xs text-slate-400">{{ p.count }}건</span>
          </button>
        </div>
      </template>

      <!-- ═══ 부위별 ═══ -->
      <template v-else-if="activeTab === 'body'">
        <div class="space-y-4">
          <div v-for="region in bodyParts" :key="region.region"
            class="bg-white border border-slate-200 rounded-lg p-3">
            <div class="text-xs font-bold text-slate-500 mb-2">{{ region.region }}</div>
            <div class="flex flex-wrap gap-1.5">
              <button v-for="part in region.parts" :key="part.name" @click="openBodyPart(part.name)"
                class="px-3 py-1.5 text-xs bg-slate-50 border border-slate-200 rounded-full hover:border-blue-300 hover:bg-blue-50 transition">
                {{ part.name }} <span class="text-slate-400 ml-0.5">{{ part.count }}</span>
              </button>
            </div>
          </div>
        </div>
      </template>

      <!-- ═══ 장비별 ═══ -->
      <template v-else-if="activeTab === 'equipment'">
        <div class="space-y-1">
          <button v-for="eq in equipmentList" :key="eq.name" @click="openEquipment(eq.name)"
            class="w-full flex items-center gap-3 px-4 py-2.5 bg-white border border-slate-200 rounded-lg hover:border-blue-300 hover:bg-blue-50/50 transition text-left">
            <span class="text-sm font-medium text-slate-700 w-28 shrink-0">{{ eq.name }}</span>
            <span v-if="eq.branch_count" class="text-xs text-blue-500">{{ eq.branch_count }}지점</span>
            <span class="text-xs text-slate-400 flex-1 truncate">{{ eq.summary || '' }}</span>
          </button>
        </div>
      </template>
    </template>

    <!-- ═══ 상세 모드 ═══ -->
    <template v-else>
      <button @click="goBack" class="text-xs text-blue-500 hover:underline mb-3 flex items-center gap-1">
        <span>&larr;</span>
        <span v-if="detailType === 'purpose'">목적별</span>
        <span v-else-if="detailType === 'body'">부위별</span>
        <span v-else>장비별</span>
        목록으로
      </button>

      <h3 class="text-lg font-bold text-slate-800 mb-4">{{ detailTitle }}</h3>

      <div v-if="detailLoading" class="text-sm text-slate-400 py-8 text-center">로딩 중...</div>

      <!-- 목적별 상세: 부위 → 장비 -->
      <template v-else-if="detailType === 'purpose' && detailData">
        <div v-if="!detailData.body_parts?.length" class="text-sm text-slate-400 py-4">데이터가 없습니다.</div>
        <div v-else class="space-y-4">
          <div v-for="bp in detailData.body_parts" :key="bp.part"
            class="bg-white border border-slate-200 rounded-lg overflow-hidden">
            <div class="px-3 py-2 bg-slate-50 border-b border-slate-200 flex items-center gap-2">
              <span class="text-xs font-bold text-slate-700">{{ bp.part }}</span>
              <span class="text-[10px] text-slate-400">{{ bp.region }}</span>
            </div>
            <div class="divide-y divide-slate-50">
              <div v-for="eq in bp.equipment" :key="eq.name"
                class="px-3 py-2 flex items-center gap-3 hover:bg-blue-50/30 cursor-pointer"
                @click="eq.type === '장비' ? openEquipment(eq.name) : null">
                <span class="text-xs font-medium text-slate-700 w-24 shrink-0">{{ eq.name }}</span>
                <span class="text-[10px] px-1.5 py-0.5 rounded shrink-0"
                  :class="eq.type === '장비' ? 'bg-blue-100 text-blue-600' : 'bg-amber-100 text-amber-600'">
                  {{ eq.type }}
                </span>
                <span v-if="eq.branch_count" class="text-[11px] text-blue-500 shrink-0">{{ eq.branch_count }}지점</span>
                <span class="text-[11px] text-slate-400 shrink-0">{{ priceRange(eq.price_min, eq.price_max) }}</span>
                <span class="text-[11px] text-slate-300 flex-1 truncate">{{ eq.summary || '' }}</span>
              </div>
            </div>
          </div>
        </div>
      </template>

      <!-- 부위별 상세: 목적 → 장비 -->
      <template v-else-if="detailType === 'body' && detailData">
        <div v-if="!detailData.purposes?.length" class="text-sm text-slate-400 py-4">데이터가 없습니다.</div>
        <div v-else class="space-y-4">
          <div v-for="pr in detailData.purposes" :key="pr.purpose"
            class="bg-white border border-slate-200 rounded-lg overflow-hidden">
            <div class="px-3 py-2 bg-slate-50 border-b border-slate-200">
              <span class="text-xs font-bold text-slate-700">{{ pr.purpose }}</span>
            </div>
            <div class="divide-y divide-slate-50">
              <div v-for="eq in pr.equipment" :key="eq.name"
                class="px-3 py-2 flex items-center gap-3 hover:bg-blue-50/30 cursor-pointer"
                @click="eq.type === '장비' ? openEquipment(eq.name) : null">
                <span class="text-xs font-medium text-slate-700 w-24 shrink-0">{{ eq.name }}</span>
                <span class="text-[10px] px-1.5 py-0.5 rounded shrink-0"
                  :class="eq.type === '장비' ? 'bg-blue-100 text-blue-600' : 'bg-amber-100 text-amber-600'">
                  {{ eq.type }}
                </span>
                <span v-if="eq.branch_count" class="text-[11px] text-blue-500 shrink-0">{{ eq.branch_count }}지점</span>
                <span class="text-[11px] text-slate-400 shrink-0">{{ priceRange(eq.price_min, eq.price_max) }}</span>
                <span class="text-[11px] text-slate-300 flex-1 truncate">{{ eq.summary || '' }}</span>
              </div>
            </div>
          </div>
        </div>
      </template>

      <!-- 장비별 상세 -->
      <template v-else-if="detailType === 'equipment' && detailData">
        <!-- 장비 정보 카드 -->
        <div v-if="detailData.device_info" class="bg-white border border-slate-200 rounded-lg p-4 mb-4">
          <div class="text-xs text-slate-400 mb-1">장비 정보</div>
          <div class="text-sm text-slate-700 mb-2">{{ detailData.device_info.summary }}</div>
          <div v-if="detailData.device_info.target" class="text-xs text-slate-500">적용 부위: {{ detailData.device_info.target }}</div>
          <div v-if="detailData.device_info.mechanism" class="text-xs text-slate-500 mt-1">작용 원리: {{ detailData.device_info.mechanism }}</div>
          <div class="text-xs text-slate-400 mt-2">가격 범위: {{ priceRange(detailData.price_min, detailData.price_max) }}</div>
        </div>

        <!-- 적용 부위 -->
        <div v-if="detailData.body_parts?.length" class="mb-4">
          <div class="text-xs font-bold text-slate-500 mb-2">적용 부위</div>
          <div class="flex flex-wrap gap-1.5">
            <button v-for="bp in detailData.body_parts" :key="bp.part" @click="openBodyPart(bp.part)"
              class="px-2.5 py-1 text-xs bg-slate-50 border border-slate-200 rounded-full hover:border-blue-300 hover:bg-blue-50 transition">
              {{ bp.part }} <span class="text-slate-400">{{ bp.count }}</span>
            </button>
          </div>
        </div>

        <!-- 시술 목적 -->
        <div v-if="detailData.purposes?.length" class="mb-4">
          <div class="text-xs font-bold text-slate-500 mb-2">시술 목적</div>
          <div class="flex flex-wrap gap-1.5">
            <button v-for="p in detailData.purposes" :key="p.name" @click="openPurpose(p.name)"
              class="px-2.5 py-1 text-xs bg-blue-50 border border-blue-200 rounded-full hover:bg-blue-100 transition">
              {{ p.name }} <span class="text-blue-400">{{ p.count }}</span>
            </button>
          </div>
        </div>

        <!-- 보유 지점 -->
        <div v-if="detailData.branches?.length" class="mb-4">
          <div class="text-xs font-bold text-slate-500 mb-2">보유 지점 ({{ detailData.branches.length }}개)</div>
          <div class="flex flex-wrap gap-1">
            <span v-for="b in detailData.branches" :key="b.branch_name"
              class="px-2 py-0.5 text-[11px] bg-green-50 border border-green-200 rounded text-green-700">
              {{ b.branch_name?.replace('유앤아이', '') }}
            </span>
          </div>
        </div>
      </template>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useAuthStore } from '@/stores/auth'
import * as encApi from '@/api/encyclopedia'
import TabBar from '@/components/common/TabBar.vue'
import { stripBrand } from '@/utils/branchName'

const props = defineProps<{ externalEquipment?: string }>()
const emit = defineEmits<{ (e: 'equipment-handled'): void }>()

const auth = useAuthStore()
const isAdmin = computed(() => auth.role === 'admin')

// ── 탭: 목적별 / 부위별 / 장비별 ──
type Tab = 'purpose' | 'body' | 'equipment'
const activeTab = ref<Tab>('purpose')
const tabs = [
  { key: 'purpose', label: '목적별' },
  { key: 'body', label: '부위별' },
  { key: 'equipment', label: '장비별' },
]

// ── 목록 데이터 ──
const purposes = ref<any[]>([])
const bodyParts = ref<any[]>([])
const equipmentList = ref<any[]>([])
const loading = ref(false)
const notFoundHint = ref<string>('')

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

function normalizeEqName(s: string) {
  return s.trim().normalize('NFC').toLowerCase()
}

async function handleExternalEquipment(name: string | undefined) {
  if (!name) return
  activeTab.value = 'equipment'
  const target = normalizeEqName(name)

  // 1차: 정확 매칭 (정규화)
  let matched = equipmentList.value.find((eq: any) => normalizeEqName(eq.name) === target)

  // 2차: 부분 매칭 (양방향 includes) — equipment.name variant 대응
  if (!matched) {
    matched = equipmentList.value.find((eq: any) => {
      const a = normalizeEqName(eq.name)
      return a.includes(target) || target.includes(a)
    })
  }

  if (matched) {
    notFoundHint.value = ''
    await openEquipment(matched.name)
    emit('equipment-handled')
    return
  }

  // 3차: 서버 직접 호출 (equipmentList가 아직 로드 전이거나 tag에 없는 경우 대응)
  try {
    const { data } = await encApi.getByEquipment(name)
    const hasContent = data && (
      data.body_parts?.length || data.purposes?.length ||
      data.branches?.length || data.device_info
    )
    if (hasContent) {
      notFoundHint.value = ''
      detailTitle.value = name
      detailType.value = 'equipment'
      detailData.value = data
      mode.value = 'detail'
      emit('equipment-handled')
      return
    }
  } catch { /* ignore, fall through */ }

  // 최종: 진짜 매칭 실패
  notFoundHint.value = name
  mode.value = 'list'
  detailData.value = null
  emit('equipment-handled')
}

onMounted(async () => { await loadLists(); loadPendingSummary(); await handleExternalEquipment(props.externalEquipment) })
watch(() => props.externalEquipment, (v) => { handleExternalEquipment(v) })
</script>

<template>
  <div>
    <!-- 목록 모드 -->
    <template v-if="mode === 'list'">
      <!-- 탭 -->
      <TabBar :model-value="activeTab" :tabs="tabs" @update:model-value="(v) => activeTab = v as Tab" />

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
        <p v-if="notFoundHint" class="text-xs text-amber-600 mb-2">
          '{{ notFoundHint }}'과(와) 일치하는 장비 정보를 찾지 못했습니다. 아래 목록에서 선택해주세요.
        </p>
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
              {{ stripBrand(b.branch_name) }}
            </span>
          </div>
        </div>
      </template>
    </template>
  </div>
</template>

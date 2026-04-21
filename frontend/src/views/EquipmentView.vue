<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useEquipmentStore } from '@/stores/equipment'
import { useAuthStore } from '@/stores/auth'
import * as equipApi from '@/api/equipment'
import * as papersApi from '@/api/papers'
import { usePanelResize } from '@/composables/useResizePanel'
import { useAsyncAction } from '@/composables/useAsyncAction'
import FilterSelect from '@/components/common/FilterSelect.vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import EmptyState from '@/components/common/EmptyState.vue'

const store = useEquipmentStore()
const auth = useAuthStore()

// 패널 리사이즈
const { leftWidth, startResize } = usePanelResize({ initialRatio: 0.55 })

// 수정 추적
const pendingChanges = ref<Map<number, Record<string, any>>>(new Map())
const { loading: saving, message: saveMsg, error: saveError, execute: executeSave } = useAsyncAction()

// 상세 패널
const selectedRow = ref<any>(null)
const detailLoading = ref(false)
const detailData = ref<{
  device_info: any | null
  events: any[]
  is_owned: boolean
  quantity: number
} | null>(null)
const detailPapers = ref<any[]>([])

onMounted(async () => {
  try {
    await Promise.all([store.loadBranches(), store.loadCategories()])
    await store.loadEquipment()
  } catch (e) {
    console.error('[EquipmentView] 초기 데이터 로드 실패:', e)
  }
})

// 사진 토글
function togglePhoto(row: any) {
  const id = row.id
  const current = row['사진'] === '있음'
  const newVal = !current
  row['사진'] = newVal ? '있음' : ''
  if (!pendingChanges.value.has(id)) pendingChanges.value.set(id, {})
  pendingChanges.value.get(id)!.photo_status = newVal ? 1 : 0
}

// 수량 변경
function updateQuantity(row: any, val: string) {
  const id = row.id
  const num = parseInt(val) || 1
  row['수량'] = num
  if (!pendingChanges.value.has(id)) pendingChanges.value.set(id, {})
  pendingChanges.value.get(id)!.quantity = num
}

// 비고 변경
function updateNote(row: any, val: string) {
  const id = row.id
  row['비고'] = val
  if (!pendingChanges.value.has(id)) pendingChanges.value.set(id, {})
  pendingChanges.value.get(id)!.note = val
}

// 일괄 저장
async function saveAll() {
  if (pendingChanges.value.size === 0) return
  const count = pendingChanges.value.size
  await executeSave(async () => {
    const promises = Array.from(pendingChanges.value.entries()).map(([id, changes]) =>
      equipApi.updateEquipment(id, changes)
    )
    await Promise.all(promises)
    pendingChanges.value.clear()
    return `${count}건 저장 완료`
  })
}

// 장비 클릭 → 상세 로드
async function openDetail(row: any) {
  if (selectedRow.value?.id === row.id) return
  selectedRow.value = row
  detailLoading.value = true
  detailData.value = null
  detailPapers.value = []
  try {
    const { data } = await equipApi.getEquipmentContext(row['지점'], row['기기명'])
    detailData.value = data
    // 관련 논문 로드 (device_info_id가 있을 때)
    if (data.device_info?.id) {
      try {
        const { data: papers } = await papersApi.getPapersByDevice(data.device_info.id)
        detailPapers.value = papers
      } catch { /* 논문 없으면 무시 */ }
    }
  } catch {
    detailData.value = { device_info: null, events: [], is_owned: false, quantity: 0 }
  } finally {
    detailLoading.value = false
  }
}

const canEdit = ['admin', 'editor', 'branch'].includes(auth.role)

const branchOptions = computed(() => store.branches.map(b => ({ value: b.name, label: b.name })))
const categoryOptions = computed(() => store.categories.map(c => ({ value: c.name, label: c.name })))

function handleSearch() {
  store.loadEquipment()
}

function formatPrice(n: number | null) {
  if (!n) return '-'
  return n.toLocaleString() + '원'
}
</script>

<template>
  <div class="p-5 h-full flex flex-col">
    <div class="flex items-center justify-between mb-3">
      <h2 class="text-xl font-bold text-slate-800">보유장비</h2>
      <div v-if="canEdit" class="flex items-center gap-3">
        <span v-if="saveMsg || saveError" class="text-sm" :class="saveError ? 'text-red-500' : 'text-emerald-600'">{{ saveError || saveMsg }}</span>
        <span v-if="pendingChanges.size > 0" class="text-xs text-amber-600 bg-amber-50 px-2 py-1 rounded">
          {{ pendingChanges.size }}건 변경됨
        </span>
        <button @click="saveAll" :disabled="pendingChanges.size === 0 || saving"
          class="px-4 py-1.5 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 disabled:opacity-40 transition">
          {{ saving ? '저장 중...' : '변경사항 저장' }}
        </button>
      </div>
    </div>

    <!-- 필터 바 -->
    <div class="flex items-center gap-3 mb-3 flex-wrap">
      <FilterSelect
        v-model="store.filterBranch"
        :options="branchOptions"
        placeholder="전체 지점"
        @update:model-value="handleSearch"
      />

      <FilterSelect
        v-model="store.filterCategory"
        :options="categoryOptions"
        placeholder="전체 카테고리"
        @update:model-value="handleSearch"
      />

      <input v-model="store.filterSearch" placeholder="장비명 검색 (Enter)"
        class="px-3 py-1.5 border border-slate-300 rounded-md text-sm w-48 focus:outline-none focus:ring-1 focus:ring-blue-400"
        @keyup.enter="handleSearch" />

      <span class="text-xs text-slate-400">{{ store.rows.length.toLocaleString() }}건</span>
    </div>

    <!-- 2컬럼: 테이블(좌) + 상세 정보(우, 상시 존재) -->
    <div class="flex flex-1 min-h-0">

      <!-- ===== 좌측: 장비 테이블 ===== -->
      <div :style="{ width: leftWidth + 'px' }" class="shrink-0 bg-white border border-slate-200 rounded-lg overflow-hidden flex flex-col">
        <div class="overflow-auto flex-1">
          <table class="w-full text-xs">
            <thead class="bg-slate-50 border-b border-slate-200 sticky top-0 z-10">
              <tr>
                <th class="text-left pl-3 pr-1 py-2 font-medium text-slate-500 whitespace-nowrap w-14">지점</th>
                <th class="text-left px-1 py-2 font-medium text-slate-500 whitespace-nowrap w-16">카테고리</th>
                <th class="text-left px-1 py-2 font-medium text-slate-500 whitespace-nowrap w-28">장비명</th>
                <th class="text-center px-1 py-2 font-medium text-slate-500 w-8">수량</th>
                <th class="text-center px-1 py-2 font-medium text-slate-500 w-6">사진</th>
                <th class="text-left px-1 pr-2 py-2 font-medium text-slate-500">비고</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in store.rows" :key="row.id"
                class="border-b border-slate-100 cursor-pointer transition-colors"
                :class="{
                  'bg-amber-50': pendingChanges.has(row.id) && selectedRow?.id !== row.id,
                  '!bg-blue-50': selectedRow?.id === row.id,
                  'hover:bg-slate-50': selectedRow?.id !== row.id
                }"
                @click="openDetail(row)">
                <td class="px-2 py-1.5 text-slate-500 whitespace-nowrap text-xs">{{ row['지점'] }}</td>
                <td class="px-2 py-1.5 whitespace-nowrap">
                  <span class="px-1 py-0.5 bg-slate-100 rounded text-xs text-slate-500 leading-none">{{ row['카테고리'] }}</span>
                </td>
                <td class="px-2 py-1.5 font-medium text-slate-800 text-xs truncate" :title="row['기기명']">{{ row['기기명'] }}</td>
                <td class="px-2 py-1.5 text-center text-xs" @click.stop>
                  <template v-if="canEdit">
                    <input type="number" :value="row['수량']" min="1"
                      @change="updateQuantity(row, ($event.target as HTMLInputElement).value)"
                      class="w-9 text-center py-0.5 border border-slate-200 rounded text-xs focus:outline-none focus:ring-1 focus:ring-blue-400" />
                  </template>
                  <template v-else>{{ row['수량'] }}</template>
                </td>
                <td class="px-2 py-1.5 text-center" @click.stop>
                  <template v-if="canEdit">
                    <button @click="togglePhoto(row)"
                      class="w-4 h-4 rounded border transition inline-flex items-center justify-center"
                      :class="row['사진'] === '있음'
                        ? 'bg-emerald-500 border-emerald-500 text-white'
                        : 'bg-white border-slate-300 hover:border-blue-400'">
                      <span v-if="row['사진'] === '있음'" class="text-[10px] leading-none">&#x2713;</span>
                    </button>
                  </template>
                  <template v-else>
                    <span class="text-[10px]">{{ row['사진'] === '있음' ? '✅' : '' }}</span>
                  </template>
                </td>
                <td class="px-2 py-1.5" @click.stop>
                  <template v-if="canEdit">
                    <input :value="row['비고']"
                      @change="updateNote(row, ($event.target as HTMLInputElement).value)"
                      class="w-full px-1 py-0.5 border border-slate-200 rounded text-xs focus:outline-none focus:ring-1 focus:ring-blue-400"
                      placeholder="비고" />
                  </template>
                  <template v-else>
                    <span class="text-slate-400 text-xs truncate block" :title="row['비고']">{{ row['비고'] || '-' }}</span>
                  </template>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- ===== 드래그 리사이저 ===== -->
      <div
        class="resizer"
        @mousedown="startResize"
      ></div>

      <!-- ===== 우측: 장비 상세 정보 (상시 표시) ===== -->
      <div class="flex-1 min-w-[320px] overflow-auto">
        <!-- 미선택 상태: 안내 -->
        <div v-if="!selectedRow" class="h-full flex items-center justify-center bg-white border border-slate-200 rounded-lg">
          <div class="text-center">
            <div class="w-12 h-12 rounded-full bg-slate-100 flex items-center justify-center mx-auto mb-3">
              <span class="text-xl text-slate-300">🔍</span>
            </div>
            <p class="text-sm text-slate-400 font-medium">장비를 선택하세요</p>
            <p class="text-xs text-slate-300 mt-1">좌측 목록에서 장비를 클릭하면<br>시술 정보와 이벤트를 확인할 수 있습니다.</p>
          </div>
        </div>

        <!-- 선택됨: 상세 정보 -->
        <div v-else class="h-full flex flex-col bg-white border border-slate-200 rounded-lg overflow-hidden">
          <!-- 헤더 -->
          <div class="px-5 py-4 border-b border-slate-100 bg-slate-50/50 shrink-0">
            <h3 class="text-base font-bold text-slate-800">{{ selectedRow['기기명'] }}</h3>
            <div class="flex items-center gap-2 mt-1 flex-wrap">
              <span class="text-xs text-slate-500">{{ selectedRow['지점'] }}</span>
              <span class="text-slate-300">·</span>
              <span class="px-1.5 py-0.5 bg-slate-200 rounded text-[11px] text-slate-600">{{ selectedRow['카테고리'] }}</span>
              <span v-if="selectedRow['수량'] > 1" class="text-slate-300">·</span>
              <span v-if="selectedRow['수량'] > 1" class="text-xs text-slate-500">{{ selectedRow['수량'] }}대 보유</span>
              <template v-if="selectedRow['비고']">
                <span class="text-slate-300">·</span>
                <span class="text-xs text-slate-400 truncate" :title="selectedRow['비고']">{{ selectedRow['비고'] }}</span>
              </template>
            </div>
          </div>

          <!-- 로딩 -->
          <div v-if="detailLoading" class="flex-1 flex items-center justify-center">
            <LoadingSpinner message="정보를 불러오는 중..." />
          </div>

          <!-- 콘텐츠 -->
          <div v-else-if="detailData" class="flex-1 overflow-auto p-5 space-y-5">

            <!-- ── 시술 정보 ── -->
            <section>
              <h4 class="text-sm font-bold text-slate-700 mb-3 flex items-center gap-1.5">
                <span class="w-5 h-5 bg-blue-100 text-blue-600 rounded flex items-center justify-center text-xs font-bold">T</span>
                시술 정보
              </h4>
              <template v-if="detailData.device_info">
                <div class="bg-slate-50 rounded-lg p-4">
                  <div class="grid grid-cols-[80px_1fr] gap-x-3 gap-y-2">
                    <template v-if="detailData.device_info.category">
                      <span class="text-xs text-slate-400 pt-0.5">분류</span>
                      <span class="text-xs text-slate-700 font-medium">{{ detailData.device_info.category }}</span>
                    </template>
                    <template v-if="detailData.device_info.summary">
                      <span class="text-xs text-slate-400 pt-0.5">설명</span>
                      <span class="text-xs text-slate-700 leading-relaxed">{{ detailData.device_info.summary }}</span>
                    </template>
                    <template v-if="detailData.device_info.target">
                      <span class="text-xs text-slate-400 pt-0.5">부위</span>
                      <span class="text-xs text-slate-700">{{ detailData.device_info.target }}</span>
                    </template>
                    <template v-if="detailData.device_info.mechanism">
                      <span class="text-xs text-slate-400 pt-0.5">작용 원리</span>
                      <p class="text-xs text-slate-600 leading-relaxed bg-white rounded p-2 border border-slate-200">{{ detailData.device_info.mechanism }}</p>
                    </template>
                    <template v-if="detailData.device_info.aliases">
                      <span class="text-xs text-slate-400 pt-0.5">별칭</span>
                      <div class="flex flex-wrap gap-1">
                        <span v-for="alias in detailData.device_info.aliases.split(',')" :key="alias"
                          class="px-1.5 py-0.5 bg-white border border-slate-200 rounded text-xs text-slate-600">{{ alias.trim() }}</span>
                      </div>
                    </template>
                    <template v-if="detailData.device_info.usage_count">
                      <span class="text-xs text-slate-400 pt-0.5">보유</span>
                      <span class="text-xs text-blue-600 font-semibold">{{ detailData.device_info.usage_count }}개 지점</span>
                    </template>
                  </div>
                </div>
              </template>
              <template v-else>
                <div class="bg-slate-50 rounded-lg p-4 text-center">
                  <p class="text-sm text-slate-400">등록된 시술 정보가 없습니다.</p>
                  <p class="text-xs text-slate-300 mt-1">시술정보 &gt; 시술사전에서 추가할 수 있습니다.</p>
                </div>
              </template>
            </section>

            <!-- ── 현재 이벤트 ── -->
            <section>
              <h4 class="text-sm font-bold text-slate-700 mb-3 flex items-center gap-1.5">
                <span class="w-5 h-5 bg-amber-100 text-amber-600 rounded flex items-center justify-center text-xs font-bold">E</span>
                현재 이벤트
                <span v-if="detailData.events.length" class="ml-auto text-[11px] text-slate-400 font-normal">{{ detailData.events.length }}건</span>
              </h4>
              <template v-if="detailData.events.length">
                <div class="space-y-2">
                  <div v-for="(evt, i) in detailData.events" :key="i"
                    class="bg-slate-50 rounded-lg p-3 hover:bg-slate-100 transition">
                    <p class="text-sm font-medium text-slate-700 mb-1">{{ evt.display_name }}</p>
                    <div class="flex items-center gap-4 text-xs">
                      <span v-if="evt.event_price" class="text-blue-600 font-bold text-sm">{{ formatPrice(evt.event_price) }}</span>
                      <span v-if="evt.regular_price" class="line-through text-slate-400">{{ formatPrice(evt.regular_price) }}</span>
                      <span v-if="evt.regular_price && evt.event_price"
                        class="px-1.5 py-0.5 bg-red-50 text-red-500 rounded text-[11px] font-medium">
                        {{ Math.round((1 - evt.event_price / evt.regular_price) * 100) }}% OFF
                      </span>
                      <span v-if="evt.session_count" class="text-slate-500">{{ evt.session_count }}{{ evt.session_unit || '회' }}</span>
                    </div>
                    <p v-if="evt.notes" class="text-xs text-slate-400 mt-1">{{ evt.notes }}</p>
                  </div>
                </div>
              </template>
              <template v-else>
                <div class="bg-slate-50 rounded-lg p-4 text-center">
                  <p class="text-sm text-slate-400">현재 진행 중인 이벤트가 없습니다.</p>
                </div>
              </template>
            </section>

            <!-- ── 관련 논문 ── -->
            <section>
              <h4 class="text-sm font-bold text-slate-700 mb-3 flex items-center gap-1.5">
                <span class="w-5 h-5 bg-emerald-100 text-emerald-600 rounded flex items-center justify-center text-xs font-bold">P</span>
                관련 논문
                <span v-if="detailPapers.length" class="ml-1 text-[11px] text-emerald-600 font-normal">{{ detailPapers.length }}건</span>
              </h4>

              <div v-if="detailPapers.length" class="space-y-2">
                <div v-for="paper in detailPapers" :key="paper.id"
                  class="bg-slate-50 rounded-lg p-3 border border-slate-100 hover:border-blue-200 transition cursor-pointer"
                  @click="$router.push({ path: '/papers', query: { id: paper.id } })">
                  <div class="flex items-center gap-1.5 mb-1">
                    <span class="text-[11px] font-medium px-1.5 py-0.5 rounded"
                      :class="paper.evidence_level >= 4 ? 'bg-emerald-100 text-emerald-700' : paper.evidence_level >= 3 ? 'bg-blue-100 text-blue-700' : 'bg-slate-100 text-slate-500'">
                      {{ '★'.repeat(paper.evidence_level) }}{{ '☆'.repeat(5 - paper.evidence_level) }}
                    </span>
                    <span v-if="paper.study_type" class="text-[11px] text-slate-400">{{ paper.study_type }}</span>
                    <span class="ml-auto text-[11px] text-slate-400">{{ paper.pub_year }}</span>
                  </div>
                  <p class="text-sm font-medium text-slate-700 leading-snug line-clamp-2">
                    {{ paper.title_ko || paper.title }}
                  </p>
                  <p v-if="paper.one_line_summary" class="text-[11px] text-slate-500 mt-1 line-clamp-2 leading-relaxed">
                    {{ paper.one_line_summary }}
                  </p>
                  <p v-if="paper.authors" class="text-[11px] text-slate-400 mt-1 truncate">
                    {{ paper.authors }}{{ paper.journal ? ' / ' + paper.journal : '' }}
                  </p>
                </div>
              </div>

              <div v-else class="bg-slate-50 rounded-lg p-4 text-center">
                <p class="text-sm text-slate-400">등록된 관련 논문이 없습니다.</p>
              </div>
            </section>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.resizer {
  width: 6px;
  cursor: col-resize;
  background: transparent;
  position: relative;
  flex-shrink: 0;
  transition: background 0.15s;
}
.resizer::after {
  content: '';
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 2px;
  height: 32px;
  background: #cbd5e1;
  border-radius: 1px;
}
.resizer:hover {
  background: #e2e8f0;
}
.resizer:hover::after {
  background: #3b82f6;
  height: 48px;
}
</style>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import * as blogApi from '@/api/blog'
import { useColumnResize } from '@/composables/useResizePanel'
import { useAuthorVisibility } from '@/composables/useAuthorVisibility'
import { channelLabel, channelColor, typeColor, statusColor } from '@/utils/blogFormatters'

const props = defineProps<{
  mode: 'uandi' | 'all'
  initialFilters?: Record<string, any>
}>()

const route = useRoute()
const router = useRouter()

const isUandi = computed(() => props.mode !== 'all')

const { canSeeAuthor } = useAuthorVisibility()
const shouldHideAuthor = computed(() => isUandi.value || !canSeeAuthor.value)

// ── 목록 ──
const posts = ref<any[]>([])
const filterOptions = ref<any>(null)
const loading = ref(false)
const totalCount = ref(0)
const totalPages = ref(0)

const page = ref(1)
const perPage = ref(50)
const searchText = ref('')
const filterChannel = ref('')
const filterTypeMain = ref('')
const filterAuthor = ref('')
const filterBranch = ref('')
const filterProjectMonth = ref('')
const filterNeedsReview = ref<number | null>(null)

// 기본 날짜: 올해 1월 1일 ~ 오늘
const now = new Date()
const pad2 = (n: number) => String(n).padStart(2, '0')
const todayStr = `${now.getFullYear()}-${pad2(now.getMonth() + 1)}-${pad2(now.getDate())}`
const yearStartStr = `${now.getFullYear()}-01-01`
const dateFrom = ref(yearStartStr)
const dateTo = ref(todayStr)

// 빠른 기간 선택
type DatePreset = 'year' | 'this_month' | 'last_month' | 'all'
const activeDatePreset = ref<DatePreset>('year')
function setDatePreset(preset: DatePreset) {
  activeDatePreset.value = preset
  const y = now.getFullYear()
  const m = now.getMonth() // 0-indexed
  if (preset === 'year') {
    dateFrom.value = `${y}-01-01`
    dateTo.value = todayStr
  } else if (preset === 'this_month') {
    dateFrom.value = `${y}-${pad2(m + 1)}-01`
    dateTo.value = todayStr
  } else if (preset === 'last_month') {
    const lm = m === 0 ? 12 : m
    const ly = m === 0 ? y - 1 : y
    const lastDay = new Date(ly, lm, 0).getDate()
    dateFrom.value = `${ly}-${pad2(lm)}-01`
    dateTo.value = `${ly}-${pad2(lm)}-${pad2(lastDay)}`
  } else {
    dateFrom.value = ''
    dateTo.value = ''
  }
  applyFilter()
}

// 필터 패널 토글
const showAdvancedFilters = ref(false)
// 인라인 헤더 필터
const showHeaderFilters = ref(false)
const headerFilters = ref<Record<string, string>>({
  blog_channel: '',
  branch_name: '',
  post_type_main: '',
  keyword: '',
  clean_title: '',
  author_main: '',
  published_at: '',
  status_clean: '',
})

// 정렬
const sortColumn = ref('')
const sortDirection = ref<'asc' | 'desc'>('asc')

function toggleSort(colKey: string) {
  if (sortColumn.value === colKey) {
    if (sortDirection.value === 'asc') {
      sortDirection.value = 'desc'
    } else {
      // 정렬 해제
      sortColumn.value = ''
      sortDirection.value = 'asc'
    }
  } else {
    sortColumn.value = colKey
    sortDirection.value = 'asc'
  }
}

function sortIcon(colKey: string) {
  if (sortColumn.value !== colKey) return ''
  return sortDirection.value === 'asc' ? '\u25B2' : '\u25BC'
}

const selectedPost = ref<any>(null)
const detailLoading = ref(false)

// HTML 엔티티 디코딩 (&lt; → <, &gt; → >, &amp; → &)
function decodeHtml(text: string): string {
  if (!text) return text
  return text
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&amp;/g, '&')
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
}

// 컬럼 리사이즈
const columns = ref(
  props.mode !== 'all'
    ? [
        { key: 'blog_channel', label: '채널', width: 64, minWidth: 50 },
        { key: 'branch_name', label: '지점', width: 90, minWidth: 60 },
        { key: 'post_type_main', label: '원고종류', width: 72, minWidth: 50 },
        { key: 'keyword', label: '키워드', width: 200, minWidth: 120 },
        { key: 'clean_title', label: '제목', width: 0, minWidth: 120 },
        { key: 'published_at', label: '발행일', width: 82, minWidth: 60 },
        { key: 'status_clean', label: '상태', width: 68, minWidth: 50 },
        { key: '_actions', label: '', width: 52, minWidth: 52 },
      ]
    : [
        { key: 'blog_channel', label: '채널', width: 64, minWidth: 50 },
        { key: 'branch_name', label: '지점', width: 90, minWidth: 60 },
        { key: 'post_type_main', label: '원고종류', width: 72, minWidth: 50 },
        { key: 'keyword', label: '키워드', width: 200, minWidth: 120 },
        { key: 'clean_title', label: '제목', width: 0, minWidth: 120 },
        ...(canSeeAuthor.value ? [{ key: 'author_main', label: '담당', width: 56, minWidth: 44 }] : []),
        { key: 'published_at', label: '발행일', width: 82, minWidth: 60 },
        { key: 'status_clean', label: '상태', width: 68, minWidth: 50 },
        { key: '_actions', label: '', width: 52, minWidth: 52 },
      ]
)

const { startResize } = useColumnResize(columns)

async function loadPosts() {
  loading.value = true
  try {
    const params: any = { page: page.value, per_page: perPage.value }
    if (isUandi.value) params.branch_filter = 'uandi'
    if (searchText.value) params.search = searchText.value
    if (filterChannel.value) params.channel = filterChannel.value
    if (filterTypeMain.value) params.post_type_main = filterTypeMain.value
    if (filterAuthor.value) params.author = filterAuthor.value
    if (filterBranch.value) params.branch_name = filterBranch.value
    if (filterProjectMonth.value) params.project_month = filterProjectMonth.value
    if (filterNeedsReview.value !== null) params.needs_review = filterNeedsReview.value
    if (dateFrom.value) params.date_from = dateFrom.value
    if (dateTo.value) params.date_to = dateTo.value

    const { data } = await blogApi.getBlogPosts(params)
    posts.value = data.items
    totalCount.value = data.total
    totalPages.value = data.pages
  } catch (e) {
    console.error('블로그 목록 로드 실패:', e)
  } finally {
    loading.value = false
  }
}

async function loadFilterOptions() {
  // 이미 로드된 경우 재요청하지 않음 (세션 중 변하지 않는 데이터)
  if (filterOptions.value) return
  try {
    const params: any = {}
    if (isUandi.value) params.branch_filter = 'uandi'
    const { data } = await blogApi.getBlogFilterOptions(params)
    filterOptions.value = data
  } catch (e) {
    console.error(e)
  }
}

// 요약 스트립 (채널별 카운트)
const summaryStrip = computed(() => {
  if (loading.value) return null
  if (!posts.value.length) return null
  const counts: Record<string, number> = {}
  for (const p of posts.value) {
    const ch = p.blog_channel || 'etc'
    counts[ch] = (counts[ch] || 0) + 1
  }
  const channelMap: Record<string, string> = { br: '브랜드', opt: '최적', cafe: '카페' }
  const parts = Object.entries(counts)
    .sort((a, b) => b[1] - a[1])
    .map(([ch, n]) => `${channelMap[ch] || ch} ${n}`)
  const reviewCount = posts.value.filter((p: any) => p.needs_review).length
  if (reviewCount > 0) parts.push(`검토필요 ${reviewCount}`)
  return { total: totalCount.value, parts }
})

// 인라인 헤더 필터 + 정렬 적용
const filteredPosts = computed(() => {
  let result = posts.value

  // 헤더 필터
  for (const [key, val] of Object.entries(headerFilters.value)) {
    if (!val) continue
    const lower = val.toLowerCase()
    result = result.filter((p: any) => {
      const v = String(p[key] || '').toLowerCase()
      return v.includes(lower)
    })
  }

  // 정렬
  if (sortColumn.value) {
    const col = sortColumn.value
    const dir = sortDirection.value === 'asc' ? 1 : -1
    result = [...result].sort((a: any, b: any) => {
      const va = String(a[col] || '')
      const vb = String(b[col] || '')
      return va.localeCompare(vb, 'ko') * dir
    })
  }

  return result
})

function openUrl(url: string | undefined) {
  if (url) window.open(url, '_blank')
}

function copyTitle(title: string | undefined) {
  if (title) navigator.clipboard.writeText(title)
}

async function openDetail(post: any) {
  if (selectedPost.value?.id === post.id) return
  selectedPost.value = post
  detailLoading.value = true
  try {
    const { data } = await blogApi.getBlogPost(post.id)
    selectedPost.value = data
  } catch (e) {
    console.error(e)
  } finally {
    detailLoading.value = false
  }
}

function applyFilter() {
  page.value = 1
  syncUrlQuery()
  loadPosts()
}

// URL 쿼리 동기화 (주요 필터만, 빈 값 제거)
function syncUrlQuery() {
  const q: Record<string, string> = {}
  const tab = route.query.tab as string
  if (tab) q.tab = tab
  if (searchText.value) q.q = searchText.value
  if (filterChannel.value) q.channel = filterChannel.value
  if (filterBranch.value) q.branch = filterBranch.value
  if (filterAuthor.value) q.author = filterAuthor.value
  if (filterTypeMain.value) q.post_type_main = filterTypeMain.value
  if (dateFrom.value && activeDatePreset.value !== 'year') q.from = dateFrom.value
  if (dateTo.value && activeDatePreset.value !== 'year') q.to = dateTo.value
  if (filterNeedsReview.value === 1) q.needs_review = '1'
  router.replace({ query: q })
}

// URL 쿼리에서 필터 복원
function restoreFromUrlQuery() {
  const q = route.query
  if (q.q) searchText.value = q.q as string
  if (q.channel) filterChannel.value = q.channel as string
  if (q.branch) filterBranch.value = q.branch as string
  if (q.author) filterAuthor.value = q.author as string
  if (q.post_type_main) {
    filterTypeMain.value = q.post_type_main as string
    showAdvancedFilters.value = true
  }
  if (q.from) { dateFrom.value = q.from as string; activeDatePreset.value = 'year' }
  if (q.to) { dateTo.value = q.to as string; activeDatePreset.value = 'year' }
  if (q.needs_review === '1') {
    filterNeedsReview.value = 1
    showAdvancedFilters.value = true
  }
}

function resetFilter() {
  searchText.value = ''
  filterChannel.value = ''
  filterTypeMain.value = ''
  filterAuthor.value = ''
  filterBranch.value = ''
  filterProjectMonth.value = ''
  filterNeedsReview.value = null
  dateFrom.value = yearStartStr
  dateTo.value = todayStr
  activeDatePreset.value = 'year'
  for (const key in headerFilters.value) headerFilters.value[key] = ''
  sortColumn.value = ''
  sortDirection.value = 'asc'
  showHeaderFilters.value = false
  page.value = 1
  loadPosts()
}

// 대시보드 → 목록 진입 시 외부에서 필터 주입 (initialFilters prop)
function applyInitialFilters(filter: Record<string, any>) {
  searchText.value = ''
  filterChannel.value = filter.channel || ''
  filterTypeMain.value = filter.post_type_main || ''
  filterAuthor.value = filter.author || ''
  filterBranch.value = filter.branch_name || filter.project_branch || ''
  filterProjectMonth.value = filter.project_month || ''
  filterNeedsReview.value = filter.needs_review ?? null
  // 날짜: 전체 조회를 위해 비우기 (대시보드에서 올 때)
  dateFrom.value = ''
  dateTo.value = ''
  activeDatePreset.value = 'all'
  for (const key in headerFilters.value) headerFilters.value[key] = ''
  sortColumn.value = ''
  sortDirection.value = 'asc'
  page.value = 1
}

// 페이지 변경 시 목록 재조회
watch(page, () => loadPosts())

// 마운트 시 초기 로드
// - initialFilters가 있으면 대시보드에서 필터 지정 진입 → 필터 적용 후 조회
// - 없으면 기본 날짜 조건으로 조회
onMounted(() => {
  if (props.initialFilters) {
    // 대시보드에서 필터 지정 진입: initialFilters 우선
    applyInitialFilters(props.initialFilters)
    // 고급 필터에 속한 값이 주입된 경우 패널 자동 펼치기
    if (props.initialFilters.post_type_main || props.initialFilters.needs_review) {
      showAdvancedFilters.value = true
    }
  } else {
    // URL 쿼리에서 필터 복원 (북마크/새로고침)
    restoreFromUrlQuery()
  }
  loadPosts()
  loadFilterOptions()
})

</script>

<template>
  <div class="h-full flex flex-col min-h-0">
    <!-- 필터 바 -->
    <div class="bg-white border border-slate-200 rounded-lg px-3 py-2 mb-2 flex-none">
      <!-- 기본 필터 행 -->
      <div class="flex items-center gap-2 overflow-x-auto">
        <input v-model="searchText" @keyup.enter="applyFilter"
               placeholder="제목·키워드·태그 검색"
               class="border border-slate-300 rounded px-2 h-7 text-xs flex-1 min-w-[180px] max-w-[280px] focus:border-blue-400 focus:outline-none shrink-0" />
        <select v-model="filterChannel" @change="applyFilter"
                class="border border-slate-300 rounded px-2 h-7 text-xs shrink-0">
          <option value="">채널</option>
          <option value="br">브랜드</option>
          <option value="opt">최적</option>
          <option value="cafe">카페</option>
        </select>
        <select v-model="filterBranch" @change="applyFilter"
                class="border border-slate-300 rounded px-2 h-7 text-xs max-w-[120px] shrink-0">
          <option value="">지점</option>
          <option v-for="b in filterOptions?.branches" :key="b.branch_name" :value="b.branch_name">
            {{ b.branch_name }} ({{ b.cnt }})
          </option>
        </select>
        <!-- 기간 -->
        <input v-model="dateFrom" type="date" @change="activeDatePreset = 'year'; applyFilter()"
               class="border border-slate-300 rounded px-2 h-7 text-xs w-[128px] shrink-0" />
        <span class="text-slate-400 text-xs shrink-0">~</span>
        <input v-model="dateTo" type="date" @change="activeDatePreset = 'year'; applyFilter()"
               class="border border-slate-300 rounded px-2 h-7 text-xs w-[128px] shrink-0" />
        <div class="flex gap-0.5 shrink-0">
          <button v-for="dp in ([
            { key: 'year' as DatePreset, label: '올해' },
            { key: 'this_month' as DatePreset, label: '이번달' },
            { key: 'last_month' as DatePreset, label: '지난달' },
            { key: 'all' as DatePreset, label: '전체' },
          ])" :key="dp.key"
            @click="setDatePreset(dp.key)"
            class="px-2 h-7 text-xs rounded border transition-colors"
            :class="activeDatePreset === dp.key
              ? 'bg-slate-700 text-white border-slate-700'
              : 'border-slate-300 text-slate-500 hover:bg-slate-100'">
            {{ dp.label }}
          </button>
        </div>
        <button @click="resetFilter" class="text-xs text-slate-400 hover:text-slate-600 shrink-0">초기화</button>
        <!-- 고급 필터 토글 -->
        <button @click="showAdvancedFilters = !showAdvancedFilters"
                class="text-xs px-2 h-7 rounded border transition-colors shrink-0"
                :class="showAdvancedFilters
                  ? 'border-blue-400 text-blue-600 bg-blue-50'
                  : 'border-slate-300 text-slate-500 hover:bg-slate-50'">
          고급 {{ showAdvancedFilters ? '▴' : '▾' }}
        </button>
        <button @click="showHeaderFilters = !showHeaderFilters"
                class="text-xs px-2 h-7 rounded border transition-colors shrink-0"
                :class="showHeaderFilters
                  ? 'border-blue-400 text-blue-600 bg-blue-50'
                  : 'border-slate-300 text-slate-400 hover:text-slate-600'">
          {{ showHeaderFilters ? '컬럼필터 닫기' : '컬럼필터' }}
        </button>
        <span class="ml-auto text-xs text-slate-400 shrink-0 tabular-nums">{{ totalCount.toLocaleString() }}건</span>
      </div>
      <!-- 고급 필터 패널 -->
      <div v-if="showAdvancedFilters" class="flex items-center gap-2 mt-2 pt-2 border-t border-slate-100">
        <select v-model="filterTypeMain" @change="applyFilter"
                class="border border-slate-300 rounded px-2 h-7 text-xs">
          <option value="">원고종류</option>
          <option v-for="t in filterOptions?.post_types_main" :key="t.post_type_main" :value="t.post_type_main">
            {{ t.post_type_main }} ({{ t.cnt }})
          </option>
        </select>
        <label class="flex items-center gap-1 text-xs text-slate-600 cursor-pointer shrink-0">
          <input type="checkbox"
                 :checked="filterNeedsReview === 1"
                 @change="filterNeedsReview = ($event.target as HTMLInputElement).checked ? 1 : null; applyFilter()"
                 class="rounded border-slate-300" />
          검토필요
        </label>
        <select v-if="!shouldHideAuthor" v-model="filterAuthor" @change="applyFilter"
                class="border border-slate-300 rounded px-2 h-7 text-xs">
          <option value="">담당자</option>
          <option v-for="a in filterOptions?.authors" :key="a.author" :value="a.author">
            {{ a.author }} ({{ a.cnt }})
          </option>
        </select>
        <select v-model="filterProjectMonth" @change="applyFilter"
                class="border border-slate-300 rounded px-2 h-7 text-xs">
          <option value="">프로젝트 월</option>
          <option v-for="m in filterOptions?.project_months?.slice(0, 24)" :key="m.project_month" :value="m.project_month">
            {{ m.project_month }} ({{ m.cnt }})
          </option>
        </select>
      </div>
    </div>

    <!-- 요약 스트립 -->
    <div class="flex-none mb-1 min-h-[18px]">
      <p v-if="loading" class="text-xs text-slate-300 tabular-nums">로딩 중...</p>
      <p v-else-if="summaryStrip" class="text-xs text-slate-500 tabular-nums">
        검색결과 <span class="font-medium">{{ summaryStrip.total.toLocaleString() }}건</span>
        <template v-for="(part, i) in summaryStrip.parts" :key="i">
          <span class="text-slate-300 mx-1">·</span>{{ part }}
        </template>
      </p>
    </div>

    <!-- 메인 2컬럼 -->
    <div class="flex-1 flex gap-3 min-h-0">
      <!-- 좌측: 목록 테이블 -->
      <div class="flex-1 bg-white border border-slate-200 rounded-lg overflow-hidden flex flex-col min-w-0">
        <!-- 스크롤 단일 영역 -->
        <div class="flex-1 overflow-auto min-h-0">
          <table class="w-full text-sm table-fixed whitespace-nowrap" style="min-width: 700px;">
            <colgroup>
              <col v-for="col in columns" :key="col.key"
                   :style="col.width ? { width: col.width + 'px' } : {}" />
            </colgroup>
            <thead class="sticky top-0 z-10" style="box-shadow: 0 1px 3px rgba(0,0,0,0.08);">
              <tr class="text-left text-xs text-slate-500 border-b">
                <th v-for="(col, idx) in columns" :key="col.key"
                    @click="toggleSort(col.key)"
                    class="px-2 py-1.5 bg-slate-50 relative select-none cursor-pointer hover:bg-slate-100 transition-colors group">
                  <span>{{ col.label }}</span>
                  <span v-if="sortColumn === col.key"
                        class="ml-0.5 text-blue-500 text-[10px]">{{ sortIcon(col.key) }}</span>
                  <span v-else class="ml-0.5 text-slate-300 text-[10px] opacity-0 group-hover:opacity-100">&#x25B2;</span>
                  <div v-if="col.width > 0"
                       @mousedown.stop="startResize(idx, $event)"
                       class="absolute right-0 top-0 bottom-0 w-1 cursor-col-resize hover:bg-blue-300 transition-colors" />
                </th>
              </tr>
              <!-- 인라인 헤더 필터 (토글) -->
              <tr v-if="showHeaderFilters" class="border-b">
                <th v-for="col in columns" :key="'f-' + col.key" class="px-1 py-1 bg-slate-50">
                  <input v-model="headerFilters[col.key]"
                         :placeholder="col.label"
                         class="w-full border border-slate-200 rounded px-1.5 py-0.5 text-xs text-slate-600
                                focus:border-blue-300 focus:outline-none bg-white/80" />
                </th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="loading">
                <td :colspan="columns.length" class="px-3 py-8 text-center text-slate-400 text-sm">로딩 중...</td>
              </tr>
              <template v-else>
                <tr v-for="post in filteredPosts" :key="post.id"
                    @click="openDetail(post)"
                    class="border-b border-slate-100 hover:bg-blue-50/30 cursor-pointer transition-colors group"
                    :class="{
                      'bg-blue-50': selectedPost?.id === post.id,
                      'bg-amber-50/30': post.needs_review && selectedPost?.id !== post.id,
                    }">
                  <td class="px-2 py-1">
                    <span class="text-xs px-1.5 py-0.5 rounded-full font-medium"
                          :class="channelColor(post.blog_channel)">
                      {{ channelLabel(post.blog_channel) }}
                    </span>
                  </td>
                  <td class="px-2 py-1 text-[11px] text-slate-500 truncate">
                    {{ post.branch_name || '-' }}
                  </td>
                  <td class="px-2 py-1">
                    <span v-if="post.post_type_main"
                          class="text-xs px-1.5 py-0.5 rounded font-medium"
                          :class="typeColor(post.post_type_main)">
                      {{ post.post_type_main }}
                    </span>
                    <span v-else class="text-slate-300 text-[10px]">-</span>
                  </td>
                  <td class="px-2 py-1 text-slate-700 font-medium truncate text-xs">
                    {{ post.keyword || '-' }}
                  </td>
                  <td class="px-2 py-1 truncate text-xs"
                      :class="(post.title && post.title !== '' && !post.title.startsWith('http'))
                        ? 'text-slate-600'
                        : 'text-slate-400 italic'">
                    {{ decodeHtml(post.clean_title) || post.keyword || '-' }}
                  </td>
                  <td v-if="!shouldHideAuthor" class="px-2 py-1 text-slate-500 text-[11px] truncate">{{ post.author_main || '-' }}</td>
                  <td class="px-2 py-1 text-slate-400 text-[11px] tabular-nums">{{ post.published_at || '-' }}</td>
                  <td class="px-2 py-1 text-[11px]" :class="statusColor(post.status_clean)">
                    {{ post.status_clean || '-' }}
                  </td>
                  <td class="px-1 py-1 whitespace-nowrap">
                    <div class="opacity-0 group-hover:opacity-100 flex gap-0.5 transition-opacity">
                      <button @click.stop="openUrl(post.published_url)" title="URL 열기"
                              class="text-[10px] text-slate-400 hover:text-blue-600 px-1 py-0.5">&#x2197;</button>
                      <button @click.stop="copyTitle(post.clean_title || post.keyword)" title="제목 복사"
                              class="text-[10px] text-slate-400 hover:text-blue-600 px-1 py-0.5">&#x29C9;</button>
                    </div>
                  </td>
                </tr>
                <tr v-if="!filteredPosts.length">
                  <td :colspan="columns.length" class="px-3 py-8 text-center text-slate-400 text-sm">데이터가 없습니다</td>
                </tr>
              </template>
            </tbody>
          </table>
        </div>
        <!-- 페이지네이션 -->
        <div class="flex-none flex items-center gap-2 px-3 py-2 border-t bg-slate-50 text-xs text-slate-500">
          <span class="tabular-nums">{{ totalCount.toLocaleString() }}건 중 {{ (page - 1) * perPage + 1 }}~{{ Math.min(page * perPage, totalCount) }}</span>
          <div class="flex gap-1 ml-auto">
            <button @click="page = 1" :disabled="page <= 1"
                    class="px-1.5 py-1 rounded border hover:bg-white disabled:opacity-30" title="첫 페이지">«</button>
            <button @click="page = Math.max(1, page - 1)" :disabled="page <= 1"
                    class="px-2 py-1 rounded border hover:bg-white disabled:opacity-30" title="이전">‹</button>
            <span class="px-2 py-1 tabular-nums">{{ page }} / {{ totalPages }}</span>
            <button @click="page = Math.min(totalPages, page + 1)" :disabled="page >= totalPages"
                    class="px-2 py-1 rounded border hover:bg-white disabled:opacity-30" title="다음">›</button>
            <button @click="page = totalPages" :disabled="page >= totalPages"
                    class="px-1.5 py-1 rounded border hover:bg-white disabled:opacity-30" title="마지막 페이지">»</button>
          </div>
        </div>
      </div>

      <!-- 우측: 상세 패널 (lg 이상에서만 표시) -->
      <div class="hidden lg:flex lg:w-[360px] xl:w-[400px] shrink-0 bg-white border border-slate-200 rounded-lg overflow-auto flex-col">
        <div v-if="!selectedPost" class="flex items-center justify-center flex-1 text-slate-300 text-sm">
          게시글을 선택하세요
        </div>
        <div v-else class="p-2.5 space-y-2">
          <div>
            <div class="flex gap-1.5 mb-2 flex-wrap">
              <span class="text-xs px-1.5 py-0.5 rounded-full font-medium"
                    :class="channelColor(selectedPost.blog_channel)">
                {{ channelLabel(selectedPost.blog_channel) }}
              </span>
              <span v-if="selectedPost.post_type_main"
                    class="text-xs px-1.5 py-0.5 rounded font-medium"
                    :class="typeColor(selectedPost.post_type_main)">
                {{ selectedPost.post_type_main }}
              </span>
              <span v-if="selectedPost.post_type_sub"
                    class="text-xs px-1.5 py-0.5 rounded bg-slate-100 text-slate-500">
                {{ selectedPost.post_type_sub }}
              </span>
              <span v-if="selectedPost.needs_review"
                    class="text-xs px-1.5 py-0.5 rounded bg-amber-100 text-amber-700 font-medium">
                검토필요
              </span>
            </div>
            <h3 class="font-bold text-sm leading-snug"
                :class="selectedPost.title && !selectedPost.title.startsWith('http')
                  ? 'text-slate-800' : 'text-slate-500'">
              {{ decodeHtml(selectedPost.clean_title) || selectedPost.keyword || '(제목 없음)' }}
              <span v-if="!selectedPost.title || selectedPost.title.startsWith('http')"
                    class="text-[10px] text-slate-400 font-normal ml-1">(키워드)</span>
            </h3>
          </div>

          <div class="grid text-xs gap-x-3 gap-y-1" style="grid-template-columns: auto 1fr;">
            <span class="text-xs text-slate-500 whitespace-nowrap">키워드</span>
            <span class="text-xs text-slate-800 font-medium">{{ selectedPost.keyword || '-' }}</span>

            <template v-if="selectedPost.tags">
              <span class="text-xs text-slate-500 whitespace-nowrap">태그</span>
              <span class="text-xs text-slate-800">{{ selectedPost.tags }}</span>
            </template>

            <template v-if="!shouldHideAuthor && (selectedPost.author_main || selectedPost.author_sub)">
              <span class="text-xs text-slate-500 whitespace-nowrap">담당자</span>
              <span class="text-xs text-slate-800">
                {{ selectedPost.author_main || '-' }}
                <span v-if="selectedPost.author_sub" class="text-slate-500"> · {{ selectedPost.author_sub }}</span>
              </span>
            </template>

            <template v-if="selectedPost.branch_name">
              <span class="text-xs text-slate-500 whitespace-nowrap">지점</span>
              <span class="text-xs text-slate-800">
                {{ selectedPost.branch_name }}
                <span v-if="selectedPost.slot_number" class="text-slate-500">#{{ selectedPost.slot_number }}</span>
              </span>
            </template>

            <template v-if="selectedPost.published_at">
              <span class="text-xs text-slate-500 whitespace-nowrap">발행일</span>
              <span class="text-xs text-slate-800 tabular-nums">{{ selectedPost.published_at }}</span>
            </template>

            <template v-if="selectedPost.deadline_at">
              <span class="text-xs text-slate-500 whitespace-nowrap">마감일</span>
              <span class="text-xs text-slate-800 tabular-nums">{{ selectedPost.deadline_at }}</span>
            </template>

            <template v-if="selectedPost.status_clean">
              <span class="text-xs text-slate-500 whitespace-nowrap">상태</span>
              <span class="text-xs" :class="statusColor(selectedPost.status_clean)">{{ selectedPost.status_clean }}</span>
            </template>

            <template v-if="selectedPost.blog_id">
              <span class="text-xs text-slate-500 whitespace-nowrap">계정</span>
              <span class="text-xs text-slate-800 font-mono">{{ selectedPost.blog_id }}</span>
            </template>

            <template v-if="selectedPost.project_month">
              <span class="text-xs text-slate-500 whitespace-nowrap">프로젝트</span>
              <span class="text-xs text-slate-800">
                {{ selectedPost.project_month }}
                <span v-if="selectedPost.project_branch" class="text-slate-500"> · {{ selectedPost.project_branch }}</span>
              </span>
            </template>

            <template v-if="selectedPost.exposure_rank">
              <span class="text-xs text-slate-500 whitespace-nowrap">노출순위</span>
              <span class="text-xs text-slate-800 tabular-nums">{{ selectedPost.exposure_rank }}</span>
            </template>
          </div>

          <div v-if="selectedPost.published_url" class="pt-2 border-t">
            <a :href="selectedPost.published_url" target="_blank"
               class="text-xs text-blue-600 hover:underline break-all">
              {{ selectedPost.published_url }}
            </a>
          </div>

          <div v-if="selectedPost.linked_papers?.length" class="pt-2 border-t">
            <p class="text-[10px] text-slate-400 mb-1.5">연결된 논문</p>
            <div v-for="lp in selectedPost.linked_papers" :key="lp.paper_id"
                 class="p-2 bg-emerald-50 rounded text-xs mb-1">
              <span class="text-emerald-700">{{ lp.title_ko }}</span>
              <span class="text-emerald-500 ml-1">{{ lp.evidence_level }}/5</span>
            </div>
          </div>

          <details v-if="selectedPost.needs_review" class="pt-2 border-t">
            <summary class="text-xs text-amber-500 cursor-pointer">원본 데이터 보기</summary>
            <div class="mt-2 text-[11px] text-slate-500 space-y-1 bg-slate-50 p-2 rounded">
              <div><span class="text-slate-400">원본 제목:</span> {{ selectedPost.title || '(없음)' }}</div>
              <div><span class="text-slate-400">원본 종류:</span> {{ selectedPost.post_type || '(없음)' }}</div>
              <div><span class="text-slate-400">원본 상태:</span> {{ selectedPost.status || '(없음)' }}</div>
              <div><span class="text-slate-400">원본 프로젝트:</span> {{ selectedPost.project || '(없음)' }}</div>
            </div>
          </details>

          <div v-if="selectedPost.note" class="pt-2 border-t">
            <p class="text-[10px] text-slate-400 mb-1">비고</p>
            <p class="text-xs text-slate-600">{{ selectedPost.note }}</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

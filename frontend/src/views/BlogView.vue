<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import * as blogApi from '@/api/blog'

// ── 탭 ──
const activeTab = ref<'dashboard' | 'list' | 'accounts'>('dashboard')

// ── 대시보드 ──
const dashboard = ref<any>(null)
const dashLoading = ref(false)

async function loadDashboard() {
  dashLoading.value = true
  try {
    const { data } = await blogApi.getBlogDashboard()
    dashboard.value = data
  } catch (e) {
    console.error('대시보드 로드 실패:', e)
  } finally {
    dashLoading.value = false
  }
}

// ── 목록 ──
const posts = ref<any[]>([])
const filterOptions = ref<any>(null)
const stats = ref<any>(null)
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
const dateFrom = ref('')
const dateTo = ref('')

const selectedPost = ref<any>(null)
const detailLoading = ref(false)

async function loadPosts() {
  loading.value = true
  try {
    const params: any = { page: page.value, per_page: perPage.value }
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
  try {
    const { data } = await blogApi.getBlogFilterOptions()
    filterOptions.value = data
  } catch (e) {
    console.error(e)
  }
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
  loadPosts()
}

function resetFilter() {
  searchText.value = ''
  filterChannel.value = ''
  filterTypeMain.value = ''
  filterAuthor.value = ''
  filterBranch.value = ''
  filterProjectMonth.value = ''
  filterNeedsReview.value = null
  dateFrom.value = ''
  dateTo.value = ''
  page.value = 1
  loadPosts()
}

// ── 계정관리 ──
const accounts = ref<any[]>([])
const accountsLoading = ref(false)
const accountSearch = ref('')
const accountChannelFilter = ref('')
const editingAccount = ref<string | null>(null)
const editForm = ref({ account_name: '', account_group: '' })

async function loadAccounts() {
  accountsLoading.value = true
  try {
    const params: any = {}
    if (accountChannelFilter.value) params.channel = accountChannelFilter.value
    if (accountSearch.value) params.search = accountSearch.value
    const { data } = await blogApi.getBlogAccounts(params)
    accounts.value = data.items
  } catch (e) {
    console.error(e)
  } finally {
    accountsLoading.value = false
  }
}

function startEdit(acc: any) {
  editingAccount.value = acc.blog_id
  editForm.value = {
    account_name: acc.account_name || '',
    account_group: acc.account_group || '',
  }
}

async function saveAccount(blogId: string) {
  try {
    await blogApi.updateBlogAccount(blogId, editForm.value)
    editingAccount.value = null
    loadAccounts()
  } catch (e) {
    console.error(e)
  }
}

function cancelEdit() {
  editingAccount.value = null
}

// ── 유틸 ──
function channelLabel(ch: string) {
  return ch === 'br' ? '브랜드' : ch === 'opt' ? '최적' : ch || '-'
}
function channelColor(ch: string) {
  return ch === 'br' ? 'bg-blue-100 text-blue-700' : ch === 'opt' ? 'bg-purple-100 text-purple-700' : 'bg-slate-100 text-slate-500'
}
function typeColor(t: string) {
  if (t === '논문글') return 'bg-emerald-100 text-emerald-700'
  if (t === '정보성글') return 'bg-sky-100 text-sky-700'
  if (t === '홍보성글') return 'bg-amber-100 text-amber-700'
  if (t === '임상글') return 'bg-rose-100 text-rose-700'
  if (t === '키컨텐츠') return 'bg-indigo-100 text-indigo-700'
  if (t === '최적') return 'bg-purple-100 text-purple-700'
  if (t === '소개글') return 'bg-teal-100 text-teal-700'
  return 'bg-slate-100 text-slate-600'
}
function statusColor(s: string) {
  if (s === '보고 완료') return 'text-green-600'
  if (s === '발행 완료') return 'text-blue-600'
  if (s === '예약 발행') return 'text-amber-600'
  if (s === '진행 취소') return 'text-red-500'
  if (s === '밀림') return 'text-slate-400'
  return 'text-slate-500'
}

const lastSyncInfo = computed(() => {
  return filterOptions.value?.last_sync || null
})

// ── 대시보드 차트 ──
const maxBranchCount = computed(() => {
  if (!dashboard.value?.by_branch?.length) return 1
  return Math.max(...dashboard.value.by_branch.map((b: any) => b.cnt))
})

const maxMonthlyCount = computed(() => {
  if (!dashboard.value?.monthly?.length) return 1
  return Math.max(...dashboard.value.monthly.map((m: any) => m.cnt))
})

const sortedMonthly = computed(() => {
  if (!dashboard.value?.monthly) return []
  return [...dashboard.value.monthly].sort((a: any, b: any) => a.month.localeCompare(b.month))
})

// ── 초기 로드 ──
watch(page, () => loadPosts())

watch(activeTab, (tab) => {
  if (tab === 'dashboard' && !dashboard.value) loadDashboard()
  if (tab === 'list' && !posts.value.length) { loadPosts(); loadFilterOptions() }
  if (tab === 'accounts' && !accounts.value.length) loadAccounts()
})

onMounted(() => {
  loadDashboard()
})
</script>

<template>
  <div class="p-5 h-full flex flex-col">
    <!-- 헤더 -->
    <div class="flex items-center justify-between mb-4">
      <div>
        <h2 class="text-xl font-bold text-slate-800">블로그 관리</h2>
        <p class="text-xs text-slate-400 mt-0.5" v-if="lastSyncInfo">
          마지막 데이터: {{ lastSyncInfo.csv_modified_at }}
        </p>
      </div>
    </div>

    <!-- 탭 바 -->
    <div class="flex gap-1 mb-4 border-b border-slate-200">
      <button v-for="tab in ([
        { key: 'dashboard', label: '대시보드' },
        { key: 'list', label: '목록' },
        { key: 'accounts', label: '계정관리' },
      ] as const)" :key="tab.key"
        @click="activeTab = tab.key"
        class="px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px"
        :class="activeTab === tab.key
          ? 'border-blue-500 text-blue-600'
          : 'border-transparent text-slate-500 hover:text-slate-700'">
        {{ tab.label }}
      </button>
    </div>

    <!-- ═══════ 대시보드 탭 ═══════ -->
    <div v-if="activeTab === 'dashboard'" class="flex-1 overflow-auto space-y-4">
      <div v-if="dashLoading" class="text-center py-12 text-slate-400">로딩 중...</div>
      <template v-else-if="dashboard">
        <!-- 요약 카드 -->
        <div class="grid grid-cols-4 gap-3">
          <div class="bg-white border border-slate-200 rounded-lg p-4">
            <p class="text-xs text-slate-400">전체 게시글</p>
            <p class="text-2xl font-bold text-slate-800 mt-1">{{ dashboard.total?.toLocaleString() }}</p>
          </div>
          <div class="bg-white border border-blue-200 rounded-lg p-4">
            <p class="text-xs text-blue-500">브랜드</p>
            <p class="text-2xl font-bold text-blue-700 mt-1">{{ (dashboard.by_channel?.br || 0).toLocaleString() }}</p>
          </div>
          <div class="bg-white border border-purple-200 rounded-lg p-4">
            <p class="text-xs text-purple-500">최적</p>
            <p class="text-2xl font-bold text-purple-700 mt-1">{{ (dashboard.by_channel?.opt || 0).toLocaleString() }}</p>
          </div>
          <div class="bg-white border border-amber-200 rounded-lg p-4">
            <p class="text-xs text-amber-500">검토 필요</p>
            <p class="text-2xl font-bold text-amber-700 mt-1">{{ (dashboard.review_count || 0).toLocaleString() }}</p>
          </div>
        </div>

        <div class="grid grid-cols-2 gap-4">
          <!-- 지점별 게시글 수 -->
          <div class="bg-white border border-slate-200 rounded-lg p-4">
            <h3 class="text-sm font-semibold text-slate-700 mb-3">지점별 게시글 수</h3>
            <div class="space-y-1.5">
              <div v-for="b in dashboard.by_branch" :key="b.branch_name" class="flex items-center gap-2 text-xs">
                <span class="w-20 text-right text-slate-600 truncate shrink-0">{{ b.branch_name }}</span>
                <div class="flex-1 bg-slate-100 rounded-full h-4 overflow-hidden">
                  <div class="bg-blue-400 h-full rounded-full transition-all"
                       :style="{ width: (b.cnt / maxBranchCount * 100) + '%' }"></div>
                </div>
                <span class="w-10 text-right text-slate-500 shrink-0">{{ b.cnt }}</span>
              </div>
            </div>
          </div>

          <!-- 월별 발행 추이 -->
          <div class="bg-white border border-slate-200 rounded-lg p-4">
            <h3 class="text-sm font-semibold text-slate-700 mb-3">월별 발행 추이</h3>
            <div class="flex items-end gap-1 h-40">
              <div v-for="m in sortedMonthly" :key="m.month"
                   class="flex-1 flex flex-col items-center justify-end">
                <span class="text-[9px] text-slate-500 mb-1">{{ m.cnt }}</span>
                <div class="w-full bg-purple-400 rounded-t transition-all min-h-[2px]"
                     :style="{ height: (m.cnt / maxMonthlyCount * 120) + 'px' }"></div>
                <span class="text-[9px] text-slate-400 mt-1 rotate-[-45deg] origin-center whitespace-nowrap">
                  {{ m.month.slice(2) }}
                </span>
              </div>
            </div>
          </div>

          <!-- 종류별 분포 -->
          <div class="bg-white border border-slate-200 rounded-lg p-4">
            <h3 class="text-sm font-semibold text-slate-700 mb-3">종류별 분포</h3>
            <div class="space-y-2">
              <div v-for="t in dashboard.by_type" :key="t.post_type_main" class="flex items-center gap-2">
                <span class="text-[10px] px-1.5 py-0.5 rounded font-medium shrink-0"
                      :class="typeColor(t.post_type_main)">
                  {{ t.post_type_main }}
                </span>
                <div class="flex-1 bg-slate-100 rounded-full h-3 overflow-hidden">
                  <div class="bg-emerald-300 h-full rounded-full"
                       :style="{ width: (t.cnt / dashboard.total * 100) + '%' }"></div>
                </div>
                <span class="text-xs text-slate-500 w-14 text-right">{{ t.cnt.toLocaleString() }}</span>
              </div>
            </div>
          </div>

          <!-- 최근 발행 -->
          <div class="bg-white border border-slate-200 rounded-lg p-4">
            <h3 class="text-sm font-semibold text-slate-700 mb-3">최근 발행</h3>
            <div class="space-y-1.5">
              <div v-for="r in dashboard.recent" :key="r.id"
                   class="flex items-center gap-2 text-xs border-b border-slate-50 pb-1.5">
                <span class="text-[10px] px-1 py-0.5 rounded-full shrink-0"
                      :class="channelColor(r.blog_channel)">
                  {{ channelLabel(r.blog_channel) }}
                </span>
                <span class="text-slate-600 truncate flex-1">{{ r.clean_title || r.keyword || '-' }}</span>
                <span class="text-slate-400 shrink-0">{{ r.published_at?.slice(5) }}</span>
              </div>
            </div>
          </div>
        </div>
      </template>
    </div>

    <!-- ═══════ 목록 탭 ═══════ -->
    <template v-if="activeTab === 'list'">
      <!-- 필터 바 -->
      <div class="bg-white border border-slate-200 rounded-lg p-3 mb-3 flex flex-wrap items-center gap-2">
        <input v-model="searchText" @keyup.enter="applyFilter"
               placeholder="제목·키워드·태그 검색"
               class="border border-slate-300 rounded px-2 py-1 text-sm w-48 focus:border-blue-400 focus:outline-none" />
        <select v-model="filterChannel" @change="applyFilter" class="border border-slate-300 rounded px-2 py-1 text-sm">
          <option value="">전체 채널</option>
          <option value="br">브랜드</option>
          <option value="opt">최적</option>
        </select>
        <select v-model="filterTypeMain" @change="applyFilter" class="border border-slate-300 rounded px-2 py-1 text-sm">
          <option value="">전체 종류</option>
          <option v-for="t in filterOptions?.post_types_main" :key="t.post_type_main" :value="t.post_type_main">
            {{ t.post_type_main }} ({{ t.cnt }})
          </option>
        </select>
        <select v-model="filterBranch" @change="applyFilter" class="border border-slate-300 rounded px-2 py-1 text-sm">
          <option value="">전체 지점</option>
          <option v-for="b in filterOptions?.branches?.slice(0, 30)" :key="b.branch_name" :value="b.branch_name">
            {{ b.branch_name }} ({{ b.cnt }})
          </option>
        </select>
        <select v-model="filterProjectMonth" @change="applyFilter" class="border border-slate-300 rounded px-2 py-1 text-sm">
          <option value="">전체 월</option>
          <option v-for="m in filterOptions?.project_months?.slice(0, 24)" :key="m.project_month" :value="m.project_month">
            {{ m.project_month }} ({{ m.cnt }})
          </option>
        </select>
        <select v-model="filterAuthor" @change="applyFilter" class="border border-slate-300 rounded px-2 py-1 text-sm">
          <option value="">전체 작성자</option>
          <option v-for="a in filterOptions?.authors" :key="a.author" :value="a.author">
            {{ a.author }} ({{ a.cnt }})
          </option>
        </select>
        <input v-model="dateFrom" type="date" @change="applyFilter"
               class="border border-slate-300 rounded px-2 py-1 text-sm" />
        <span class="text-slate-400 text-xs">~</span>
        <input v-model="dateTo" type="date" @change="applyFilter"
               class="border border-slate-300 rounded px-2 py-1 text-sm" />
        <label class="flex items-center gap-1 text-xs text-amber-600 cursor-pointer">
          <input type="checkbox"
                 :checked="filterNeedsReview === 1"
                 @change="filterNeedsReview = ($event.target as HTMLInputElement).checked ? 1 : null; applyFilter()"
                 class="rounded border-slate-300" />
          검토필요
        </label>
        <button @click="resetFilter" class="text-xs text-slate-400 hover:text-slate-600 ml-1">초기화</button>
        <span class="ml-auto text-xs text-slate-400">{{ totalCount.toLocaleString() }}건</span>
      </div>

      <!-- 메인 2컬럼 -->
      <div class="flex-1 flex gap-3 min-h-0">
        <!-- 좌측: 목록 테이블 -->
        <div class="flex-1 bg-white border border-slate-200 rounded-lg overflow-hidden flex flex-col">
          <div class="overflow-auto flex-1">
            <table class="w-full text-sm">
              <thead class="bg-slate-50 sticky top-0">
                <tr class="text-left text-xs text-slate-500 border-b">
                  <th class="px-2 py-2 w-14">채널</th>
                  <th class="px-2 py-2 w-16">지점</th>
                  <th class="px-2 py-2 w-16">종류</th>
                  <th class="px-2 py-2 w-28">키워드</th>
                  <th class="px-2 py-2">제목</th>
                  <th class="px-2 py-2 w-14">담당</th>
                  <th class="px-2 py-2 w-20">발행일</th>
                  <th class="px-2 py-2 w-16">상태</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="post in posts" :key="post.id"
                    @click="openDetail(post)"
                    class="border-b border-slate-100 hover:bg-blue-50/40 cursor-pointer transition-colors"
                    :class="{
                      'bg-blue-50': selectedPost?.id === post.id,
                      'bg-amber-50/30': post.needs_review && selectedPost?.id !== post.id,
                    }">
                  <td class="px-2 py-1.5">
                    <span class="text-[10px] px-1.5 py-0.5 rounded-full font-medium"
                          :class="channelColor(post.blog_channel)">
                      {{ channelLabel(post.blog_channel) }}
                    </span>
                  </td>
                  <td class="px-2 py-1.5 text-[11px] text-slate-500 truncate max-w-[64px]">
                    {{ post.branch_name || '-' }}
                  </td>
                  <td class="px-2 py-1.5">
                    <span v-if="post.post_type_main"
                          class="text-[10px] px-1.5 py-0.5 rounded font-medium"
                          :class="typeColor(post.post_type_main)">
                      {{ post.post_type_main }}
                    </span>
                    <span v-else class="text-slate-300 text-[10px]">-</span>
                  </td>
                  <td class="px-2 py-1.5 text-slate-700 font-medium truncate max-w-[112px] text-xs">
                    {{ post.keyword || '-' }}
                  </td>
                  <td class="px-2 py-1.5 text-slate-600 truncate max-w-[250px] text-xs">
                    {{ post.clean_title || post.title || '-' }}
                  </td>
                  <td class="px-2 py-1.5 text-slate-500 text-[11px]">{{ post.author_main || '-' }}</td>
                  <td class="px-2 py-1.5 text-slate-400 text-[11px]">{{ post.published_at || '-' }}</td>
                  <td class="px-2 py-1.5 text-[11px]" :class="statusColor(post.status_clean)">
                    {{ post.status_clean || '-' }}
                  </td>
                </tr>
                <tr v-if="!posts.length && !loading">
                  <td colspan="8" class="px-3 py-8 text-center text-slate-400 text-sm">데이터가 없습니다</td>
                </tr>
              </tbody>
            </table>
          </div>
          <!-- 페이지네이션 -->
          <div class="flex items-center justify-between px-3 py-2 border-t bg-slate-50 text-xs text-slate-500">
            <span>{{ totalCount.toLocaleString() }}건 중 {{ (page - 1) * perPage + 1 }}~{{ Math.min(page * perPage, totalCount) }}</span>
            <div class="flex gap-1">
              <button @click="page = Math.max(1, page - 1)" :disabled="page <= 1"
                      class="px-2 py-1 rounded border hover:bg-white disabled:opacity-30">이전</button>
              <span class="px-2 py-1">{{ page }} / {{ totalPages }}</span>
              <button @click="page = Math.min(totalPages, page + 1)" :disabled="page >= totalPages"
                      class="px-2 py-1 rounded border hover:bg-white disabled:opacity-30">다음</button>
            </div>
          </div>
        </div>

        <!-- 우측: 상세 패널 -->
        <div class="w-[360px] shrink-0 bg-white border border-slate-200 rounded-lg overflow-auto">
          <div v-if="!selectedPost" class="flex items-center justify-center h-full text-slate-300 text-sm">
            게시글을 선택하세요
          </div>
          <div v-else class="p-4 space-y-3">
            <!-- 헤더 -->
            <div>
              <div class="flex gap-1.5 mb-2 flex-wrap">
                <span class="text-[10px] px-1.5 py-0.5 rounded-full font-medium"
                      :class="channelColor(selectedPost.blog_channel)">
                  {{ channelLabel(selectedPost.blog_channel) }}
                </span>
                <span v-if="selectedPost.post_type_main"
                      class="text-[10px] px-1.5 py-0.5 rounded font-medium"
                      :class="typeColor(selectedPost.post_type_main)">
                  {{ selectedPost.post_type_main }}
                </span>
                <span v-if="selectedPost.post_type_sub"
                      class="text-[10px] px-1.5 py-0.5 rounded bg-slate-100 text-slate-500">
                  {{ selectedPost.post_type_sub }}
                </span>
                <span v-if="selectedPost.needs_review"
                      class="text-[10px] px-1.5 py-0.5 rounded bg-amber-100 text-amber-700 font-medium">
                  검토필요
                </span>
              </div>
              <h3 class="font-bold text-slate-800 text-sm leading-snug">
                {{ selectedPost.clean_title || selectedPost.title || '(제목 없음)' }}
              </h3>
            </div>

            <!-- 정보 -->
            <div class="space-y-1.5 text-xs">
              <div class="flex justify-between">
                <span class="text-slate-400">키워드</span>
                <span class="text-slate-700 font-medium">{{ selectedPost.keyword || '-' }}</span>
              </div>
              <div class="flex justify-between" v-if="selectedPost.tags">
                <span class="text-slate-400">태그</span>
                <span class="text-slate-700">{{ selectedPost.tags }}</span>
              </div>
              <div class="flex justify-between">
                <span class="text-slate-400">담당자</span>
                <span class="text-slate-700">
                  {{ selectedPost.author_main || '-' }}
                  <span v-if="selectedPost.author_sub" class="text-slate-400"> · {{ selectedPost.author_sub }}</span>
                </span>
              </div>
              <div class="flex justify-between" v-if="selectedPost.branch_name">
                <span class="text-slate-400">지점</span>
                <span class="text-slate-700">{{ selectedPost.branch_name }}
                  <span v-if="selectedPost.slot_number" class="text-slate-400">#{{ selectedPost.slot_number }}</span>
                </span>
              </div>
              <div class="flex justify-between">
                <span class="text-slate-400">발행일</span>
                <span class="text-slate-700">{{ selectedPost.published_at || '-' }}</span>
              </div>
              <div class="flex justify-between" v-if="selectedPost.deadline_at">
                <span class="text-slate-400">마감일</span>
                <span class="text-slate-700">{{ selectedPost.deadline_at }}</span>
              </div>
              <div class="flex justify-between">
                <span class="text-slate-400">상태</span>
                <span :class="statusColor(selectedPost.status_clean)">{{ selectedPost.status_clean || '-' }}</span>
              </div>
              <div class="flex justify-between" v-if="selectedPost.blog_id">
                <span class="text-slate-400">계정</span>
                <span class="text-slate-700 font-mono text-[11px]">{{ selectedPost.blog_id }}</span>
              </div>
              <div class="flex justify-between" v-if="selectedPost.project_month">
                <span class="text-slate-400">프로젝트</span>
                <span class="text-slate-700">{{ selectedPost.project_month }}
                  <span v-if="selectedPost.project_branch" class="text-slate-400"> · {{ selectedPost.project_branch }}</span>
                </span>
              </div>
              <div class="flex justify-between" v-if="selectedPost.exposure_rank">
                <span class="text-slate-400">노출순위</span>
                <span class="text-slate-700">{{ selectedPost.exposure_rank }}</span>
              </div>
            </div>

            <!-- 링크 -->
            <div v-if="selectedPost.published_url" class="pt-2 border-t">
              <a :href="selectedPost.published_url" target="_blank"
                 class="text-xs text-blue-600 hover:underline break-all">
                {{ selectedPost.published_url }}
              </a>
            </div>

            <!-- 연결된 논문 -->
            <div v-if="selectedPost.linked_papers?.length" class="pt-2 border-t">
              <p class="text-[10px] text-slate-400 mb-1.5">연결된 논문</p>
              <div v-for="lp in selectedPost.linked_papers" :key="lp.paper_id"
                   class="p-2 bg-emerald-50 rounded text-xs mb-1">
                <span class="text-emerald-700">{{ lp.title_ko }}</span>
                <span class="text-emerald-500 ml-1">{{ lp.evidence_level }}/5</span>
              </div>
            </div>

            <!-- 원본 데이터 (접기) -->
            <details v-if="selectedPost.needs_review" class="pt-2 border-t">
              <summary class="text-[10px] text-amber-500 cursor-pointer">원본 데이터 보기</summary>
              <div class="mt-2 text-[11px] text-slate-500 space-y-1 bg-slate-50 p-2 rounded">
                <div><span class="text-slate-400">원본 제목:</span> {{ selectedPost.title || '(없음)' }}</div>
                <div><span class="text-slate-400">원본 종류:</span> {{ selectedPost.post_type || '(없음)' }}</div>
                <div><span class="text-slate-400">원본 상태:</span> {{ selectedPost.status || '(없음)' }}</div>
                <div><span class="text-slate-400">원본 프로젝트:</span> {{ selectedPost.project || '(없음)' }}</div>
              </div>
            </details>

            <!-- 비고 -->
            <div v-if="selectedPost.note" class="pt-2 border-t">
              <p class="text-[10px] text-slate-400 mb-1">비고</p>
              <p class="text-xs text-slate-600">{{ selectedPost.note }}</p>
            </div>
          </div>
        </div>
      </div>
    </template>

    <!-- ═══════ 계정관리 탭 ═══════ -->
    <div v-if="activeTab === 'accounts'" class="flex-1 flex flex-col min-h-0">
      <!-- 필터 -->
      <div class="bg-white border border-slate-200 rounded-lg p-3 mb-3 flex items-center gap-2">
        <input v-model="accountSearch" @keyup.enter="loadAccounts"
               placeholder="계정 ID / 별명 검색"
               class="border border-slate-300 rounded px-2 py-1 text-sm w-56 focus:border-blue-400 focus:outline-none" />
        <select v-model="accountChannelFilter" @change="loadAccounts" class="border border-slate-300 rounded px-2 py-1 text-sm">
          <option value="">전체 채널</option>
          <option value="br">브랜드</option>
          <option value="opt">최적</option>
        </select>
        <span class="ml-auto text-xs text-slate-400">{{ accounts.length }}개 계정</span>
      </div>

      <!-- 테이블 -->
      <div class="flex-1 bg-white border border-slate-200 rounded-lg overflow-auto">
        <table class="w-full text-sm">
          <thead class="bg-slate-50 sticky top-0">
            <tr class="text-left text-xs text-slate-500 border-b">
              <th class="px-3 py-2 w-14">채널</th>
              <th class="px-3 py-2 w-40">블로그 ID</th>
              <th class="px-3 py-2 w-36">별명</th>
              <th class="px-3 py-2 w-36">그룹</th>
              <th class="px-3 py-2 w-20 text-right">게시글</th>
              <th class="px-3 py-2 w-24">마지막 발행</th>
              <th class="px-3 py-2 w-20"></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="acc in accounts" :key="acc.blog_id"
                class="border-b border-slate-100 hover:bg-slate-50/50">
              <td class="px-3 py-2">
                <span class="text-[10px] px-1.5 py-0.5 rounded-full font-medium"
                      :class="channelColor(acc.channel)">
                  {{ channelLabel(acc.channel) }}
                </span>
              </td>
              <td class="px-3 py-2 font-mono text-[11px] text-slate-600">{{ acc.blog_id }}</td>
              <td class="px-3 py-2">
                <template v-if="editingAccount === acc.blog_id">
                  <input v-model="editForm.account_name"
                         class="border border-blue-300 rounded px-1.5 py-0.5 text-xs w-full"
                         placeholder="별명 입력" />
                </template>
                <template v-else>
                  <span class="text-xs text-slate-700">{{ acc.account_name || '-' }}</span>
                </template>
              </td>
              <td class="px-3 py-2">
                <template v-if="editingAccount === acc.blog_id">
                  <input v-model="editForm.account_group"
                         class="border border-blue-300 rounded px-1.5 py-0.5 text-xs w-full"
                         placeholder="그룹 입력" />
                </template>
                <template v-else>
                  <span class="text-xs text-slate-500">{{ acc.account_group || '-' }}</span>
                </template>
              </td>
              <td class="px-3 py-2 text-right text-xs text-slate-600 font-medium">{{ acc.post_count }}</td>
              <td class="px-3 py-2 text-xs text-slate-400">{{ acc.last_published || '-' }}</td>
              <td class="px-3 py-2 text-right">
                <template v-if="editingAccount === acc.blog_id">
                  <button @click="saveAccount(acc.blog_id)" class="text-[10px] text-blue-600 hover:underline mr-1">저장</button>
                  <button @click="cancelEdit" class="text-[10px] text-slate-400 hover:underline">취소</button>
                </template>
                <template v-else>
                  <button @click="startEdit(acc)" class="text-[10px] text-slate-400 hover:text-blue-600">편집</button>
                </template>
              </td>
            </tr>
            <tr v-if="!accounts.length && !accountsLoading">
              <td colspan="7" class="px-3 py-8 text-center text-slate-400 text-sm">계정이 없습니다</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

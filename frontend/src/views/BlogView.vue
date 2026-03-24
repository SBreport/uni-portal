<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import * as blogApi from '@/api/blog'

// 데이터
const posts = ref<any[]>([])
const filterOptions = ref<any>(null)
const stats = ref<any>(null)
const loading = ref(false)
const totalCount = ref(0)
const totalPages = ref(0)

// 필터
const page = ref(1)
const perPage = ref(50)
const searchText = ref('')
const filterChannel = ref('')
const filterType = ref('')
const filterAuthor = ref('')
const filterBlogId = ref('')
const dateFrom = ref('')
const dateTo = ref('')

// 상세
const selectedPost = ref<any>(null)
const detailLoading = ref(false)

// CSV 업로드
const showUploadModal = ref(false)
const uploadFile = ref<File | null>(null)
const uploading = ref(false)
const uploadResult = ref<string | null>(null)

async function loadPosts() {
  loading.value = true
  try {
    const params: any = { page: page.value, per_page: perPage.value }
    if (searchText.value) params.search = searchText.value
    if (filterChannel.value) params.channel = filterChannel.value
    if (filterType.value) params.post_type = filterType.value
    if (filterAuthor.value) params.author = filterAuthor.value
    if (filterBlogId.value) params.blog_id = filterBlogId.value
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

async function loadStats() {
  try {
    const { data } = await blogApi.getBlogStats()
    stats.value = data
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
  filterType.value = ''
  filterAuthor.value = ''
  filterBlogId.value = ''
  dateFrom.value = ''
  dateTo.value = ''
  page.value = 1
  loadPosts()
}

function channelLabel(ch: string) {
  return ch === 'br' ? '브랜드' : ch === 'opt' ? '최적' : ch || '-'
}

function channelColor(ch: string) {
  return ch === 'br' ? 'bg-blue-100 text-blue-700' : ch === 'opt' ? 'bg-purple-100 text-purple-700' : 'bg-slate-100 text-slate-500'
}

function typeLabel(t: string) {
  if (!t) return '-'
  if (t.includes('논문글')) return '논문글'
  if (t.includes('정보성글')) return '정보성'
  if (t.includes('홍보성글')) return '홍보성'
  if (t.includes('임상글')) return '임상글'
  if (t.includes('키컨텐츠')) return '키컨텐츠'
  if (t.includes('최적')) return '최적'
  return t.length > 10 ? t.slice(0, 10) + '…' : t
}

function typeColor(t: string) {
  if (t.includes('논문글')) return 'bg-emerald-100 text-emerald-700'
  if (t.includes('정보성글')) return 'bg-sky-100 text-sky-700'
  if (t.includes('홍보성글')) return 'bg-amber-100 text-amber-700'
  if (t.includes('임상글')) return 'bg-rose-100 text-rose-700'
  return 'bg-slate-100 text-slate-600'
}

function statusIcon(s: string) {
  if (s.includes('보고 완료')) return '✅'
  if (s.includes('발행 완료')) return '📤'
  if (s.includes('예약 발행')) return '⏱️'
  if (s.includes('작성 전')) return '📝'
  if (s.includes('취소')) return '❌'
  return '⏳'
}

const lastSyncInfo = computed(() => {
  if (!filterOptions.value?.last_sync) return null
  return filterOptions.value.last_sync
})

// CSV 업로드
function onCsvSelect(e: Event) {
  const target = e.target as HTMLInputElement
  uploadFile.value = target.files?.[0] || null
  uploadResult.value = null
}

async function doUpload() {
  if (!uploadFile.value) return
  uploading.value = true
  uploadResult.value = null
  try {
    const { data } = await blogApi.uploadBlogCsv(uploadFile.value)
    uploadResult.value = data.output || data.message || '완료'
    loadPosts()
    loadFilterOptions()
    loadStats()
  } catch (err: any) {
    uploadResult.value = err.response?.data?.detail || '업로드 실패'
  } finally {
    uploading.value = false
  }
}

watch(page, () => loadPosts())

onMounted(() => {
  loadPosts()
  loadFilterOptions()
  loadStats()
})
</script>

<template>
  <div class="p-5 h-full flex flex-col">
    <!-- 헤더 -->
    <div class="flex items-center justify-between mb-4">
      <div>
        <h2 class="text-xl font-bold text-slate-800">블로그 관리</h2>
        <p class="text-xs text-slate-400 mt-0.5" v-if="lastSyncInfo">
          마지막 데이터 기준: {{ lastSyncInfo.csv_modified_at }} · 임포트: {{ lastSyncInfo.imported_at }}
        </p>
      </div>
      <div class="flex items-center gap-3">
        <!-- 통계 뱃지 -->
        <div class="flex gap-2 text-xs" v-if="stats">
          <span class="px-2 py-1 bg-slate-100 rounded">전체 {{ stats.total?.toLocaleString() }}</span>
          <span class="px-2 py-1 bg-blue-50 text-blue-700 rounded">브랜드 {{ stats.by_channel?.br?.toLocaleString() || 0 }}</span>
          <span class="px-2 py-1 bg-purple-50 text-purple-700 rounded">최적 {{ stats.by_channel?.opt?.toLocaleString() || 0 }}</span>
          <span class="px-2 py-1 bg-emerald-50 text-emerald-700 rounded">논문글 {{ stats.paper_posts || 0 }}</span>
        </div>
        <!-- CSV 업로드 버튼 -->
        <button @click="showUploadModal = true"
                class="px-3 py-1.5 bg-slate-800 text-white text-xs rounded hover:bg-slate-700">
          CSV 업로드
        </button>
      </div>
    </div>

    <!-- 필터 바 -->
    <div class="bg-white border border-slate-200 rounded-lg p-3 mb-3 flex flex-wrap items-center gap-2">
      <input v-model="searchText" @keyup.enter="applyFilter"
             placeholder="제목·키워드·태그 검색"
             class="border border-slate-300 rounded px-2 py-1 text-sm w-56 focus:border-blue-400 focus:outline-none" />
      <select v-model="filterChannel" @change="applyFilter" class="border border-slate-300 rounded px-2 py-1 text-sm">
        <option value="">전체 채널</option>
        <option value="br">브랜드</option>
        <option value="opt">최적</option>
      </select>
      <select v-model="filterType" @change="applyFilter" class="border border-slate-300 rounded px-2 py-1 text-sm">
        <option value="">전체 종류</option>
        <option v-for="t in filterOptions?.post_types?.slice(0, 15)" :key="t.post_type" :value="t.post_type">
          {{ t.post_type }} ({{ t.cnt }})
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
                <th class="px-3 py-2 w-16">채널</th>
                <th class="px-3 py-2 w-20">종류</th>
                <th class="px-3 py-2">키워드</th>
                <th class="px-3 py-2">제목</th>
                <th class="px-3 py-2 w-16">작성자</th>
                <th class="px-3 py-2 w-24">발행일</th>
                <th class="px-3 py-2 w-10">상태</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="post in posts" :key="post.id"
                  @click="openDetail(post)"
                  class="border-b border-slate-100 hover:bg-blue-50/40 cursor-pointer transition-colors"
                  :class="{ 'bg-blue-50': selectedPost?.id === post.id }">
                <td class="px-3 py-2">
                  <span class="text-[10px] px-1.5 py-0.5 rounded-full font-medium"
                        :class="channelColor(post.blog_channel)">
                    {{ channelLabel(post.blog_channel) }}
                  </span>
                </td>
                <td class="px-3 py-2">
                  <span class="text-[10px] px-1.5 py-0.5 rounded font-medium"
                        :class="typeColor(post.post_type)">
                    {{ typeLabel(post.post_type) }}
                  </span>
                </td>
                <td class="px-3 py-2 text-slate-700 font-medium truncate max-w-[120px]">
                  {{ post.keyword || '-' }}
                </td>
                <td class="px-3 py-2 text-slate-600 truncate max-w-[250px]">
                  {{ post.title || '-' }}
                </td>
                <td class="px-3 py-2 text-slate-500 text-xs">{{ post.author || '-' }}</td>
                <td class="px-3 py-2 text-slate-400 text-xs">{{ post.published_at || '-' }}</td>
                <td class="px-3 py-2 text-center">{{ statusIcon(post.status) }}</td>
              </tr>
              <tr v-if="!posts.length && !loading">
                <td colspan="7" class="px-3 py-8 text-center text-slate-400 text-sm">데이터가 없습니다</td>
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
      <div class="w-[340px] shrink-0 bg-white border border-slate-200 rounded-lg overflow-auto">
        <div v-if="!selectedPost" class="flex items-center justify-center h-full text-slate-300 text-sm">
          게시글을 선택하세요
        </div>
        <div v-else class="p-4 space-y-3">
          <!-- 헤더 -->
          <div>
            <div class="flex gap-1.5 mb-2">
              <span class="text-[10px] px-1.5 py-0.5 rounded-full font-medium"
                    :class="channelColor(selectedPost.blog_channel)">
                {{ channelLabel(selectedPost.blog_channel) }}
              </span>
              <span class="text-[10px] px-1.5 py-0.5 rounded font-medium"
                    :class="typeColor(selectedPost.post_type)">
                {{ typeLabel(selectedPost.post_type) }}
              </span>
            </div>
            <h3 class="font-bold text-slate-800 text-sm leading-snug">
              {{ selectedPost.title || '(제목 없음)' }}
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
              <span class="text-slate-400">작성자</span>
              <span class="text-slate-700">{{ selectedPost.author || '-' }}</span>
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
              <span class="text-slate-700">{{ selectedPost.status || '-' }}</span>
            </div>
            <div class="flex justify-between" v-if="selectedPost.blog_id">
              <span class="text-slate-400">계정</span>
              <span class="text-slate-700 font-mono text-[11px]">{{ selectedPost.blog_id }}</span>
            </div>
            <div class="flex justify-between" v-if="selectedPost.project">
              <span class="text-slate-400">프로젝트</span>
              <span class="text-slate-700 truncate max-w-[180px]">{{ selectedPost.project.split('(')[0] }}</span>
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
              <span class="text-emerald-500 ml-1">★{{ lp.evidence_level }}/5</span>
            </div>
          </div>

          <!-- 비고 -->
          <div v-if="selectedPost.note" class="pt-2 border-t">
            <p class="text-[10px] text-slate-400 mb-1">비고</p>
            <p class="text-xs text-slate-600">{{ selectedPost.note }}</p>
          </div>
        </div>
      </div>
    </div>

    <!-- CSV 업로드 모달 -->
    <div v-if="showUploadModal" class="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
      <div class="bg-white rounded-lg p-5 w-96 shadow-xl">
        <h3 class="font-bold text-slate-800 mb-3">CSV 업로드 (관리자 전용)</h3>
        <p class="text-xs text-slate-500 mb-3">
          노션에서 내보낸 CSV 파일을 업로드하면 블로그 데이터가 갱신됩니다.<br/>
          기존 데이터와 중복되는 항목은 자동으로 건너뜁니다.
        </p>
        <input type="file" accept=".csv" @change="onCsvSelect"
               class="block w-full text-sm text-slate-500 mb-3
                      file:mr-4 file:py-1.5 file:px-3 file:rounded file:border-0
                      file:text-sm file:font-medium file:bg-slate-100 file:text-slate-700
                      hover:file:bg-slate-200" />
        <div v-if="uploadResult" class="p-2 bg-slate-50 rounded text-xs text-slate-600 mb-3 whitespace-pre-line">
          {{ uploadResult }}
        </div>
        <div class="flex justify-end gap-2">
          <button @click="showUploadModal = false; uploadFile = null; uploadResult = null"
                  class="px-3 py-1.5 text-xs border rounded hover:bg-slate-50">닫기</button>
          <button @click="doUpload" :disabled="!uploadFile || uploading"
                  class="px-3 py-1.5 text-xs bg-slate-800 text-white rounded hover:bg-slate-700 disabled:opacity-40">
            {{ uploading ? '업로드 중...' : '업로드' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

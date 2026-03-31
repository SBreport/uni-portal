<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import * as blogApi from '@/api/blog'
import { channelLabel, channelColor } from '@/utils/blogFormatters'
import { useColumnResize } from '@/composables/useResizePanel'

const props = defineProps<{
  branchFilter?: string
}>()

const accounts = ref<any[]>([])
const loading = ref(false)
const search = ref('')
const channelFilter = ref('')
const editingAccount = ref<string | null>(null)
const editForm = ref({ account_name: '', account_group: '' })
const selectedAccounts = ref<Set<string>>(new Set())

// 도구 실행 상태
const scrapingNicknames = ref(false)
const fixingUrlTitles = ref(false)
const toolMessage = ref('')

async function runScrapeNicknames() {
  scrapingNicknames.value = true
  toolMessage.value = '닉네임 수집 중...'
  try {
    const { data } = await blogApi.scrapeNicknames()
    toolMessage.value = `닉네임 수집 완료: ${data.updated}건 갱신 / ${data.failed}건 실패`
    loadAccounts()
  } catch (e: any) {
    toolMessage.value = `닉네임 수집 실패: ${e.response?.data?.detail || e.message}`
  } finally {
    scrapingNicknames.value = false
    setTimeout(() => { toolMessage.value = '' }, 5000)
  }
}

async function runFixUrlTitles() {
  fixingUrlTitles.value = true
  toolMessage.value = 'URL 제목 수정 중...'
  try {
    const { data } = await blogApi.fixUrlTitles()
    toolMessage.value = data.total === 0
      ? 'URL 제목 수정 대상이 없습니다'
      : `URL 제목 수정 완료: ${data.fixed}건 수정 / ${data.failed}건 실패`
  } catch (e: any) {
    toolMessage.value = `URL 제목 수정 실패: ${e.response?.data?.detail || e.message}`
  } finally {
    fixingUrlTitles.value = false
    setTimeout(() => { toolMessage.value = '' }, 5000)
  }
}

// 정렬
type SortKey = 'channel' | 'blog_id' | 'blog_nickname' | 'blog_title' | 'post_count' | 'recent_count' | 'last_published'
const sortKey = ref<SortKey>('last_published')
const sortAsc = ref(false)

function toggleSort(key: SortKey) {
  if (sortKey.value === key) {
    sortAsc.value = !sortAsc.value
  } else {
    sortKey.value = key
    // 기본 방향: 게시글/발행일은 내림차순, 나머지는 오름차순
    sortAsc.value = !['post_count', 'recent_count', 'last_published'].includes(key)
  }
}

function sortIcon(key: SortKey) {
  if (sortKey.value !== key) return ''
  return sortAsc.value ? ' \u25B2' : ' \u25BC'
}

// 컬럼 리사이즈
const cols = ref([
  { key: 'check',          label: '',             width: 36,  minWidth: 30 },
  { key: 'channel',        label: '채널',         width: 52,  minWidth: 46 },
  { key: 'blog_id',        label: '블로그 ID',    width: 120, minWidth: 80 },
  { key: 'blog_nickname',  label: '닉네임',       width: 120, minWidth: 60 },
  { key: 'post_count',     label: '전체',         width: 50,  minWidth: 40 },
  { key: 'recent_count',   label: '최근',         width: 50,  minWidth: 40 },
  { key: 'last_published', label: '최근발행',     width: 84,  minWidth: 60 },
  { key: 'blog_title',     label: '블로그 타이틀', width: 180, minWidth: 100 },
  { key: 'blog_link',      label: '블로그 링크',  width: 170, minWidth: 120 },
  { key: 'edit',           label: '',             width: 38,  minWidth: 30 },
])
const { startResize } = useColumnResize(cols)

const sortedAccounts = computed(() => {
  const arr = [...accounts.value]
  const key = sortKey.value
  const asc = sortAsc.value
  arr.sort((a, b) => {
    let va = a[key] ?? ''
    let vb = b[key] ?? ''
    if (key === 'post_count' || key === 'recent_count') {
      va = Number(va) || 0
      vb = Number(vb) || 0
    } else {
      va = String(va).toLowerCase()
      vb = String(vb).toLowerCase()
    }
    if (va < vb) return asc ? -1 : 1
    if (va > vb) return asc ? 1 : -1
    // 2차 정렬: 채널 오름차순
    if (key !== 'channel') {
      const ca = (a.channel || '').toLowerCase()
      const cb = (b.channel || '').toLowerCase()
      if (ca < cb) return -1
      if (ca > cb) return 1
    }
    return 0
  })
  return arr
})

async function loadAccounts() {
  loading.value = true
  try {
    const params: any = {}
    if (channelFilter.value) params.channel = channelFilter.value
    if (search.value) params.search = search.value
    if (props.branchFilter) params.branch_filter = props.branchFilter
    const { data } = await blogApi.getBlogAccounts(params)
    accounts.value = data.items
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
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

function cancelEdit() { editingAccount.value = null }

function toggleAccount(blogId: string) {
  if (selectedAccounts.value.has(blogId)) {
    selectedAccounts.value.delete(blogId)
  } else {
    selectedAccounts.value.add(blogId)
  }
}

function toggleAllAccounts() {
  if (selectedAccounts.value.size === accounts.value.length) {
    selectedAccounts.value.clear()
  } else {
    selectedAccounts.value = new Set(accounts.value.map((a: any) => a.blog_id))
  }
}

const allAccountsSelected = computed(() =>
  accounts.value.length > 0 && selectedAccounts.value.size === accounts.value.length
)

onMounted(loadAccounts)
</script>

<template>
  <div class="flex-1 flex flex-col min-h-0">
    <!-- 필터 -->
    <div class="bg-white border border-slate-200 rounded-lg p-3 mb-3 flex items-center gap-2">
      <input v-model="search" @keyup.enter="loadAccounts"
             placeholder="계정 ID / 닉네임 검색"
             class="border border-slate-300 rounded px-2 py-1 text-sm w-56 focus:border-blue-400 focus:outline-none" />
      <button @click="loadAccounts" class="px-3 py-1 bg-blue-500 text-white text-xs rounded hover:bg-blue-600">검색</button>
      <select v-model="channelFilter" @change="loadAccounts" class="border border-slate-300 rounded px-2 py-1 text-sm">
        <option value="">전체 채널</option>
        <option value="br">브랜드</option>
        <option value="opt">최적</option>
        <option value="cafe">카페</option>
      </select>
      <!-- 관리 도구 -->
      <div class="ml-auto flex items-center gap-2">
        <button @click="runScrapeNicknames"
                :disabled="scrapingNicknames"
                class="px-2 py-1 text-xs rounded border border-slate-300 hover:bg-slate-100 disabled:opacity-50 disabled:cursor-wait whitespace-nowrap">
          {{ scrapingNicknames ? '수집 중...' : '닉네임 수집' }}
        </button>
        <button @click="runFixUrlTitles"
                :disabled="fixingUrlTitles"
                class="px-2 py-1 text-xs rounded border border-slate-300 hover:bg-slate-100 disabled:opacity-50 disabled:cursor-wait whitespace-nowrap">
          {{ fixingUrlTitles ? '수정 중...' : 'URL 제목 수정' }}
        </button>
        <span class="text-xs text-slate-400">
          {{ accounts.length }}개 계정
          <span v-if="selectedAccounts.size > 0" class="text-blue-500 ml-1">
            ({{ selectedAccounts.size }}개 선택)
          </span>
        </span>
      </div>
    </div>
    <!-- 도구 실행 결과 메시지 -->
    <div v-if="toolMessage"
         class="bg-blue-50 border border-blue-200 rounded-lg px-3 py-2 mb-3 text-xs text-blue-700">
      {{ toolMessage }}
    </div>

    <!-- 테이블 -->
    <div class="flex-1 bg-white border border-slate-200 rounded-lg overflow-auto">
      <table class="text-sm" style="table-layout: fixed; width: max-content; min-width: 100%;">
        <colgroup>
          <col v-for="c in cols" :key="c.key"
               :style="c.width ? { width: c.width + 'px' } : {}" />
        </colgroup>
        <thead class="sticky top-0 z-10" style="box-shadow: 0 1px 3px rgba(0,0,0,0.08);">
          <tr class="text-left text-xs text-slate-500 border-b">
            <!-- 체크박스 -->
            <th class="px-2 py-2 bg-slate-50">
              <input type="checkbox"
                     :checked="allAccountsSelected"
                     @change="toggleAllAccounts"
                     class="rounded border-slate-300" />
            </th>
            <!-- 정렬 가능 헤더 + 리사이즈 핸들 -->
            <th v-for="(c, idx) in cols.slice(1, -1)" :key="c.key"
                @click="toggleSort(c.key as SortKey)"
                class="px-2 py-2 bg-slate-50 relative select-none cursor-pointer hover:bg-slate-100 transition-colors group"
                :class="{ 'text-right': c.key === 'post_count' || c.key === 'recent_count' }">
              <span>{{ c.label }}</span>
              <span v-if="sortKey === c.key" class="ml-0.5 text-blue-500 text-[9px]">{{ sortIcon(c.key as SortKey) }}</span>
              <div v-if="c.width > 0"
                   @mousedown.stop.prevent="startResize(idx + 1, $event)"
                   class="absolute -right-1.5 top-0 bottom-0 w-3 cursor-col-resize z-10 hover:bg-blue-300/50" />
            </th>
            <!-- 편집 -->
            <th class="px-2 py-2 bg-slate-50"></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="acc in sortedAccounts" :key="acc.blog_id"
              class="border-b border-slate-100 hover:bg-slate-50/50"
              :class="{ 'bg-blue-50/50': selectedAccounts.has(acc.blog_id) }">
            <td class="px-2 py-1.5">
              <input type="checkbox"
                     :checked="selectedAccounts.has(acc.blog_id)"
                     @change="toggleAccount(acc.blog_id)"
                     class="rounded border-slate-300" />
            </td>
            <td class="px-2 py-1.5">
              <span class="text-[10px] px-1.5 py-0.5 rounded-full font-medium whitespace-nowrap"
                    :class="channelColor(acc.channel)">
                {{ channelLabel(acc.channel) }}
              </span>
            </td>
            <td class="px-2 py-1.5 font-mono text-[11px] text-slate-600 truncate">{{ acc.blog_id }}</td>
            <td class="px-2 py-1.5 text-xs truncate"
                :class="acc.blog_nickname?.startsWith('(') ? 'text-red-400 italic' : acc.blog_nickname ? 'text-slate-700' : 'text-slate-400'">
              {{ acc.blog_nickname || '-' }}
            </td>
            <td class="px-2 py-1.5 text-right text-xs text-slate-600 font-medium">{{ acc.post_count }}</td>
            <td class="px-2 py-1.5 text-right text-xs font-medium"
                :class="acc.recent_count > 0 ? 'text-blue-600' : 'text-slate-300'">{{ acc.recent_count ?? 0 }}</td>
            <td class="px-2 py-1.5 text-xs text-slate-400">{{ acc.last_published || '-' }}</td>
            <td class="px-2 py-1.5 text-xs text-slate-500 truncate">{{ acc.blog_title || '-' }}</td>
            <td class="px-2 py-1.5 text-xs truncate">
              <a v-if="acc.channel !== 'cafe'"
                 :href="`https://blog.naver.com/${acc.blog_id}`"
                 target="_blank"
                 @click.stop
                 class="text-blue-400 hover:text-blue-600 hover:underline">blog.naver.com/{{ acc.blog_id }}</a>
              <span v-else class="text-slate-300">-</span>
            </td>
            <td class="px-2 py-1.5 text-right">
              <template v-if="editingAccount === acc.blog_id">
                <button @click="saveAccount(acc.blog_id)" class="text-[10px] text-blue-600 hover:underline mr-1">저장</button>
                <button @click="cancelEdit" class="text-[10px] text-slate-400 hover:underline">취소</button>
              </template>
              <template v-else>
                <button @click="startEdit(acc)" class="text-[10px] text-slate-400 hover:text-blue-600">편집</button>
              </template>
            </td>
          </tr>
          <tr v-if="!accounts.length && !loading">
            <td colspan="10" class="px-3 py-8 text-center text-slate-400 text-sm">계정이 없습니다</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

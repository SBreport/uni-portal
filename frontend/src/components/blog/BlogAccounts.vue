<script setup lang="ts">
import { ref, computed, onMounted, h } from 'vue'
import * as blogApi from '@/api/blog'
import { channelLabel, channelColor } from '@/utils/blogFormatters'
import DataTable from '@/components/common/DataTable.vue'
import { createColumnHelper } from '@tanstack/vue-table'

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

// 도구 패널 토글
const showTools = ref(false)

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

// ── Column definitions ────────────────────────────────────────────
const col = createColumnHelper<any>()

const columns = computed(() => [
  col.display({
    id: 'select',
    size: 36,
    enableSorting: false,
    header: () => h('input', {
      type: 'checkbox',
      checked: allAccountsSelected.value,
      onChange: () => toggleAllAccounts(),
      class: 'rounded border-slate-300',
    }),
    cell: (info) => {
      const blogId = info.row.original.blog_id
      return h('input', {
        type: 'checkbox',
        checked: selectedAccounts.value.has(blogId),
        onChange: (e: Event) => { e.stopPropagation(); toggleAccount(blogId) },
        class: 'rounded border-slate-300',
      })
    },
  }),

  col.accessor('channel', {
    header: '채널',
    size: 52,
    enableSorting: true,
    cell: (info) => h('span', {
      class: `text-xs px-1.5 py-0.5 rounded-full font-medium whitespace-nowrap ${channelColor(info.getValue())}`,
    }, channelLabel(info.getValue())),
  }),

  col.accessor('blog_id', {
    header: '블로그 ID',
    size: 120,
    enableSorting: true,
    cell: (info) => h('span', {
      class: 'font-mono text-[11px] text-slate-600 truncate block',
    }, info.getValue()),
  }),

  col.accessor('blog_nickname', {
    header: '닉네임',
    size: 120,
    enableSorting: true,
    cell: (info) => {
      const v = info.getValue()
      const cls = v?.startsWith('(') ? 'text-red-400 italic' : v ? 'text-slate-700' : 'text-slate-400'
      return h('span', { class: `text-xs truncate block ${cls}` }, v || '-')
    },
  }),

  col.accessor('post_count', {
    header: '전체',
    size: 50,
    enableSorting: true,
    cell: (info) => h('span', { class: 'text-right text-xs text-slate-600 font-medium block tabular-nums' }, info.getValue()),
  }),

  col.accessor('recent_count', {
    header: '최근',
    size: 50,
    enableSorting: true,
    cell: (info) => {
      const v = info.getValue() ?? 0
      return h('span', {
        class: `text-right text-xs font-medium block tabular-nums ${v > 0 ? 'text-blue-600' : 'text-slate-300'}`,
      }, v)
    },
  }),

  col.accessor('last_published', {
    header: '최근발행',
    size: 84,
    enableSorting: true,
    cell: (info) => h('span', { class: 'text-xs text-slate-400 tabular-nums' }, info.getValue() || '-'),
  }),

  col.accessor('blog_title', {
    header: '블로그 타이틀',
    size: 180,
    enableSorting: true,
    cell: (info) => h('span', { class: 'text-xs text-slate-500 truncate block' }, info.getValue() || '-'),
  }),

  col.accessor('blog_link', {
    header: '블로그 링크',
    size: 170,
    enableSorting: false,
    cell: (info) => {
      const acc = info.row.original
      if (acc.channel !== 'cafe') {
        return h('a', {
          href: `https://blog.naver.com/${acc.blog_id}`,
          target: '_blank',
          onClick: (e: MouseEvent) => e.stopPropagation(),
          class: 'text-xs text-blue-400 hover:text-blue-600 hover:underline truncate block',
        }, `blog.naver.com/${acc.blog_id}`)
      }
      return h('span', { class: 'text-xs text-slate-300' }, '-')
    },
  }),

  col.display({
    id: 'edit',
    size: 60,
    enableSorting: false,
    header: '',
    cell: (info) => {
      const acc = info.row.original
      if (editingAccount.value === acc.blog_id) {
        return h('div', { class: 'flex justify-end gap-1' }, [
          h('button', {
            onClick: (e: MouseEvent) => { e.stopPropagation(); saveAccount(acc.blog_id) },
            class: 'text-xs text-blue-600 hover:underline',
          }, '저장'),
          h('button', {
            onClick: (e: MouseEvent) => { e.stopPropagation(); cancelEdit() },
            class: 'text-xs text-slate-400 hover:underline',
          }, '취소'),
        ])
      }
      return h('div', { class: 'flex justify-end' }, [
        h('button', {
          onClick: (e: MouseEvent) => { e.stopPropagation(); startEdit(acc) },
          class: 'text-xs text-slate-400 hover:text-blue-600',
        }, '편집'),
      ])
    },
  }),
])

// Row highlight: selected accounts get a blue tint — handled via onRowClick + CSS class
// DataTable doesn't support per-row class, so selection highlight is done via checkbox only
</script>

<template>
  <div class="h-full flex flex-col min-h-0">
    <!-- 필터 -->
    <div class="bg-white border border-slate-200 rounded-lg px-3 py-2 mb-2 flex items-center gap-3 flex-none">
      <input v-model="search" @keyup.enter="loadAccounts"
             placeholder="계정 ID / 닉네임 검색"
             class="border border-slate-300 rounded px-2 h-7 text-xs w-48 focus:border-blue-400 focus:outline-none" />
      <button @click="loadAccounts"
              class="px-3 h-7 bg-blue-600 text-white text-xs rounded hover:bg-blue-700">검색</button>
      <select v-model="channelFilter" @change="loadAccounts"
              class="border border-slate-300 rounded px-2 h-7 text-xs w-32">
        <option value="">전체 채널</option>
        <option value="br">브랜드</option>
        <option value="opt">최적</option>
        <option value="cafe">카페</option>
      </select>
      <span class="text-xs text-slate-400 ml-auto tabular-nums">
        {{ accounts.length }}개 계정
        <span v-if="selectedAccounts.size > 0" class="text-blue-500 ml-1">
          ({{ selectedAccounts.size }}개 선택)
        </span>
      </span>
    </div>

    <!-- 테이블 (flex-1로 남은 공간 채움) -->
    <div class="flex-1 min-h-0 overflow-auto min-w-[720px]">
      <DataTable
        :data="accounts"
        :columns="columns"
        :page-size="100"
        height="none"
        :searchable="false"
      />
    </div>

    <!-- 도구 패널 (접힘 기본) -->
    <div class="flex-none mt-2">
      <button @click="showTools = !showTools"
              class="text-xs px-2 py-1 rounded border transition-colors"
              :class="showTools
                ? 'border-blue-400 text-blue-600 bg-blue-50'
                : 'border-slate-300 text-slate-500 hover:bg-slate-50'">
        도구 {{ showTools ? '▴' : '▾' }}
      </button>
      <div v-if="showTools" class="mt-2 flex items-center gap-2 bg-white border border-slate-200 rounded-lg px-3 py-1.5">
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
        <span v-if="toolMessage" class="text-xs text-blue-700 ml-2">{{ toolMessage }}</span>
      </div>
    </div>
  </div>
</template>

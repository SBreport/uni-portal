<script setup lang="ts">
import { ref, computed } from 'vue'
import { useCafeStore } from '@/stores/cafe'
import * as cafeApi from '@/api/cafe'
import { useAuthStore } from '@/stores/auth'

const emit = defineEmits<{ open: [id: number] }>()
const store = useCafeStore()
const auth = useAuthStore()

const statusColor: Record<string, { bg: string; border: string; dot: string }> = {
  '작성대기': { bg: 'bg-slate-400', border: 'border-slate-400', dot: '#94a3b8' },
  '작성완료': { bg: 'bg-amber-500', border: 'border-amber-500', dot: '#f59e0b' },
  '수정요청': { bg: 'bg-red-500', border: 'border-red-500', dot: '#ef4444' },
  '검수완료': { bg: 'bg-blue-500', border: 'border-blue-500', dot: '#3b82f6' },
  '발행완료': { bg: 'bg-emerald-500', border: 'border-emerald-500', dot: '#10b981' },
  '보류': { bg: 'bg-purple-500', border: 'border-purple-500', dot: '#8b5cf6' },
}
const statuses = ['작성대기', '작성완료', '수정요청', '검수완료', '발행완료', '보류']

// 필터
const filterStatus = ref('')
const searchQuery = ref('')

const filteredArticles = computed(() => {
  let list = store.articles
  if (filterStatus.value) {
    list = list.filter(a => a.status === filterStatus.value)
  }
  if (searchQuery.value) {
    const q = searchQuery.value.toLowerCase()
    list = list.filter(a =>
      (a.title || '').toLowerCase().includes(q) ||
      (a.body || '').toLowerCase().includes(q) ||
      (a.equipment_name || '').toLowerCase().includes(q) ||
      (a.keyword || '').toLowerCase().includes(q)
    )
  }
  return list
})

// 상태별 통계
const statusStats = computed(() => {
  const map: Record<string, number> = {}
  store.articles.forEach(a => {
    const s = a.status || '작성대기'
    map[s] = (map[s] || 0) + 1
  })
  return map
})

// 댓글 파싱
function parseComments(article: any): { slot: number; comment: string; reply: string }[] {
  try {
    if (article.comments_json && article.comments_json !== '[]') {
      return JSON.parse(article.comments_json)
    }
  } catch { /* ignore */ }
  return []
}

// 날짜 포맷
function shortDate(dateStr: string | null | undefined): string {
  if (!dateStr) return '—'
  const d = new Date(dateStr)
  const mm = String(d.getMonth() + 1).padStart(2, '0')
  const dd = String(d.getDate()).padStart(2, '0')
  return `${mm}.${dd}`
}

// 상태 빠른 변경
const changingStatus = ref<number | null>(null)
async function quickStatusChange(articleId: number, newStatus: string) {
  changingStatus.value = articleId
  try {
    await cafeApi.changeStatus(articleId, newStatus, auth.username, '')
    await store.loadArticles()
  } finally {
    changingStatus.value = null
  }
}
</script>

<template>
  <div>
    <p v-if="!store.articles.length" class="text-sm text-slate-400 py-8 text-center">
      지점과 기간을 선택하면 원고 목록이 표시됩니다.
    </p>

    <template v-else>
      <!-- 상단: 상태 필터 칩 + 검색 -->
      <div class="flex items-center gap-2 mb-3 flex-wrap">
        <button
          @click="filterStatus = ''"
          :class="[
            'px-2.5 py-1 rounded-full text-xs font-medium transition',
            !filterStatus ? 'bg-slate-800 text-white' : 'bg-slate-100 text-slate-500 hover:bg-slate-200'
          ]"
        >전체 {{ store.articles.length }}</button>
        <button
          v-for="(count, status) in statusStats" :key="status"
          @click="filterStatus = filterStatus === status ? '' : status"
          :class="[
            'px-2.5 py-1 rounded-full text-xs font-medium transition',
            filterStatus === status ? 'text-white ' + (statusColor[status]?.bg || 'bg-slate-400') : 'bg-slate-100 text-slate-500 hover:bg-slate-200'
          ]"
        >{{ status }} {{ count }}</button>

        <div class="ml-auto flex items-center gap-2">
          <input v-model="searchQuery" placeholder="제목, 본문, 장비 검색..."
            class="px-3 py-1.5 border border-slate-300 rounded-md text-sm w-52 focus:outline-none focus:ring-1 focus:ring-blue-400" />
          <span class="text-xs text-slate-400">{{ filteredArticles.length }}건</span>
        </div>
      </div>

      <!-- 헤더 -->
      <div class="grid-header">
        <div class="gh-meta">원고 정보</div>
        <div class="gh-body">본문</div>
        <div class="gh-cmt">댓글 · 대댓글</div>
        <div class="gh-side">상세</div>
      </div>

      <!-- 4컬럼 블록 리스트 -->
      <div class="overflow-auto" style="max-height: calc(100vh - 300px)">
        <div
          v-for="(article, idx) in filteredArticles"
          :key="article.id"
          class="article-row"
          :class="{ 'row-even': idx % 2 === 1 }"
        >
          <!-- 1: 메타 정보 -->
          <div class="col-meta">
            <div class="status-bar" :style="{ backgroundColor: statusColor[article.status]?.dot || '#94a3b8' }"></div>
            <div class="meta-content">
              <div class="flex items-center gap-1 mb-0.5">
                <span class="order-num">{{ article.article_order }}</span>
                <span
                  :class="'status-badge ' + (statusColor[article.status]?.bg || 'bg-slate-400')"
                >{{ article.status }}</span>
              </div>
              <p class="title-text">{{ article.title || '(미작성)' }}</p>
              <span v-if="article.equipment_name"
                class="equip-tag mt-1">{{ article.equipment_name }}</span>
            </div>
          </div>

          <!-- 2: 본문 -->
          <div class="col-body">
            <p v-if="article.body" class="body-text">{{ article.body }}</p>
            <p v-else class="text-[11px] text-slate-300 italic">본문 미작성</p>
          </div>

          <!-- 3: 댓글 + 대댓글 -->
          <div class="col-comments">
            <template v-if="parseComments(article).length">
              <div
                v-for="cmt in parseComments(article)"
                :key="cmt.slot"
                class="comment-pair"
              >
                <div class="cmt-row">
                  <span class="cmt-label">댓{{ cmt.slot }}</span>
                  <span v-if="cmt.comment" class="cmt-text">{{ cmt.comment }}</span>
                  <span v-else class="cmt-empty">—</span>
                </div>
                <div class="reply-row">
                  <span class="reply-label">↩</span>
                  <span v-if="cmt.reply" class="reply-text">{{ cmt.reply }}</span>
                  <span v-else class="cmt-empty">—</span>
                </div>
              </div>
            </template>
            <span v-else class="text-[11px] text-slate-300">댓글 없음</span>
          </div>

          <!-- 4: 우측 사이드 — 메타 + 빠른 액션 -->
          <div class="col-side">
            <!-- 키워드 · 카테고리 -->
            <div class="side-row">
              <span class="side-label">키워드</span>
              <span class="side-value">{{ article.keyword || '—' }}</span>
            </div>
            <div class="side-row">
              <span class="side-label">카테고리</span>
              <span class="side-value">{{ article.category || '—' }}</span>
            </div>

            <div class="side-divider"></div>

            <!-- 날짜 -->
            <div class="side-row">
              <span class="side-label">작성</span>
              <span class="side-value">{{ shortDate(article.created_at) }}</span>
            </div>
            <div class="side-row">
              <span class="side-label">수정</span>
              <span class="side-value">{{ shortDate(article.updated_at) }}</span>
            </div>

            <div class="side-divider"></div>

            <!-- 빠른 상태 변경 -->
            <select
              :value="article.status"
              @change="quickStatusChange(article.id, ($event.target as HTMLSelectElement).value)"
              :disabled="changingStatus === article.id"
              class="side-select"
            >
              <option v-for="s in statuses" :key="s" :value="s">{{ s }}</option>
            </select>

            <!-- 액션 -->
            <div class="flex items-center gap-2 mt-1.5">
              <a v-if="article.published_url" :href="article.published_url" target="_blank"
                class="side-link" title="발행 링크">🔗 발행</a>
              <button @click="emit('open', article.id)"
                class="side-link" title="원고 편집">✏️ 편집</button>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
/* 헤더 */
.grid-header {
  display: grid;
  grid-template-columns: 180px 1fr 1fr 150px;
  border-bottom: 2px solid #cbd5e1;
  padding: 6px 0;
  font-size: 11px;
  font-weight: 600;
  color: #64748b;
}
.gh-meta { padding-left: 14px; }
.gh-body { padding-left: 12px; }
.gh-cmt { padding-left: 10px; }
.gh-side { padding-left: 10px; }

/* 행 */
.article-row {
  display: grid;
  grid-template-columns: 180px 1fr 1fr 150px;
  border-bottom: 1px solid #e2e8f0;
  min-height: 56px;
  transition: background-color 0.15s;
}
.row-even {
  background-color: #fafbfc;
}
.article-row:hover {
  background-color: #eff6ff;
}

/* 1: 메타 */
.col-meta {
  display: flex;
  position: relative;
  border-right: 1px solid #f1f5f9;
}
.status-bar {
  width: 3px;
  min-height: 100%;
  flex-shrink: 0;
}
.meta-content {
  padding: 7px 8px;
  min-width: 0;
}
.order-num {
  font-family: ui-monospace, monospace;
  font-size: 11px;
  color: #94a3b8;
  font-weight: 600;
  min-width: 16px;
}
.status-badge {
  font-size: 9px;
  font-weight: 700;
  color: white;
  padding: 1px 5px;
  border-radius: 3px;
  white-space: nowrap;
}
.title-text {
  font-size: 11px;
  font-weight: 600;
  color: #1e293b;
  line-height: 1.4;
  word-break: keep-all;
  overflow-wrap: break-word;
}
.equip-tag {
  display: inline-block;
  font-size: 9px;
  color: #2563eb;
  background: #eff6ff;
  padding: 1px 5px;
  border-radius: 3px;
  font-weight: 500;
  white-space: nowrap;
}

/* 2: 본문 */
.col-body {
  padding: 7px 10px;
  border-right: 1px solid #f1f5f9;
  overflow: hidden;
}
.body-text {
  font-size: 11px;
  color: #475569;
  line-height: 1.55;
  white-space: pre-line;
  display: -webkit-box;
  -webkit-line-clamp: 8;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* 3: 댓글 */
.col-comments {
  padding: 7px 8px;
  border-right: 1px solid #f1f5f9;
  overflow: hidden;
}
.comment-pair {
  margin-bottom: 5px;
  padding-bottom: 5px;
  border-bottom: 1px dotted #e2e8f0;
}
.comment-pair:last-child {
  margin-bottom: 0;
  padding-bottom: 0;
  border-bottom: none;
}
.cmt-row, .reply-row {
  display: flex;
  gap: 4px;
  font-size: 11px;
  line-height: 1.5;
}
.reply-row {
  padding-left: 16px;
  margin-top: 1px;
}
.cmt-label {
  flex-shrink: 0;
  font-size: 9px;
  font-weight: 700;
  color: #3b82f6;
  background: #eff6ff;
  padding: 0 4px;
  border-radius: 2px;
  height: 16px;
  line-height: 16px;
  margin-top: 1px;
}
.reply-label {
  flex-shrink: 0;
  color: #94a3b8;
  font-size: 11px;
  width: 14px;
}
.cmt-text { color: #334155; }
.reply-text { color: #64748b; }
.cmt-empty { color: #cbd5e1; }

/* 4: 사이드 패널 */
.col-side {
  padding: 7px 10px;
  background: #f8fafc;
  border-left: none;
}
.row-even .col-side {
  background: #f1f5f9;
}
.article-row:hover .col-side {
  background: #e0ecff;
}

.side-row {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 4px;
  margin-bottom: 2px;
}
.side-label {
  font-size: 9px;
  color: #94a3b8;
  font-weight: 600;
  flex-shrink: 0;
}
.side-value {
  font-size: 10px;
  color: #475569;
  text-align: right;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.side-divider {
  border-top: 1px solid #e2e8f0;
  margin: 4px 0;
}

.side-select {
  width: 100%;
  font-size: 10px;
  padding: 2px 4px;
  border: 1px solid #cbd5e1;
  border-radius: 4px;
  background: white;
  color: #334155;
  cursor: pointer;
  outline: none;
}
.side-select:focus {
  border-color: #3b82f6;
  box-shadow: 0 0 0 1px #3b82f6;
}
.side-select:disabled {
  opacity: 0.5;
  cursor: wait;
}

.side-link {
  font-size: 10px;
  color: #3b82f6;
  transition: color 0.15s;
  cursor: pointer;
  background: none;
  border: none;
  padding: 0;
}
.side-link:hover {
  color: #1d4ed8;
  text-decoration: underline;
}
</style>

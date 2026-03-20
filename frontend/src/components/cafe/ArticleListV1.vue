<script setup lang="ts">
import { ref, computed } from 'vue'
import { useCafeStore } from '@/stores/cafe'

const emit = defineEmits<{ open: [id: number] }>()
const store = useCafeStore()

const statusColor: Record<string, { bg: string; dot: string }> = {
  '작성대기': { bg: 'bg-slate-400', dot: '#94a3b8' },
  '작성완료': { bg: 'bg-amber-500', dot: '#f59e0b' },
  '수정요청': { bg: 'bg-red-500', dot: '#ef4444' },
  '검수완료': { bg: 'bg-blue-500', dot: '#3b82f6' },
  '발행완료': { bg: 'bg-emerald-500', dot: '#10b981' },
  '보류': { bg: 'bg-purple-500', dot: '#8b5cf6' },
}

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

      <!-- 3컬럼: 순번+상태 | 제목+본문 | 댓글+대댓글 -->
      <div class="overflow-auto" style="max-height: calc(100vh - 260px)">
        <div
          v-for="(article, idx) in filteredArticles"
          :key="article.id"
          class="article-row"
          :class="{ 'row-even': idx % 2 === 1 }"
        >
          <!-- 1열: 순번 + 상태 -->
          <div class="col-num">
            <span class="order-num">{{ article.article_order }}</span>
            <span :class="'status-badge ' + (statusColor[article.status]?.bg || 'bg-slate-400')">{{ article.status }}</span>
          </div>

          <!-- 2열: 제목 + 장비 + 본문 -->
          <div class="col-content">
            <div class="content-header">
              <span v-if="article.equipment_name" class="equip-tag">{{ article.equipment_name }}</span>
              <span class="title-text">{{ article.title || '(미작성)' }}</span>
              <a v-if="article.published_url" :href="article.published_url" target="_blank"
                class="link-icon" title="발행 링크">🔗</a>
              <button @click="emit('open', article.id)"
                class="edit-btn ml-auto" title="원고 편집">
                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
                  <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
                </svg>
              </button>
            </div>
            <p v-if="article.body" class="body-text">{{ article.body }}</p>
            <p v-else class="text-[11px] text-slate-300 italic">본문 미작성</p>
          </div>

          <!-- 3열: 댓글·대댓글 -->
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
                  <span class="reply-arrow">↩</span>
                  <span v-if="cmt.reply" class="reply-text">{{ cmt.reply }}</span>
                  <span v-else class="cmt-empty">—</span>
                </div>
              </div>
            </template>
            <span v-else class="text-[11px] text-slate-300">댓글 없음</span>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
/* 행 */
.article-row {
  display: grid;
  grid-template-columns: 52px minmax(0, 480px) 1fr;
  border-bottom: 1px solid #e2e8f0;
  background: white;
  transition: background-color 0.15s;
}
.row-even {
  background-color: #fafbfc;
}
.article-row:hover {
  background-color: #eff6ff;
}

/* 1열: 순번+상태 */
.col-num {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 8px 4px;
  border-right: 1px solid #f1f5f9;
}
.order-num {
  font-family: ui-monospace, monospace;
  font-size: 12px;
  color: #94a3b8;
  font-weight: 700;
}
.status-badge {
  font-size: 8px;
  font-weight: 700;
  color: white;
  padding: 1px 4px;
  border-radius: 3px;
  white-space: nowrap;
  text-align: center;
  line-height: 1.4;
}

/* 2열: 제목+본문 */
.col-content {
  padding: 8px 10px;
  border-right: 1px solid #f1f5f9;
  min-width: 0;
}
.content-header {
  display: flex;
  align-items: center;
  gap: 5px;
  margin-bottom: 4px;
}
.equip-tag {
  font-size: 9px;
  color: #2563eb;
  background: #eff6ff;
  padding: 1px 5px;
  border-radius: 3px;
  font-weight: 500;
  white-space: nowrap;
  flex-shrink: 0;
}
.title-text {
  font-size: 12px;
  font-weight: 600;
  color: #1e293b;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  min-width: 0;
}
.link-icon {
  font-size: 10px;
  color: #60a5fa;
  flex-shrink: 0;
}
.link-icon:hover { color: #2563eb; }
.edit-btn {
  color: #94a3b8;
  transition: color 0.15s;
  padding: 2px;
  border-radius: 3px;
  flex-shrink: 0;
}
.edit-btn:hover {
  color: #3b82f6;
  background: #eff6ff;
}
.body-text {
  font-size: 11px;
  color: #475569;
  line-height: 1.6;
  white-space: pre-line;
  display: -webkit-box;
  -webkit-line-clamp: 8;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* 3열: 댓글 */
.col-comments {
  padding: 8px 10px;
  min-width: 0;
  overflow: hidden;
}
.comment-pair {
  margin-bottom: 6px;
  padding-bottom: 6px;
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
  padding-left: 18px;
  margin-top: 2px;
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
.reply-arrow {
  flex-shrink: 0;
  color: #94a3b8;
  font-size: 11px;
  width: 14px;
}
.cmt-text { color: #334155; }
.reply-text { color: #64748b; }
.cmt-empty { color: #cbd5e1; }
</style>

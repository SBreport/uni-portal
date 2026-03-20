<script setup lang="ts">
import { ref, watch, computed, onMounted } from 'vue'
import { useCafeStore, type ArticleDetail } from '@/stores/cafe'
import { useAuthStore } from '@/stores/auth'
import * as cafeApi from '@/api/cafe'

const props = defineProps<{ articleId: number | null }>()
const emit = defineEmits<{ back: [] }>()

const store = useCafeStore()
const auth = useAuthStore()

// 폼 상태
const title = ref('')
const body = ref('')
const keyword = ref('')
const category = ref('')
const equipmentName = ref('')
const publishedUrl = ref('')
const comments = ref<{ comment_text: string; reply_text: string }[]>([])
const newStatus = ref('')
const statusNote = ref('')
const feedbackText = ref('')
const saving = ref(false)
const copied = ref('')

const statusColors: Record<string, string> = {
  '작성대기': '#6B7280', '작성완료': '#F59E0B', '수정요청': '#EF4444',
  '검수완료': '#3B82F6', '발행완료': '#10B981', '보류': '#8B5CF6',
}
const statuses = ['작성대기', '작성완료', '수정요청', '검수완료', '발행완료', '보류']

const article = computed(() => store.currentArticle)

// 이전/다음 글 이동
const prevArticle = computed(() => {
  const idx = store.articles.findIndex(a => a.id === props.articleId)
  return idx > 0 ? store.articles[idx - 1] : null
})
const nextArticle = computed(() => {
  const idx = store.articles.findIndex(a => a.id === props.articleId)
  return idx >= 0 && idx < store.articles.length - 1 ? store.articles[idx + 1] : null
})

function navigateTo(id: number) {
  // 부모에게 알리지 않고 직접 로드
  loadArticle(id)
}

async function loadArticle(id: number) {
  await store.loadArticleDetail(id)
  if (store.currentArticle) {
    const a = store.currentArticle
    title.value = a.title || ''
    body.value = a.body || ''
    keyword.value = a.keyword || ''
    category.value = a.category || ''
    equipmentName.value = a.equipment_name || ''
    publishedUrl.value = a.published_url || ''
    newStatus.value = a.status
    // 댓글 (최소 3개 슬롯)
    const cmts = a.comments || []
    comments.value = []
    for (let i = 1; i <= Math.max(3, cmts.length); i++) {
      const c = cmts.find(x => x.slot_number === i)
      comments.value.push({
        comment_text: c?.comment_text || '',
        reply_text: c?.reply_text || '',
      })
    }
  }
}

watch(() => props.articleId, (id) => { if (id) loadArticle(id) }, { immediate: true })

// 댓글 추가
function addCommentSlot() {
  comments.value.push({ comment_text: '', reply_text: '' })
}

// 저장
async function save() {
  if (!article.value) return
  saving.value = true
  try {
    await cafeApi.updateArticle(article.value.id, {
      title: title.value,
      body: body.value,
      keyword: keyword.value,
      category: category.value,
      equipment_name: equipmentName.value,
    })
    // 댓글 저장
    for (let i = 0; i < comments.value.length; i++) {
      const c = comments.value[i]!
      if (c.comment_text || c.reply_text) {
        await cafeApi.upsertComment(article.value.id, i + 1, c.comment_text, c.reply_text)
      }
    }
    // 발행 URL
    if (publishedUrl.value && publishedUrl.value !== article.value.published_url) {
      await cafeApi.publishArticle(article.value.id, publishedUrl.value, auth.username)
    }
    await loadArticle(article.value.id)
    await store.loadArticles()
  } finally {
    saving.value = false
  }
}

// 상태 변경
async function handleStatusChange() {
  if (!article.value || newStatus.value === article.value.status) return
  await cafeApi.changeStatus(article.value.id, newStatus.value, auth.username, statusNote.value)
  statusNote.value = ''
  await loadArticle(article.value.id)
  await store.loadArticles()
}

// 피드백 등록
async function submitFeedback() {
  if (!article.value || !feedbackText.value.trim()) return
  await cafeApi.addFeedback(article.value.id, auth.username, feedbackText.value)
  feedbackText.value = ''
  await loadArticle(article.value.id)
}

// 복사
async function copyText(text: string, label: string) {
  await navigator.clipboard.writeText(text)
  copied.value = label
  setTimeout(() => copied.value = '', 1500)
}
</script>

<template>
  <div v-if="!article" class="text-sm text-slate-400 p-4">
    원고 목록에서 항목을 선택해주세요.
  </div>

  <div v-else>
    <!-- Row 1: 네비게이션 (3컬럼 — 1칸만 사용) -->
    <div class="grid grid-cols-3 gap-4 mb-3">
      <div class="flex items-center gap-2">
        <button v-if="prevArticle" @click="navigateTo(prevArticle!.id)"
          class="px-2 py-1 text-xs border border-slate-200 rounded hover:bg-slate-50">
          ◀ #{{ prevArticle!.article_order }}
        </button>
        <span class="text-sm font-bold text-slate-800 truncate">
          #{{ article.article_order }} {{ article.title || '(제목 없음)' }}
        </span>
        <button v-if="nextArticle" @click="navigateTo(nextArticle!.id)"
          class="px-2 py-1 text-xs border border-slate-200 rounded hover:bg-slate-50">
          #{{ nextArticle!.article_order }} ▶
        </button>
      </div>
      <div></div>
      <div></div>
    </div>

    <!-- Row 2: 메타 정보 (3컬럼) -->
    <div class="grid grid-cols-3 gap-4 mb-4">
      <!-- 키워드/카테/장비 -->
      <div class="flex gap-2">
        <input v-model="keyword" placeholder="키워드"
          class="flex-1 px-2 py-1 border border-slate-200 rounded text-xs" />
        <input v-model="category" placeholder="카테고리"
          class="w-20 px-2 py-1 border border-slate-200 rounded text-xs" />
        <input v-model="equipmentName" placeholder="장비"
          class="flex-1 px-2 py-1 border border-slate-200 rounded text-xs" />
      </div>
      <!-- 상태 변경 -->
      <div class="flex items-center gap-2">
        <span class="text-xs px-2 py-0.5 rounded text-white font-semibold"
          :style="{ backgroundColor: statusColors[article.status] }">
          {{ article.status }}
        </span>
        <select v-model="newStatus" class="text-xs border border-slate-200 rounded px-2 py-1">
          <option v-for="s in statuses" :key="s" :value="s">{{ s }}</option>
        </select>
        <button @click="handleStatusChange"
          class="text-xs px-2 py-1 bg-slate-100 rounded hover:bg-slate-200">변경</button>
      </div>
      <!-- 발행 URL + 저장 -->
      <div class="flex items-center gap-2">
        <input v-model="publishedUrl" placeholder="https://cafe.naver.com/..."
          class="flex-1 px-2 py-1 border border-slate-200 rounded text-xs" />
        <button @click="save" :disabled="saving"
          class="px-3 py-1 bg-blue-600 text-white text-xs rounded hover:bg-blue-700 disabled:opacity-50 font-semibold">
          {{ saving ? '...' : '저장' }}
        </button>
      </div>
    </div>

    <!-- Row 3: 본문 / 댓글 / 피드백 (3컬럼) -->
    <div class="grid grid-cols-3 gap-4" style="min-height: 500px;">
      <!-- Col 1: 제목 + 본문 -->
      <div class="flex flex-col gap-2">
        <div class="flex items-center gap-1">
          <label class="text-xs font-medium text-slate-500">제목</label>
          <button @click="copyText(title, '제목')" class="text-slate-300 hover:text-slate-500" title="복사">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
            </svg>
          </button>
          <span v-if="copied === '제목'" class="text-[10px] text-emerald-500">복사됨</span>
        </div>
        <input v-model="title"
          class="w-full px-3 py-2 border border-slate-200 rounded text-sm" />

        <div class="flex items-center gap-1 mt-2">
          <label class="text-xs font-medium text-slate-500">본문</label>
          <button @click="copyText(body, '본문')" class="text-slate-300 hover:text-slate-500" title="복사">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
            </svg>
          </button>
          <span v-if="copied === '본문'" class="text-[10px] text-emerald-500">복사됨</span>
        </div>
        <textarea v-model="body"
          class="w-full flex-1 px-3 py-2 border border-slate-200 rounded text-sm leading-7"
          style="min-height: 400px; max-width: 420px; font-size: 14px;"
        />
      </div>

      <!-- Col 2: 댓글/대댓글 -->
      <div class="flex flex-col gap-2">
        <div class="flex items-center justify-between">
          <label class="text-xs font-medium text-slate-500">댓글 ({{ comments.length }})</label>
          <button @click="addCommentSlot"
            class="text-xs px-2 py-0.5 border border-slate-200 rounded hover:bg-slate-50">
            + 추가
          </button>
        </div>

        <div v-for="(c, i) in comments" :key="i" class="border border-slate-100 rounded p-2 space-y-1">
          <div class="flex items-center gap-1">
            <span class="text-[10px] text-slate-400">💬 댓글 {{ i + 1 }}</span>
            <button @click="copyText(c.comment_text, `댓${i+1}`)"
              class="text-slate-300 hover:text-slate-500" title="복사">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
              </svg>
            </button>
          </div>
          <textarea v-model="c.comment_text" rows="2"
            class="w-full px-2 py-1 border border-slate-100 rounded text-xs" />

          <div class="flex items-center gap-1">
            <span class="text-[10px] text-slate-400">↳ 대댓글 {{ i + 1 }}</span>
            <button @click="copyText(c.reply_text, `대${i+1}`)"
              class="text-slate-300 hover:text-slate-500" title="복사">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
              </svg>
            </button>
          </div>
          <textarea v-model="c.reply_text" rows="2"
            class="w-full px-2 py-1 border border-slate-100 rounded text-xs" />
        </div>
      </div>

      <!-- Col 3: 피드백 -->
      <div class="flex flex-col gap-3">
        <label class="text-xs font-medium text-slate-500">📋 피드백</label>

        <!-- 피드백 이력 -->
        <div class="flex-1 overflow-y-auto space-y-2 max-h-[300px]">
          <div v-if="!article.feedbacks?.length" class="text-xs text-slate-300">피드백 없음</div>
          <div v-for="fb in article.feedbacks" :key="fb.id"
            class="border border-slate-100 rounded p-2">
            <p class="text-xs text-slate-800">{{ fb.content }}</p>
            <p class="text-[10px] text-slate-400 mt-1">{{ fb.author }} · {{ fb.created_at }}</p>
          </div>
        </div>

        <!-- 피드백 입력 -->
        <textarea v-model="feedbackText" rows="3"
          placeholder="수정 요청이나 승인 의견을 입력하세요"
          class="w-full px-3 py-2 border border-slate-200 rounded text-sm" />
        <button @click="submitFeedback"
          class="w-full py-2 border border-slate-200 rounded text-sm hover:bg-slate-50 transition">
          피드백 등록
        </button>

        <!-- 상태 변경 이력 -->
        <details class="mt-2">
          <summary class="text-xs text-slate-400 cursor-pointer">상태 변경 이력</summary>
          <div class="mt-1 text-xs text-slate-500 space-y-1" v-if="article.feedbacks">
            <p class="text-slate-300">별도 API 연동 예정</p>
          </div>
        </details>
      </div>
    </div>
  </div>
</template>

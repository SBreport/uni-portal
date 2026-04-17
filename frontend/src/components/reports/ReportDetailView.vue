<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { getWeeklyReport, updateWeeklyReport, deleteWeeklyReport, uploadReportImage, deleteReportImage } from '@/api/reports'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import { mergeReportData, createEmptyReportData, type ReportData } from './reportSchema'
import { parseWeeklyReportText } from './parseWeeklyReportText'

// ── props ──
const props = defineProps<{ weekStart: string }>()

const router = useRouter()
const auth = useAuthStore()
const canEdit = computed(() => ['admin', 'editor'].includes(auth.role))
const isAdmin = computed(() => auth.role === 'admin')

// ── 상태 ──
const loading = ref(true)
const loadError = ref('')
const tab = ref<'write' | 'result'>('write')

// 보고서 데이터
const title = ref('')
const data = ref<ReportData>(createEmptyReportData())
let weekEnd = ''

// 접기
const collapsed = ref<Record<string, boolean>>({
  blogDistribution: false,
  place: false,
  website: false,
  blogExposure: false,
  related: false,
})

// 저장 상태
type SaveState = 'idle' | 'saving' | 'saved' | 'error'
const saveState = ref<SaveState>('idle')
const lastSavedAt = ref<Date | null>(null)
const lastSavedLabel = ref('')

// 자동저장 트리거 플래그
let watchActive = false

// ── 날짜 유틸 ──
function formatPeriod(start: string, end: string): string {
  const fmt = (s: string) => s.replace(/-/g, '.').slice(0, 10)
  return `${fmt(start)} – ${fmt(end)}`
}

function calcWeekEnd(start: string): string {
  const d = new Date(start)
  d.setDate(d.getDate() + 6)
  return d.toISOString().slice(0, 10)
}

const periodLabel = computed(() =>
  weekEnd ? formatPeriod(props.weekStart, weekEnd) : ''
)

// ── 저장 경과 시간 라벨 ──
function updateSavedLabel() {
  if (!lastSavedAt.value) return
  const diff = Math.floor((Date.now() - lastSavedAt.value.getTime()) / 1000)
  if (diff < 10) lastSavedLabel.value = '방금 저장됨'
  else if (diff < 60) lastSavedLabel.value = `저장됨 · ${diff}초 전`
  else lastSavedLabel.value = `저장됨 · ${Math.floor(diff / 60)}분 전`
}

let labelTimer: ReturnType<typeof setInterval> | null = null

// ── debounce ──
function createDebouncer<T extends (...args: any[]) => any>(fn: T, ms: number) {
  let timer: ReturnType<typeof setTimeout> | undefined
  return (...args: Parameters<T>) => {
    if (timer) clearTimeout(timer)
    timer = setTimeout(() => fn(...args), ms)
  }
}

// ── 저장 ──
async function save() {
  if (!canEdit.value) return
  saveState.value = 'saving'
  try {
    await updateWeeklyReport(props.weekStart, {
      title: title.value,
      data: data.value,
    })
    saveState.value = 'saved'
    lastSavedAt.value = new Date()
    updateSavedLabel()
  } catch {
    saveState.value = 'error'
  }
}

const debouncedSave = createDebouncer(save, 1500)

// ── 로드 ──
async function loadReport() {
  loading.value = true
  loadError.value = ''
  watchActive = false
  try {
    const res = await getWeeklyReport(props.weekStart)
    title.value = res.data.title ?? ''
    weekEnd = res.data.week_end ?? calcWeekEnd(props.weekStart)
    data.value = mergeReportData(res.data.data ?? {})
  } catch (e: any) {
    loadError.value = e.response?.data?.detail || '보고서를 불러오지 못했습니다.'
  } finally {
    loading.value = false
    // 한 tick 후 watch 활성화 (초기 세팅이 트리거하지 않도록)
    setTimeout(() => { watchActive = true }, 50)
  }
}

// ── watch: 자동저장 ──
watch(
  () => ({ t: title.value, d: JSON.stringify(data.value) }),
  () => {
    if (!watchActive) return
    debouncedSave()
  },
  { deep: false }
)

// 저장 경과 라벨 갱신 타이머
onMounted(() => {
  loadReport()
  labelTimer = setInterval(updateSavedLabel, 15000)
})

import { onUnmounted } from 'vue'
onUnmounted(() => {
  if (labelTimer) clearInterval(labelTimer)
})

// ── 삭제 ──
async function handleDelete() {
  if (!confirm('이 보고서를 삭제하시겠습니까? 복구할 수 없습니다.')) return
  try {
    await deleteWeeklyReport(props.weekStart)
    router.push('/reports')
  } catch (e: any) {
    alert(e.response?.data?.detail || '삭제 실패')
  }
}

// ── 불러오기 모달 ──
const showImportModal = ref(false)
const importText = ref('')

function openImportModal() {
  importText.value = ''
  showImportModal.value = true
}

async function onFileSelected(e: Event) {
  const target = e.target as HTMLInputElement
  const file = target.files?.[0]
  if (!file) return
  importText.value = await file.text()
}

function applyImport() {
  if (!importText.value.trim()) return
  if (!confirm('현재 섹션 내용이 불러온 값으로 덮어써집니다. 계속하시겠습니까?')) return

  const parsed = parseWeeklyReportText(importText.value)
  const empty = createEmptyReportData()

  // 파서가 반환한 섹션은 empty 기반 완전 교체, 없는 섹션은 기존 유지
  // basic.notice 는 절대 건드리지 않음
  data.value = {
    basic: { ...data.value.basic },
    blogDistribution: parsed.blogDistribution
      ? { ...empty.blogDistribution, ...parsed.blogDistribution }
      : data.value.blogDistribution,
    place: parsed.place
      ? { ...empty.place, ...parsed.place }
      : data.value.place,
    website: parsed.website
      ? { ...empty.website, ...parsed.website }
      : data.value.website,
    blogExposure: parsed.blogExposure
      ? { ...empty.blogExposure, ...parsed.blogExposure }
      : data.value.blogExposure,
    related: parsed.related
      ? { ...empty.related, ...parsed.related }
      : data.value.related,
  }

  showImportModal.value = false
  // watch 가 data 변경을 감지해 자동저장 트리거
}

// ── 섹션 네비 스크롤 ──
const sectionRefs = ref<Record<string, HTMLElement | null>>({})

function scrollTo(key: string) {
  sectionRefs.value[key]?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

const navItems = [
  { key: 'blogDistribution', label: '01 블로그배포' },
  { key: 'place', label: '02 플레이스' },
  { key: 'website', label: '03 웹사이트' },
  { key: 'blogExposure', label: '04 블로그 상위노출' },
  { key: 'related', label: '05 함께찾는' },
]

// ── 공통 클래스 ──
const inputCls = 'w-full text-xs border border-slate-200 rounded px-2 py-1.5 focus:outline-none focus:ring-1 focus:ring-blue-400 bg-white disabled:bg-slate-50 disabled:text-slate-400'
const textareaCls = 'w-full text-xs border border-slate-200 rounded px-2 py-1.5 focus:outline-none focus:ring-1 focus:ring-blue-400 resize-y bg-white disabled:bg-slate-50 disabled:text-slate-400'

// ── 결과 탭 ──
const resultSectionRefs = ref<Record<string, HTMLElement | null>>({})

function scrollToResult(key: string) {
  resultSectionRefs.value[key]?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

const resultNavItems = [
  { key: 'blogDistribution', label: '01 블로그배포' },
  { key: 'place', label: '02 플레이스' },
  { key: 'website', label: '03 웹사이트' },
  { key: 'blogExposure', label: '04 블로그 상위노출' },
  { key: 'related', label: '05 함께찾는' },
]

interface Kpi { key: string; label: string; value: string }
const kpis = computed<Kpi[]>(() => {
  const fmt = (a: string, b: string) => (a && b ? `${a} / ${b}` : '—')
  return [
    { key: 'blog',     label: '블로그배포', value: fmt(data.value.blogDistribution.ranked,  data.value.blogDistribution.keywords) },
    { key: 'place',    label: '플레이스',   value: fmt(data.value.place.occupied,           data.value.place.total) },
    { key: 'website',  label: '웹사이트',   value: fmt(data.value.website.visible,          data.value.website.total) },
    { key: 'exposure', label: '블로그노출', value: fmt(data.value.blogExposure.visible,      data.value.blogExposure.total) },
    { key: 'related',  label: '함께찾는',   value: fmt(data.value.related.created,          data.value.related.total) },
  ]
})

const generatedAtLabel = computed(() => {
  const now = new Date()
  const fmt = (n: number) => String(n).padStart(2, '0')
  return `${now.getFullYear()}.${fmt(now.getMonth() + 1)}.${fmt(now.getDate())} ${fmt(now.getHours())}:${fmt(now.getMinutes())}`
})

// ── 이미지 업로드 ──────────────────────────────────────────────────────────────
const uploadingFor = ref<string | null>(null)

async function onPaste(e: ClipboardEvent, section: keyof ReportData) {
  if (!canEdit.value) return
  const items = e.clipboardData?.items
  if (!items) return
  for (let i = 0; i < items.length; i++) {
    const item = items[i]
    if (item.type.startsWith('image/')) {
      e.preventDefault()
      const file = item.getAsFile()
      if (!file) return
      await handleUpload(file, section as string)
      break
    }
  }
}

async function handleUpload(file: File, section: string) {
  uploadingFor.value = section
  try {
    const { data: res } = await uploadReportImage(props.weekStart, section, file)
    const sec = (data.value as any)[section]
    if (Array.isArray(sec.images)) {
      sec.images.push(res.path)
    }
    // data.value 변경은 watch가 감지해 자동저장 트리거
  } catch (e: any) {
    alert(e.response?.data?.detail || '이미지 업로드 실패')
  } finally {
    uploadingFor.value = null
  }
}

async function removeImage(section: string, idx: number) {
  if (!canEdit.value) return
  const sec = (data.value as any)[section]
  if (!sec?.images?.[idx]) return
  const path = sec.images[idx]
  if (!confirm('이미지를 삭제하시겠습니까?')) return
  try {
    await deleteReportImage(props.weekStart, path)
    sec.images.splice(idx, 1)
  } catch (e: any) {
    alert(e.response?.data?.detail || '삭제 실패')
  }
}

function resolveImageUrl(path: string): string {
  return `/uploads/${path}`
}

function openImagePreview(path: string) {
  window.open(resolveImageUrl(path), '_blank', 'noopener')
}
</script>

<template>
  <div class="flex flex-col overflow-hidden" style="height: calc(100vh - 48px)">

    <!-- ── 상단바 ── -->
    <div class="shrink-0 border-b border-slate-200 bg-white">
      <!-- 1행: 목록 / 제목 / 탭 / 저장상태 / 삭제 -->
      <div class="flex items-center gap-2 px-3 py-2">
        <!-- 목록 -->
        <button
          @click="router.push('/reports')"
          class="flex items-center gap-1 text-xs text-slate-500 hover:text-slate-800 shrink-0"
        >
          &#8592; 목록
        </button>

        <span class="text-slate-200 select-none">|</span>

        <!-- 제목 인라인 편집 -->
        <input
          v-model="title"
          :disabled="!canEdit"
          placeholder="보고서 제목"
          class="flex-1 min-w-0 text-sm font-semibold text-slate-800 border-0 outline-none bg-transparent placeholder:text-slate-300 disabled:text-slate-600"
        />

        <!-- 탭 -->
        <div class="flex items-center gap-0.5 shrink-0 border border-slate-200 rounded overflow-hidden">
          <button
            @click="tab = 'write'"
            class="px-2.5 py-1 text-xs transition-colors"
            :class="tab === 'write' ? 'bg-slate-800 text-white' : 'text-slate-500 hover:bg-slate-50'"
          >작성</button>
          <button
            @click="tab = 'result'"
            class="px-2.5 py-1 text-xs transition-colors"
            :class="tab === 'result' ? 'bg-slate-800 text-white' : 'text-slate-500 hover:bg-slate-50'"
          >결과</button>
        </div>

        <!-- 저장 상태 -->
        <span class="text-[10px] shrink-0 tabular-nums" :class="{
          'text-slate-400': saveState === 'idle' || saveState === 'saved',
          'text-blue-500': saveState === 'saving',
          'text-red-500': saveState === 'error',
        }">
          <template v-if="saveState === 'saving'">저장 중...</template>
          <template v-else-if="saveState === 'error'">저장 실패</template>
          <template v-else-if="saveState === 'saved'">{{ lastSavedLabel }}</template>
        </span>

        <!-- 불러오기 (editor 이상, 작성 탭일 때) -->
        <button
          v-if="canEdit && tab === 'write'"
          @click="openImportModal"
          class="text-[10px] text-slate-500 hover:text-slate-800 shrink-0 px-2 py-1 rounded border border-slate-200 hover:bg-slate-50"
        >불러오기</button>

        <!-- 삭제 (admin) -->
        <button
          v-if="isAdmin"
          @click="handleDelete"
          class="text-[10px] text-red-400 hover:text-red-600 shrink-0 px-1.5 py-1 rounded hover:bg-red-50"
        >삭제</button>
      </div>

      <!-- 2행: 기간 + 안내 -->
      <div class="px-3 pb-1.5 flex items-center gap-2 text-[10px]">
        <span v-if="periodLabel" class="text-slate-400 tabular-nums shrink-0">
          기간: {{ periodLabel }}
        </span>
        <span v-if="periodLabel" class="text-slate-200">·</span>
        <label class="flex items-center gap-1 flex-1 min-w-0">
          <span class="text-slate-400 shrink-0">안내:</span>
          <input
            v-model="data.basic.notice"
            :disabled="!canEdit"
            placeholder="공통 안내 문구"
            class="flex-1 min-w-0 border-0 outline-none bg-transparent text-slate-500 placeholder:text-slate-300 disabled:text-slate-400"
          />
        </label>
      </div>
    </div>

    <!-- ── 로딩 ── -->
    <div v-if="loading" class="flex-1 flex items-center justify-center">
      <LoadingSpinner message="보고서 불러오는 중..." />
    </div>

    <!-- ── 에러 ── -->
    <div v-else-if="loadError" class="flex-1 flex items-center justify-center">
      <div class="text-center">
        <p class="text-sm text-red-600 mb-2">{{ loadError }}</p>
        <button @click="loadReport" class="text-xs px-3 py-1.5 border border-slate-300 rounded hover:bg-slate-50">
          다시 시도
        </button>
      </div>
    </div>

    <!-- ── 본문 ── -->
    <div v-else class="flex-1 overflow-hidden bg-slate-50">

      <!-- 작성 탭 -->
      <div v-if="tab === 'write'" class="flex h-full">

        <!-- 왼쪽 네비 (고정) -->
        <nav class="w-36 shrink-0 border-r border-slate-200 bg-white overflow-y-auto py-3 px-2 space-y-0.5">
          <button
            v-for="item in navItems"
            :key="item.key"
            @click="scrollTo(item.key)"
            class="w-full text-left text-xs px-2 py-1.5 rounded transition-colors text-slate-600 hover:bg-slate-50 hover:text-slate-900"
          >
            {{ item.label }}
          </button>
        </nav>

        <!-- 오른쪽 컨텐츠 (스크롤) -->
        <div class="flex-1 overflow-y-auto">
          <div class="py-3 pr-4 pl-4 space-y-3 max-w-3xl">

          <!-- ─── 01 블로그배포 ─── -->
          <section
            :ref="(el) => { sectionRefs['blogDistribution'] = el as HTMLElement }"
            class="bg-white border border-slate-200 rounded-lg overflow-hidden"
          >
            <div class="flex items-center justify-between px-4 py-2.5 border-b border-slate-100">
              <span class="text-xs font-semibold text-slate-700">01 블로그배포</span>
              <button
                @click="collapsed.blogDistribution = !collapsed.blogDistribution"
                class="text-[10px] text-slate-400 hover:text-slate-600 px-1"
              >{{ collapsed.blogDistribution ? '▶' : '▼' }}</button>
            </div>
            <div v-show="!collapsed.blogDistribution" class="p-4 space-y-3">
              <!-- 지표 3개 -->
              <div class="grid grid-cols-3 gap-2">
                <div>
                  <label class="block text-[10px] text-slate-500 mb-1">누적 발행 글 수</label>
                  <input v-model="data.blogDistribution.posts" :disabled="!canEdit" type="text" placeholder="0" :class="inputCls" />
                </div>
                <div>
                  <label class="block text-[10px] text-slate-500 mb-1">금일 상위노출 지점 수</label>
                  <input v-model="data.blogDistribution.ranked" :disabled="!canEdit" type="text" placeholder="0" :class="inputCls" />
                </div>
                <div>
                  <label class="block text-[10px] text-slate-500 mb-1">타겟 키워드 수</label>
                  <input v-model="data.blogDistribution.keywords" :disabled="!canEdit" type="text" placeholder="0" :class="inputCls" />
                </div>
              </div>
              <!-- 대응 -->
              <div>
                <label class="block text-[10px] text-slate-500 mb-1">대응 중인 내용</label>
                <textarea v-model="data.blogDistribution.response" :disabled="!canEdit" rows="2" :class="textareaCls" />
              </div>
              <!-- 상태 설명 -->
              <div>
                <label class="block text-[10px] text-slate-500 mb-1">상태 설명</label>
                <textarea v-model="data.blogDistribution.summary" :disabled="!canEdit" rows="2" :class="textareaCls" />
              </div>
              <!-- 링크 -->
              <div class="grid grid-cols-2 gap-2">
                <div>
                  <label class="block text-[10px] text-slate-500 mb-1">원본 링크 1</label>
                  <input v-model="data.blogDistribution.link1" :disabled="!canEdit" type="text" placeholder="https://" :class="inputCls" />
                </div>
                <div>
                  <label class="block text-[10px] text-slate-500 mb-1">원본 링크 2</label>
                  <input v-model="data.blogDistribution.link2" :disabled="!canEdit" type="text" placeholder="https://" :class="inputCls" />
                </div>
              </div>
              <!-- 이미지 -->
              <div class="border-t border-slate-100 pt-3">
                <label class="block text-[10px] text-slate-500 mb-1.5">첨부 이미지</label>
                <div
                  v-if="canEdit"
                  tabindex="0"
                  @paste="(e) => onPaste(e, 'blogDistribution')"
                  class="border-2 border-dashed border-slate-200 rounded px-3 py-2 text-[10px] text-slate-400 text-center hover:bg-slate-50 focus:outline-none focus:border-blue-300 focus:bg-blue-50/30 cursor-text mb-2"
                  :class="{ 'opacity-60': uploadingFor === 'blogDistribution' }"
                >{{ uploadingFor === 'blogDistribution' ? '업로드 중...' : '여기를 클릭 후 Ctrl+V 로 이미지 붙여넣기' }}</div>
                <div v-if="data.blogDistribution.images.length > 0" class="grid grid-cols-4 gap-1.5">
                  <div v-for="(img, i) in data.blogDistribution.images" :key="img" class="relative group">
                    <img :src="resolveImageUrl(img)" class="w-full h-16 object-cover rounded border border-slate-200 cursor-pointer" @click="openImagePreview(img)" />
                    <button v-if="canEdit" @click="removeImage('blogDistribution', i)" class="absolute top-0.5 right-0.5 w-4 h-4 bg-black/60 text-white rounded-full flex items-center justify-center text-[10px] opacity-0 group-hover:opacity-100 transition-opacity">&#x2715;</button>
                  </div>
                </div>
                <div v-else class="text-[10px] text-slate-300 text-center py-1">첨부된 이미지 없음</div>
              </div>
            </div>
          </section>

          <!-- ─── 02 플레이스 ─── -->
          <section
            :ref="(el) => { sectionRefs['place'] = el as HTMLElement }"
            class="bg-white border border-slate-200 rounded-lg overflow-hidden"
          >
            <div class="flex items-center justify-between px-4 py-2.5 border-b border-slate-100">
              <span class="text-xs font-semibold text-slate-700">02 플레이스</span>
              <button
                @click="collapsed.place = !collapsed.place"
                class="text-[10px] text-slate-400 hover:text-slate-600 px-1"
              >{{ collapsed.place ? '▶' : '▼' }}</button>
            </div>
            <div v-show="!collapsed.place" class="p-4 space-y-3">
              <!-- 지표 4개 -->
              <div class="grid grid-cols-4 gap-2">
                <div>
                  <label class="block text-[10px] text-slate-500 mb-1">총 지점 수</label>
                  <input v-model="data.place.total" :disabled="!canEdit" type="text" placeholder="0" :class="inputCls" />
                </div>
                <div>
                  <label class="block text-[10px] text-slate-500 mb-1">점유 지점 수</label>
                  <input v-model="data.place.occupied" :disabled="!canEdit" type="text" placeholder="0" :class="inputCls" />
                </div>
                <div>
                  <label class="block text-[10px] text-slate-500 mb-1">이탈 지점 수</label>
                  <input v-model="data.place.dropped" :disabled="!canEdit" type="text" placeholder="0" :class="inputCls" />
                </div>
                <div>
                  <label class="block text-[10px] text-slate-500 mb-1">휴식 지점 수</label>
                  <input v-model="data.place.paused" :disabled="!canEdit" type="text" placeholder="0" :class="inputCls" />
                </div>
              </div>
              <!-- 대응 -->
              <div>
                <label class="block text-[10px] text-slate-500 mb-1">대응 중인 내용</label>
                <textarea v-model="data.place.response" :disabled="!canEdit" rows="2" :class="textareaCls" />
              </div>
              <!-- 상태 설명 -->
              <div>
                <label class="block text-[10px] text-slate-500 mb-1">상태 설명</label>
                <textarea v-model="data.place.summary" :disabled="!canEdit" rows="2" :class="textareaCls" />
              </div>
              <!-- 목록 텍스트 영역 -->
              <div class="grid grid-cols-2 gap-2">
                <div>
                  <label class="block text-[10px] text-slate-500 mb-1">이탈 지점 목록</label>
                  <textarea v-model="data.place.droppedList" :disabled="!canEdit" rows="3" :class="textareaCls" />
                </div>
                <div>
                  <label class="block text-[10px] text-slate-500 mb-1">신규 지점 목록</label>
                  <textarea v-model="data.place.newList" :disabled="!canEdit" rows="3" :class="textareaCls" />
                </div>
              </div>
              <div class="grid grid-cols-2 gap-2">
                <div>
                  <label class="block text-[10px] text-slate-500 mb-1">휴식 지점 목록</label>
                  <textarea v-model="data.place.pausedList" :disabled="!canEdit" rows="3" :class="textareaCls" />
                </div>
                <div>
                  <label class="block text-[10px] text-slate-500 mb-1">작업 코멘트</label>
                  <textarea v-model="data.place.comment" :disabled="!canEdit" rows="3" :class="textareaCls" />
                </div>
              </div>
              <!-- 링크 -->
              <div>
                <label class="block text-[10px] text-slate-500 mb-1">원본 링크</label>
                <input v-model="data.place.link" :disabled="!canEdit" type="text" placeholder="https://" :class="inputCls" />
              </div>
              <!-- 이미지 -->
              <div class="border-t border-slate-100 pt-3">
                <label class="block text-[10px] text-slate-500 mb-1.5">첨부 이미지</label>
                <div
                  v-if="canEdit"
                  tabindex="0"
                  @paste="(e) => onPaste(e, 'place')"
                  class="border-2 border-dashed border-slate-200 rounded px-3 py-2 text-[10px] text-slate-400 text-center hover:bg-slate-50 focus:outline-none focus:border-blue-300 focus:bg-blue-50/30 cursor-text mb-2"
                  :class="{ 'opacity-60': uploadingFor === 'place' }"
                >{{ uploadingFor === 'place' ? '업로드 중...' : '여기를 클릭 후 Ctrl+V 로 이미지 붙여넣기' }}</div>
                <div v-if="data.place.images.length > 0" class="grid grid-cols-4 gap-1.5">
                  <div v-for="(img, i) in data.place.images" :key="img" class="relative group">
                    <img :src="resolveImageUrl(img)" class="w-full h-16 object-cover rounded border border-slate-200 cursor-pointer" @click="openImagePreview(img)" />
                    <button v-if="canEdit" @click="removeImage('place', i)" class="absolute top-0.5 right-0.5 w-4 h-4 bg-black/60 text-white rounded-full flex items-center justify-center text-[10px] opacity-0 group-hover:opacity-100 transition-opacity">&#x2715;</button>
                  </div>
                </div>
                <div v-else class="text-[10px] text-slate-300 text-center py-1">첨부된 이미지 없음</div>
              </div>
            </div>
          </section>

          <!-- ─── 03 웹사이트 ─── -->
          <section
            :ref="(el) => { sectionRefs['website'] = el as HTMLElement }"
            class="bg-white border border-slate-200 rounded-lg overflow-hidden"
          >
            <div class="flex items-center justify-between px-4 py-2.5 border-b border-slate-100">
              <span class="text-xs font-semibold text-slate-700">03 웹사이트</span>
              <button
                @click="collapsed.website = !collapsed.website"
                class="text-[10px] text-slate-400 hover:text-slate-600 px-1"
              >{{ collapsed.website ? '▶' : '▼' }}</button>
            </div>
            <div v-show="!collapsed.website" class="p-4 space-y-3">
              <!-- 지표 4개 -->
              <div class="grid grid-cols-4 gap-2">
                <div>
                  <label class="block text-[10px] text-slate-500 mb-1">총 키워드 수</label>
                  <input v-model="data.website.total" :disabled="!canEdit" type="text" placeholder="0" :class="inputCls" />
                </div>
                <div>
                  <label class="block text-[10px] text-slate-500 mb-1">노출 지점 수</label>
                  <input v-model="data.website.visible" :disabled="!canEdit" type="text" placeholder="0" :class="inputCls" />
                </div>
                <div>
                  <label class="block text-[10px] text-slate-500 mb-1">이탈 지점 수</label>
                  <input v-model="data.website.dropped" :disabled="!canEdit" type="text" placeholder="0" :class="inputCls" />
                </div>
                <div>
                  <label class="block text-[10px] text-slate-500 mb-1">미점유 지점 수</label>
                  <input v-model="data.website.missing" :disabled="!canEdit" type="text" placeholder="0" :class="inputCls" />
                </div>
              </div>
              <!-- 대응 -->
              <div>
                <label class="block text-[10px] text-slate-500 mb-1">대응 중인 내용</label>
                <textarea v-model="data.website.response" :disabled="!canEdit" rows="2" :class="textareaCls" />
              </div>
              <!-- 상태 설명 -->
              <div>
                <label class="block text-[10px] text-slate-500 mb-1">상태 설명</label>
                <textarea v-model="data.website.summary" :disabled="!canEdit" rows="2" :class="textareaCls" />
              </div>
              <!-- 현재 노출 지점 -->
              <div>
                <label class="block text-[10px] text-slate-500 mb-1">현재 노출 지점</label>
                <textarea v-model="data.website.visibleList" :disabled="!canEdit" rows="3" :class="textareaCls" />
              </div>
              <!-- 링크 -->
              <div>
                <label class="block text-[10px] text-slate-500 mb-1">원본 링크</label>
                <input v-model="data.website.link" :disabled="!canEdit" type="text" placeholder="https://" :class="inputCls" />
              </div>
              <!-- 이미지 -->
              <div class="border-t border-slate-100 pt-3">
                <label class="block text-[10px] text-slate-500 mb-1.5">첨부 이미지</label>
                <div
                  v-if="canEdit"
                  tabindex="0"
                  @paste="(e) => onPaste(e, 'website')"
                  class="border-2 border-dashed border-slate-200 rounded px-3 py-2 text-[10px] text-slate-400 text-center hover:bg-slate-50 focus:outline-none focus:border-blue-300 focus:bg-blue-50/30 cursor-text mb-2"
                  :class="{ 'opacity-60': uploadingFor === 'website' }"
                >{{ uploadingFor === 'website' ? '업로드 중...' : '여기를 클릭 후 Ctrl+V 로 이미지 붙여넣기' }}</div>
                <div v-if="data.website.images.length > 0" class="grid grid-cols-4 gap-1.5">
                  <div v-for="(img, i) in data.website.images" :key="img" class="relative group">
                    <img :src="resolveImageUrl(img)" class="w-full h-16 object-cover rounded border border-slate-200 cursor-pointer" @click="openImagePreview(img)" />
                    <button v-if="canEdit" @click="removeImage('website', i)" class="absolute top-0.5 right-0.5 w-4 h-4 bg-black/60 text-white rounded-full flex items-center justify-center text-[10px] opacity-0 group-hover:opacity-100 transition-opacity">&#x2715;</button>
                  </div>
                </div>
                <div v-else class="text-[10px] text-slate-300 text-center py-1">첨부된 이미지 없음</div>
              </div>
            </div>
          </section>

          <!-- ─── 04 블로그 상위노출 ─── -->
          <section
            :ref="(el) => { sectionRefs['blogExposure'] = el as HTMLElement }"
            class="bg-white border border-slate-200 rounded-lg overflow-hidden"
          >
            <div class="flex items-center justify-between px-4 py-2.5 border-b border-slate-100">
              <span class="text-xs font-semibold text-slate-700">04 블로그 상위노출</span>
              <button
                @click="collapsed.blogExposure = !collapsed.blogExposure"
                class="text-[10px] text-slate-400 hover:text-slate-600 px-1"
              >{{ collapsed.blogExposure ? '▶' : '▼' }}</button>
            </div>
            <div v-show="!collapsed.blogExposure" class="p-4 space-y-3">
              <!-- 지표 3개 -->
              <div class="grid grid-cols-3 gap-2">
                <div>
                  <label class="block text-[10px] text-slate-500 mb-1">총 키워드 수</label>
                  <input v-model="data.blogExposure.total" :disabled="!canEdit" type="text" placeholder="0" :class="inputCls" />
                </div>
                <div>
                  <label class="block text-[10px] text-slate-500 mb-1">노출 수</label>
                  <input v-model="data.blogExposure.visible" :disabled="!canEdit" type="text" placeholder="0" :class="inputCls" />
                </div>
                <div>
                  <label class="block text-[10px] text-slate-500 mb-1">이탈 수</label>
                  <input v-model="data.blogExposure.dropped" :disabled="!canEdit" type="text" placeholder="0" :class="inputCls" />
                </div>
              </div>
              <!-- 대응 -->
              <div>
                <label class="block text-[10px] text-slate-500 mb-1">대응 중인 내용</label>
                <textarea v-model="data.blogExposure.response" :disabled="!canEdit" rows="2" :class="textareaCls" />
              </div>
              <!-- 상태 설명 -->
              <div>
                <label class="block text-[10px] text-slate-500 mb-1">상태 설명</label>
                <textarea v-model="data.blogExposure.summary" :disabled="!canEdit" rows="2" :class="textareaCls" />
              </div>
              <!-- 링크 -->
              <div>
                <label class="block text-[10px] text-slate-500 mb-1">원본 링크</label>
                <input v-model="data.blogExposure.link" :disabled="!canEdit" type="text" placeholder="https://" :class="inputCls" />
              </div>
              <!-- 이미지 -->
              <div class="border-t border-slate-100 pt-3">
                <label class="block text-[10px] text-slate-500 mb-1.5">첨부 이미지</label>
                <div
                  v-if="canEdit"
                  tabindex="0"
                  @paste="(e) => onPaste(e, 'blogExposure')"
                  class="border-2 border-dashed border-slate-200 rounded px-3 py-2 text-[10px] text-slate-400 text-center hover:bg-slate-50 focus:outline-none focus:border-blue-300 focus:bg-blue-50/30 cursor-text mb-2"
                  :class="{ 'opacity-60': uploadingFor === 'blogExposure' }"
                >{{ uploadingFor === 'blogExposure' ? '업로드 중...' : '여기를 클릭 후 Ctrl+V 로 이미지 붙여넣기' }}</div>
                <div v-if="data.blogExposure.images.length > 0" class="grid grid-cols-4 gap-1.5">
                  <div v-for="(img, i) in data.blogExposure.images" :key="img" class="relative group">
                    <img :src="resolveImageUrl(img)" class="w-full h-16 object-cover rounded border border-slate-200 cursor-pointer" @click="openImagePreview(img)" />
                    <button v-if="canEdit" @click="removeImage('blogExposure', i)" class="absolute top-0.5 right-0.5 w-4 h-4 bg-black/60 text-white rounded-full flex items-center justify-center text-[10px] opacity-0 group-hover:opacity-100 transition-opacity">&#x2715;</button>
                  </div>
                </div>
                <div v-else class="text-[10px] text-slate-300 text-center py-1">첨부된 이미지 없음</div>
              </div>
            </div>
          </section>

          <!-- ─── 05 함께찾는 ─── -->
          <section
            :ref="(el) => { sectionRefs['related'] = el as HTMLElement }"
            class="bg-white border border-slate-200 rounded-lg overflow-hidden"
          >
            <div class="flex items-center justify-between px-4 py-2.5 border-b border-slate-100">
              <span class="text-xs font-semibold text-slate-700">05 함께찾는</span>
              <button
                @click="collapsed.related = !collapsed.related"
                class="text-[10px] text-slate-400 hover:text-slate-600 px-1"
              >{{ collapsed.related ? '▶' : '▼' }}</button>
            </div>
            <div v-show="!collapsed.related" class="p-4 space-y-3">
              <!-- 지표 4개 -->
              <div class="grid grid-cols-4 gap-2">
                <div>
                  <label class="block text-[10px] text-slate-500 mb-1">총 키워드 수</label>
                  <input v-model="data.related.total" :disabled="!canEdit" type="text" placeholder="0" :class="inputCls" />
                </div>
                <div>
                  <label class="block text-[10px] text-slate-500 mb-1">생성 키워드 수</label>
                  <input v-model="data.related.created" :disabled="!canEdit" type="text" placeholder="0" :class="inputCls" />
                </div>
                <div>
                  <label class="block text-[10px] text-slate-500 mb-1">이탈 키워드 수</label>
                  <input v-model="data.related.dropped" :disabled="!canEdit" type="text" placeholder="0" :class="inputCls" />
                </div>
                <div>
                  <label class="block text-[10px] text-slate-500 mb-1">신규 키워드 수</label>
                  <input v-model="data.related.newCount" :disabled="!canEdit" type="text" placeholder="0" :class="inputCls" />
                </div>
              </div>
              <!-- 대응 -->
              <div>
                <label class="block text-[10px] text-slate-500 mb-1">대응 중인 내용</label>
                <textarea v-model="data.related.response" :disabled="!canEdit" rows="2" :class="textareaCls" />
              </div>
              <!-- 상태 설명 -->
              <div>
                <label class="block text-[10px] text-slate-500 mb-1">상태 설명</label>
                <textarea v-model="data.related.summary" :disabled="!canEdit" rows="2" :class="textareaCls" />
              </div>
              <!-- 생성 키워드 목록 -->
              <div>
                <label class="block text-[10px] text-slate-500 mb-1">생성 키워드 목록</label>
                <textarea v-model="data.related.keywords" :disabled="!canEdit" rows="3" :class="textareaCls" />
              </div>
              <!-- 링크 -->
              <div>
                <label class="block text-[10px] text-slate-500 mb-1">원본 링크</label>
                <input v-model="data.related.link" :disabled="!canEdit" type="text" placeholder="https://" :class="inputCls" />
              </div>
              <!-- 이미지 -->
              <div class="border-t border-slate-100 pt-3">
                <label class="block text-[10px] text-slate-500 mb-1.5">첨부 이미지</label>
                <div
                  v-if="canEdit"
                  tabindex="0"
                  @paste="(e) => onPaste(e, 'related')"
                  class="border-2 border-dashed border-slate-200 rounded px-3 py-2 text-[10px] text-slate-400 text-center hover:bg-slate-50 focus:outline-none focus:border-blue-300 focus:bg-blue-50/30 cursor-text mb-2"
                  :class="{ 'opacity-60': uploadingFor === 'related' }"
                >{{ uploadingFor === 'related' ? '업로드 중...' : '여기를 클릭 후 Ctrl+V 로 이미지 붙여넣기' }}</div>
                <div v-if="data.related.images.length > 0" class="grid grid-cols-4 gap-1.5">
                  <div v-for="(img, i) in data.related.images" :key="img" class="relative group">
                    <img :src="resolveImageUrl(img)" class="w-full h-16 object-cover rounded border border-slate-200 cursor-pointer" @click="openImagePreview(img)" />
                    <button v-if="canEdit" @click="removeImage('related', i)" class="absolute top-0.5 right-0.5 w-4 h-4 bg-black/60 text-white rounded-full flex items-center justify-center text-[10px] opacity-0 group-hover:opacity-100 transition-opacity">&#x2715;</button>
                  </div>
                </div>
                <div v-else class="text-[10px] text-slate-300 text-center py-1">첨부된 이미지 없음</div>
              </div>
            </div>
          </section>

          <!-- 하단 여백 -->
          <div class="h-6"></div>
        </div>
        </div>
      </div>

      <!-- 결과 탭 -->
      <div v-if="tab === 'result'" class="h-full flex flex-col overflow-hidden">

        <!-- 앵커 바 (sticky 상단) -->
        <nav class="shrink-0 border-b border-slate-200 bg-white px-4 py-2 flex items-center gap-3 overflow-x-auto">
          <button
            v-for="item in resultNavItems"
            :key="item.key"
            @click="scrollToResult(item.key)"
            class="text-[11px] text-slate-500 hover:text-slate-900 whitespace-nowrap shrink-0"
          >{{ item.label }}</button>
        </nav>

        <!-- 문서 스크롤 영역 -->
        <div class="flex-1 overflow-y-auto bg-slate-100 py-8 px-4">
          <article class="max-w-4xl mx-auto bg-white border border-slate-200 rounded-lg shadow-sm">

            <!-- 헤더 블록 -->
            <header class="px-10 pt-10 pb-6 border-b border-slate-100">
              <p class="text-[10px] tracking-[0.2em] text-slate-400 font-medium mb-3">WEEKLY RANKING REPORT</p>
              <h1 class="text-2xl font-bold text-slate-800 mb-2">{{ title || '제목 없음' }}</h1>
              <p class="text-xs text-slate-500 tabular-nums">{{ periodLabel }}</p>
              <p v-if="data.basic.notice" class="text-[11px] text-slate-400 mt-2">{{ data.basic.notice }}</p>
            </header>

            <!-- KPI strip -->
            <div class="grid grid-cols-5 gap-px bg-slate-100 border-b border-slate-100">
              <div v-for="kpi in kpis" :key="kpi.key" class="bg-white px-4 py-3 text-center">
                <div class="text-[10px] text-slate-500 mb-1">{{ kpi.label }}</div>
                <div class="text-lg font-semibold text-slate-800 tabular-nums">{{ kpi.value }}</div>
              </div>
            </div>

            <!-- 섹션 5개 -->
            <div class="divide-y divide-slate-100">

              <!-- §1 블로그배포 -->
              <section
                :ref="(el) => { resultSectionRefs['blogDistribution'] = el as HTMLElement }"
                class="px-10 py-8"
              >
                <div class="flex items-baseline gap-3 mb-4">
                  <span class="text-sm font-bold text-slate-400">01</span>
                  <h3 class="text-base font-bold text-slate-800">최적블로그 배포</h3>
                </div>
                <div class="grid grid-cols-3 gap-4 mb-4">
                  <div>
                    <div class="text-[10px] text-slate-500 mb-0.5">누적 발행 글</div>
                    <div class="text-xl font-semibold text-slate-800 tabular-nums">{{ data.blogDistribution.posts || '—' }}</div>
                  </div>
                  <div>
                    <div class="text-[10px] text-slate-500 mb-0.5">금일 상위노출 지점</div>
                    <div class="text-xl font-semibold text-slate-800 tabular-nums">{{ data.blogDistribution.ranked || '—' }}</div>
                  </div>
                  <div>
                    <div class="text-[10px] text-slate-500 mb-0.5">타겟 키워드</div>
                    <div class="text-xl font-semibold text-slate-800 tabular-nums">{{ data.blogDistribution.keywords || '—' }}</div>
                  </div>
                </div>
                <p v-if="data.blogDistribution.summary" class="text-sm text-slate-700 leading-relaxed mb-4">{{ data.blogDistribution.summary }}</p>
                <dl class="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-xs">
                  <template v-if="data.blogDistribution.response">
                    <dt class="text-slate-400 shrink-0">대응 중</dt>
                    <dd class="text-slate-700">{{ data.blogDistribution.response }}</dd>
                  </template>
                  <template v-if="data.blogDistribution.link1 || data.blogDistribution.link2">
                    <dt class="text-slate-400 shrink-0">원본 링크</dt>
                    <dd class="text-slate-700">
                      <a v-if="data.blogDistribution.link1" :href="data.blogDistribution.link1" target="_blank" rel="noopener" class="text-blue-600 hover:underline mr-2">링크1</a>
                      <a v-if="data.blogDistribution.link2" :href="data.blogDistribution.link2" target="_blank" rel="noopener" class="text-blue-600 hover:underline">링크2</a>
                    </dd>
                  </template>
                </dl>
                <div v-if="data.blogDistribution.images.length > 0" class="mt-3 grid grid-cols-4 gap-2">
                  <img
                    v-for="img in data.blogDistribution.images"
                    :key="img"
                    :src="resolveImageUrl(img)"
                    class="w-full h-24 object-cover rounded border border-slate-100 cursor-pointer"
                    @click="openImagePreview(img)"
                  />
                </div>
              </section>

              <!-- §2 플레이스 -->
              <section
                :ref="(el) => { resultSectionRefs['place'] = el as HTMLElement }"
                class="px-10 py-8"
              >
                <div class="flex items-baseline gap-3 mb-4">
                  <span class="text-sm font-bold text-slate-400">02</span>
                  <h3 class="text-base font-bold text-slate-800">플레이스</h3>
                </div>
                <div class="grid grid-cols-4 gap-4 mb-4">
                  <div>
                    <div class="text-[10px] text-slate-500 mb-0.5">총 지점</div>
                    <div class="text-xl font-semibold text-slate-800 tabular-nums">{{ data.place.total || '—' }}</div>
                  </div>
                  <div>
                    <div class="text-[10px] text-slate-500 mb-0.5">점유</div>
                    <div class="text-xl font-semibold text-slate-800 tabular-nums">{{ data.place.occupied || '—' }}</div>
                  </div>
                  <div>
                    <div class="text-[10px] text-slate-500 mb-0.5">이탈</div>
                    <div class="text-xl font-semibold text-slate-800 tabular-nums">{{ data.place.dropped || '—' }}</div>
                  </div>
                  <div>
                    <div class="text-[10px] text-slate-500 mb-0.5">휴식</div>
                    <div class="text-xl font-semibold text-slate-800 tabular-nums">{{ data.place.paused || '—' }}</div>
                  </div>
                </div>
                <p v-if="data.place.summary" class="text-sm text-slate-700 leading-relaxed mb-4">{{ data.place.summary }}</p>
                <dl class="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-xs">
                  <template v-if="data.place.droppedList">
                    <dt class="text-slate-400 shrink-0">이탈 지점</dt>
                    <dd class="text-slate-700 whitespace-pre-wrap">{{ data.place.droppedList }}</dd>
                  </template>
                  <template v-if="data.place.newList">
                    <dt class="text-slate-400 shrink-0">신규 지점</dt>
                    <dd class="text-slate-700 whitespace-pre-wrap">{{ data.place.newList }}</dd>
                  </template>
                  <template v-if="data.place.pausedList">
                    <dt class="text-slate-400 shrink-0">휴식 지점</dt>
                    <dd class="text-slate-700 whitespace-pre-wrap">{{ data.place.pausedList }}</dd>
                  </template>
                  <template v-if="data.place.comment">
                    <dt class="text-slate-400 shrink-0">작업 코멘트</dt>
                    <dd class="text-slate-700 whitespace-pre-wrap">{{ data.place.comment }}</dd>
                  </template>
                  <template v-if="data.place.response">
                    <dt class="text-slate-400 shrink-0">대응 중</dt>
                    <dd class="text-slate-700">{{ data.place.response }}</dd>
                  </template>
                  <template v-if="data.place.link">
                    <dt class="text-slate-400 shrink-0">원본 링크</dt>
                    <dd class="text-slate-700">
                      <a :href="data.place.link" target="_blank" rel="noopener" class="text-blue-600 hover:underline">링크</a>
                    </dd>
                  </template>
                </dl>
                <div v-if="data.place.images.length > 0" class="mt-3 grid grid-cols-4 gap-2">
                  <img
                    v-for="img in data.place.images"
                    :key="img"
                    :src="resolveImageUrl(img)"
                    class="w-full h-24 object-cover rounded border border-slate-100 cursor-pointer"
                    @click="openImagePreview(img)"
                  />
                </div>
              </section>

              <!-- §3 웹사이트 -->
              <section
                :ref="(el) => { resultSectionRefs['website'] = el as HTMLElement }"
                class="px-10 py-8"
              >
                <div class="flex items-baseline gap-3 mb-4">
                  <span class="text-sm font-bold text-slate-400">03</span>
                  <h3 class="text-base font-bold text-slate-800">웹사이트</h3>
                </div>
                <div class="grid grid-cols-4 gap-4 mb-4">
                  <div>
                    <div class="text-[10px] text-slate-500 mb-0.5">총 키워드</div>
                    <div class="text-xl font-semibold text-slate-800 tabular-nums">{{ data.website.total || '—' }}</div>
                  </div>
                  <div>
                    <div class="text-[10px] text-slate-500 mb-0.5">노출 지점</div>
                    <div class="text-xl font-semibold text-slate-800 tabular-nums">{{ data.website.visible || '—' }}</div>
                  </div>
                  <div>
                    <div class="text-[10px] text-slate-500 mb-0.5">이탈 지점</div>
                    <div class="text-xl font-semibold text-slate-800 tabular-nums">{{ data.website.dropped || '—' }}</div>
                  </div>
                  <div>
                    <div class="text-[10px] text-slate-500 mb-0.5">미점유 지점</div>
                    <div class="text-xl font-semibold text-slate-800 tabular-nums">{{ data.website.missing || '—' }}</div>
                  </div>
                </div>
                <p v-if="data.website.summary" class="text-sm text-slate-700 leading-relaxed mb-4">{{ data.website.summary }}</p>
                <dl class="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-xs">
                  <template v-if="data.website.visibleList">
                    <dt class="text-slate-400 shrink-0">현재 노출 지점</dt>
                    <dd class="text-slate-700 whitespace-pre-wrap">{{ data.website.visibleList }}</dd>
                  </template>
                  <template v-if="data.website.response">
                    <dt class="text-slate-400 shrink-0">대응 중</dt>
                    <dd class="text-slate-700">{{ data.website.response }}</dd>
                  </template>
                  <template v-if="data.website.link">
                    <dt class="text-slate-400 shrink-0">원본 링크</dt>
                    <dd class="text-slate-700">
                      <a :href="data.website.link" target="_blank" rel="noopener" class="text-blue-600 hover:underline">링크</a>
                    </dd>
                  </template>
                </dl>
                <div v-if="data.website.images.length > 0" class="mt-3 grid grid-cols-4 gap-2">
                  <img
                    v-for="img in data.website.images"
                    :key="img"
                    :src="resolveImageUrl(img)"
                    class="w-full h-24 object-cover rounded border border-slate-100 cursor-pointer"
                    @click="openImagePreview(img)"
                  />
                </div>
              </section>

              <!-- §4 블로그 상위노출 -->
              <section
                :ref="(el) => { resultSectionRefs['blogExposure'] = el as HTMLElement }"
                class="px-10 py-8"
              >
                <div class="flex items-baseline gap-3 mb-4">
                  <span class="text-sm font-bold text-slate-400">04</span>
                  <h3 class="text-base font-bold text-slate-800">블로그 상위노출</h3>
                </div>
                <div class="grid grid-cols-3 gap-4 mb-4">
                  <div>
                    <div class="text-[10px] text-slate-500 mb-0.5">총 키워드</div>
                    <div class="text-xl font-semibold text-slate-800 tabular-nums">{{ data.blogExposure.total || '—' }}</div>
                  </div>
                  <div>
                    <div class="text-[10px] text-slate-500 mb-0.5">노출</div>
                    <div class="text-xl font-semibold text-slate-800 tabular-nums">{{ data.blogExposure.visible || '—' }}</div>
                  </div>
                  <div>
                    <div class="text-[10px] text-slate-500 mb-0.5">이탈</div>
                    <div class="text-xl font-semibold text-slate-800 tabular-nums">{{ data.blogExposure.dropped || '—' }}</div>
                  </div>
                </div>
                <p v-if="data.blogExposure.summary" class="text-sm text-slate-700 leading-relaxed mb-4">{{ data.blogExposure.summary }}</p>
                <dl class="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-xs">
                  <template v-if="data.blogExposure.response">
                    <dt class="text-slate-400 shrink-0">대응 중</dt>
                    <dd class="text-slate-700">{{ data.blogExposure.response }}</dd>
                  </template>
                  <template v-if="data.blogExposure.link">
                    <dt class="text-slate-400 shrink-0">원본 링크</dt>
                    <dd class="text-slate-700">
                      <a :href="data.blogExposure.link" target="_blank" rel="noopener" class="text-blue-600 hover:underline">링크</a>
                    </dd>
                  </template>
                </dl>
                <div v-if="data.blogExposure.images.length > 0" class="mt-3 grid grid-cols-4 gap-2">
                  <img
                    v-for="img in data.blogExposure.images"
                    :key="img"
                    :src="resolveImageUrl(img)"
                    class="w-full h-24 object-cover rounded border border-slate-100 cursor-pointer"
                    @click="openImagePreview(img)"
                  />
                </div>
              </section>

              <!-- §5 함께찾는 -->
              <section
                :ref="(el) => { resultSectionRefs['related'] = el as HTMLElement }"
                class="px-10 py-8"
              >
                <div class="flex items-baseline gap-3 mb-4">
                  <span class="text-sm font-bold text-slate-400">05</span>
                  <h3 class="text-base font-bold text-slate-800">함께 많이 찾는</h3>
                </div>
                <div class="grid grid-cols-4 gap-4 mb-4">
                  <div>
                    <div class="text-[10px] text-slate-500 mb-0.5">총 키워드</div>
                    <div class="text-xl font-semibold text-slate-800 tabular-nums">{{ data.related.total || '—' }}</div>
                  </div>
                  <div>
                    <div class="text-[10px] text-slate-500 mb-0.5">생성</div>
                    <div class="text-xl font-semibold text-slate-800 tabular-nums">{{ data.related.created || '—' }}</div>
                  </div>
                  <div>
                    <div class="text-[10px] text-slate-500 mb-0.5">이탈</div>
                    <div class="text-xl font-semibold text-slate-800 tabular-nums">{{ data.related.dropped || '—' }}</div>
                  </div>
                  <div>
                    <div class="text-[10px] text-slate-500 mb-0.5">신규</div>
                    <div class="text-xl font-semibold text-slate-800 tabular-nums">{{ data.related.newCount || '—' }}</div>
                  </div>
                </div>
                <p v-if="data.related.summary" class="text-sm text-slate-700 leading-relaxed mb-4">{{ data.related.summary }}</p>
                <dl class="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-xs">
                  <template v-if="data.related.keywords">
                    <dt class="text-slate-400 shrink-0">생성 키워드</dt>
                    <dd class="text-slate-700 whitespace-pre-wrap">{{ data.related.keywords }}</dd>
                  </template>
                  <template v-if="data.related.response">
                    <dt class="text-slate-400 shrink-0">대응 중</dt>
                    <dd class="text-slate-700">{{ data.related.response }}</dd>
                  </template>
                  <template v-if="data.related.link">
                    <dt class="text-slate-400 shrink-0">원본 링크</dt>
                    <dd class="text-slate-700">
                      <a :href="data.related.link" target="_blank" rel="noopener" class="text-blue-600 hover:underline">링크</a>
                    </dd>
                  </template>
                </dl>
                <div v-if="data.related.images.length > 0" class="mt-3 grid grid-cols-4 gap-2">
                  <img
                    v-for="img in data.related.images"
                    :key="img"
                    :src="resolveImageUrl(img)"
                    class="w-full h-24 object-cover rounded border border-slate-100 cursor-pointer"
                    @click="openImagePreview(img)"
                  />
                </div>
              </section>

            </div>

            <!-- Footer -->
            <footer class="px-10 py-4 border-t border-slate-100 text-[10px] text-slate-400 tabular-nums">
              Generated · {{ generatedAtLabel }}
            </footer>

          </article>
        </div>
      </div>

    </div>
  </div>

  <!-- ── 불러오기 모달 ── -->
  <Teleport to="body">
    <div
      v-if="showImportModal"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
      @click.self="showImportModal = false"
    >
      <div class="bg-white rounded-lg shadow-xl w-[480px] max-w-[90vw]">
        <div class="px-4 py-3 border-b border-slate-100 flex items-center justify-between">
          <h3 class="text-sm font-semibold text-slate-800">텍스트 불러오기</h3>
          <button @click="showImportModal = false" class="text-slate-400 hover:text-slate-600 text-sm">&#x2715;</button>
        </div>
        <div class="px-4 py-3 space-y-3">
          <div>
            <label class="block text-[10px] text-slate-500 mb-1">파일 업로드 (.txt)</label>
            <input
              type="file"
              accept=".txt,text/plain"
              @change="onFileSelected"
              class="text-xs w-full"
            />
          </div>
          <div>
            <label class="block text-[10px] text-slate-500 mb-1">또는 텍스트 직접 붙여넣기</label>
            <textarea
              v-model="importText"
              rows="10"
              class="w-full text-xs border border-slate-200 rounded px-2 py-1.5 font-mono"
              placeholder="[최적블로그 배포]&#10;발행한 글 N개..."
            />
          </div>
          <p class="text-[10px] text-slate-400">
            확정 시 현재 섹션 내용이 불러온 값으로 교체됩니다.
          </p>
        </div>
        <div class="px-4 py-3 border-t border-slate-100 flex items-center justify-end gap-2">
          <button
            @click="showImportModal = false"
            class="text-xs px-3 py-1.5 rounded border border-slate-300 hover:bg-slate-50 text-slate-600"
          >취소</button>
          <button
            @click="applyImport"
            :disabled="!importText.trim()"
            class="text-xs px-3 py-1.5 rounded bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-40"
          >불러오기</button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

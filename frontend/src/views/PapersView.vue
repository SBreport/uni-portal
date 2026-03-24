<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { usePapersStore, type Paper } from '@/stores/papers'
import * as papersApi from '@/api/papers'

const store = usePapersStore()

const selectedPaper = ref<Paper | null>(null)
const detailLoading = ref(false)
const detailData = ref<Paper | null>(null)

// JSON 업로드
const showUploadModal = ref(false)
const uploadFile = ref<File | null>(null)
const uploading = ref(false)
const uploadResult = ref<{ inserted: number; duplicates: any[]; errors: any[]; message: string } | null>(null)

function onFileSelect(e: Event) {
  const target = e.target as HTMLInputElement
  uploadFile.value = target.files?.[0] || null
  uploadResult.value = null
}

async function doUpload() {
  if (!uploadFile.value) return
  uploading.value = true
  uploadResult.value = null
  try {
    const { data } = await papersApi.uploadPapersJson(uploadFile.value)
    uploadResult.value = data
    if (data.inserted > 0) {
      store.loadPapers()  // 목록 새로고침
    }
  } catch (err: any) {
    uploadResult.value = {
      inserted: 0, duplicates: [], errors: [],
      message: err.response?.data?.detail || '업로드 실패',
    }
  } finally {
    uploading.value = false
  }
}

function closeUploadModal() {
  showUploadModal.value = false
  uploadFile.value = null
  uploadResult.value = null
}

onMounted(() => {
  store.loadPapers()
  store.loadFilterOptions()
})

function evidenceStars(level: number) {
  return '\u2605'.repeat(level) + '\u2606'.repeat(5 - level)
}

function evidenceColor(level: number) {
  if (level >= 4) return 'text-emerald-600 bg-emerald-50'
  if (level >= 3) return 'text-blue-600 bg-blue-50'
  if (level >= 2) return 'text-amber-600 bg-amber-50'
  return 'text-slate-500 bg-slate-100'
}

function statusBadge(status: string) {
  switch (status) {
    case 'verified': return { label: '검증됨', cls: 'bg-emerald-100 text-emerald-700' }
    case 'reviewed': return { label: '검토됨', cls: 'bg-blue-100 text-blue-700' }
    case 'draft': return { label: '초안', cls: 'bg-slate-100 text-slate-600' }
    default: return { label: status, cls: 'bg-slate-100 text-slate-500' }
  }
}

function parseKeywords(raw: string): string[] {
  try { return JSON.parse(raw) } catch { return [] }
}

async function openDetail(paper: Paper) {
  if (selectedPaper.value?.id === paper.id) return
  selectedPaper.value = paper
  detailLoading.value = true
  detailData.value = null
  try {
    const { data } = await papersApi.getPaper(paper.id)
    detailData.value = data
  } catch {
    detailData.value = paper
  } finally {
    detailLoading.value = false
  }
}

function handleSearch() {
  store.loadPapers()
}
</script>

<template>
  <div class="p-5 h-[calc(100vh-1rem)]">
    <div class="flex items-center justify-between mb-3">
      <h2 class="text-xl font-bold text-slate-800">시술논문</h2>
      <div class="flex items-center gap-2">
        <span class="text-xs text-slate-400">{{ store.papers.length }}건</span>
        <button @click="showUploadModal = true"
          class="px-3 py-1.5 bg-blue-600 text-white text-xs font-medium rounded-md hover:bg-blue-700 transition">
          📄 JSON 업로드
        </button>
      </div>
    </div>

    <!-- 필터 바 -->
    <div class="flex items-center gap-2 mb-3 flex-wrap">
      <!-- 장비 필터 -->
      <select v-model="store.filterDeviceId" @change="handleSearch"
        class="px-2.5 py-1.5 border border-slate-300 rounded-md text-xs bg-white min-w-[140px]">
        <option :value="null">전체 ({{ store.papers.length }}건)</option>
        <option v-for="d in store.deviceOptions" :key="d.id" :value="d.id">
          {{ d.name }} ({{ d.paper_count }})
        </option>
      </select>

      <!-- 근거수준 필터 -->
      <select v-model="store.filterEvidenceMin" @change="handleSearch"
        class="px-2.5 py-1.5 border border-slate-300 rounded-md text-xs bg-white">
        <option :value="null">근거수준 전체</option>
        <option :value="4">★★★★ 이상 (RCT+)</option>
        <option :value="3">★★★ 이상 (코호트+)</option>
        <option :value="2">★★ 이상 (증례+)</option>
        <option :value="1">★ 이상</option>
      </select>

      <!-- 연구유형 필터 -->
      <select v-model="store.filterStudyType" @change="handleSearch"
        class="px-2.5 py-1.5 border border-slate-300 rounded-md text-xs bg-white">
        <option value="">연구유형 전체</option>
        <option v-for="st in store.studyTypeOptions" :key="st.study_type" :value="st.study_type">
          {{ st.study_type }} ({{ st.cnt }})
        </option>
      </select>

      <!-- 텍스트 검색 -->
      <input v-model="store.filterSearch" placeholder="제목, 저자, 키워드, 요약 검색..."
        class="px-3 py-1.5 border border-slate-300 rounded-md text-xs flex-1 min-w-[200px] focus:outline-none focus:ring-1 focus:ring-blue-400"
        @input="handleSearch" />

      <!-- 필터 초기화 -->
      <button v-if="store.filterSearch || store.filterStatus || store.filterDeviceId || store.filterEvidenceMin || store.filterStudyType"
        @click="store.resetFilters()"
        class="px-2.5 py-1.5 text-xs text-slate-500 hover:text-slate-700 border border-slate-200 rounded-md hover:bg-slate-50">
        초기화
      </button>
    </div>

    <!-- 2컬럼: 목록(좌) + 상세(우) -->
    <div class="flex gap-4" style="height: calc(100vh - 160px)">

      <!-- ===== 좌측: 논문 목록 ===== -->
      <div class="w-[38%] shrink-0 bg-white border border-slate-200 rounded-lg overflow-hidden flex flex-col">
        <div class="overflow-auto flex-1">
          <div v-if="store.loading" class="flex items-center justify-center h-32">
            <div class="w-5 h-5 border-2 border-blue-400 border-t-transparent rounded-full animate-spin"></div>
          </div>

          <div v-else-if="store.papers.length === 0" class="flex items-center justify-center h-32">
            <p class="text-sm text-slate-400">등록된 논문이 없습니다.</p>
          </div>

          <div v-else class="divide-y divide-slate-100">
            <div v-for="paper in store.papers" :key="paper.id"
              class="px-4 py-3 cursor-pointer transition-colors"
              :class="{
                '!bg-blue-50 border-l-2 border-l-blue-500': selectedPaper?.id === paper.id,
                'hover:bg-slate-50': selectedPaper?.id !== paper.id
              }"
              @click="openDetail(paper)">

              <div class="flex items-center gap-2 mb-1">
                <span v-if="paper.device_name"
                  class="px-1.5 py-0.5 bg-blue-100 text-blue-700 rounded text-[11px] font-medium truncate max-w-[120px]">
                  {{ paper.device_name }}
                </span>
                <span :class="statusBadge(paper.status).cls"
                  class="px-1.5 py-0.5 rounded text-[11px]">
                  {{ statusBadge(paper.status).label }}
                </span>
                <span class="ml-auto text-[11px] text-slate-400">{{ paper.pub_year || '' }}</span>
              </div>

              <p class="text-sm font-medium text-slate-800 leading-snug line-clamp-2">
                <span v-if="paper.photo_restriction" class="inline-block mr-1 text-red-500" title="사진 사용 제한">🚫</span>
                {{ paper.title_ko || paper.title }}
              </p>

              <div class="flex items-center gap-2 mt-1.5">
                <span :class="evidenceColor(paper.evidence_level)"
                  class="px-1.5 py-0.5 rounded text-[11px] font-medium">
                  {{ evidenceStars(paper.evidence_level) }} ({{ paper.evidence_level }}/5)
                </span>
                <span v-if="paper.study_type" class="text-[11px] text-slate-500">{{ paper.study_type }}</span>
              </div>

              <p v-if="paper.authors || paper.journal" class="text-[11px] text-slate-400 mt-1 truncate">
                {{ paper.authors }}{{ paper.authors && paper.journal ? ' / ' : '' }}{{ paper.journal }}
              </p>
            </div>
          </div>
        </div>
      </div>

      <!-- ===== 우측: 논문 상세 ===== -->
      <div class="flex-1 min-w-0 overflow-auto">
        <div v-if="!selectedPaper" class="h-full flex items-center justify-center bg-white border border-slate-200 rounded-lg">
          <div class="text-center">
            <div class="w-12 h-12 rounded-full bg-slate-100 flex items-center justify-center mx-auto mb-3">
              <span class="text-xl text-slate-300">P</span>
            </div>
            <p class="text-sm text-slate-400 font-medium">논문을 선택하세요</p>
            <p class="text-xs text-slate-300 mt-1">좌측 목록에서 논문을 클릭하면<br>상세 분석 내용을 확인할 수 있습니다.</p>
          </div>
        </div>

        <div v-else class="h-full flex flex-col bg-white border border-slate-200 rounded-lg overflow-hidden">
          <!-- 헤더 -->
          <div class="px-5 py-4 border-b border-slate-100 bg-slate-50/50 shrink-0">
            <h3 class="text-base font-bold text-slate-800 leading-snug">
              {{ selectedPaper.title_ko || selectedPaper.title }}
            </h3>
            <p v-if="selectedPaper.title_ko && selectedPaper.title"
              class="text-xs text-slate-400 mt-1 leading-snug">{{ selectedPaper.title }}</p>
            <div class="flex items-center gap-2 mt-2 flex-wrap">
              <span v-if="selectedPaper.device_name"
                class="px-2 py-0.5 bg-blue-100 text-blue-700 rounded text-xs font-medium">
                {{ selectedPaper.device_name }}
              </span>
              <span :class="evidenceColor(selectedPaper.evidence_level)"
                class="px-2 py-0.5 rounded text-xs font-medium">
                {{ evidenceStars(selectedPaper.evidence_level) }} ({{ selectedPaper.evidence_level }}/5)
              </span>
              <span v-if="selectedPaper.study_type" class="text-xs text-slate-500">{{ selectedPaper.study_type }}</span>
              <span class="text-slate-300">|</span>
              <span class="text-xs text-slate-500">{{ selectedPaper.sample_size || '대상자 미상' }}</span>
              <span v-if="selectedPaper.follow_up_period" class="text-slate-300">|</span>
              <span v-if="selectedPaper.follow_up_period" class="text-xs text-slate-500">추적 {{ selectedPaper.follow_up_period }}</span>
            </div>
            <div class="flex items-center gap-3 mt-1 text-xs text-slate-400">
              <span>{{ selectedPaper.authors }}</span>
              <span v-if="selectedPaper.journal">{{ selectedPaper.journal }} ({{ selectedPaper.pub_year }})</span>
              <a v-if="selectedPaper.source_url" :href="selectedPaper.source_url" target="_blank"
                class="text-blue-500 hover:underline ml-auto">DOI</a>
            </div>
            <!-- 📄 원본 파일명 -->
            <div v-if="selectedPaper.source_file" class="mt-2 flex items-center gap-2 bg-slate-100 rounded px-3 py-1.5">
              <span class="text-slate-400 shrink-0">📄</span>
              <span class="text-xs text-slate-600 font-mono truncate" :title="selectedPaper.source_file">
                {{ selectedPaper.source_file.split('/').pop().split('\\\\').pop() }}
              </span>
              <span v-if="selectedPaper.photo_restriction"
                    class="ml-auto shrink-0 text-red-500 text-sm" title="사진 사용 제한">🚫</span>
            </div>
          </div>

          <!-- 로딩 -->
          <div v-if="detailLoading" class="flex-1 flex items-center justify-center">
            <div class="w-6 h-6 border-2 border-blue-400 border-t-transparent rounded-full animate-spin"></div>
          </div>

          <!-- 콘텐츠 -->
          <div v-else-if="detailData" class="flex-1 overflow-auto p-5 space-y-5">

            <!-- 🚫 사진 사용 제한 경고 -->
            <div v-if="detailData.photo_restriction"
                 class="bg-red-600 text-white rounded-lg p-4 shadow-md border-2 border-red-700">
              <div class="flex items-start gap-3">
                <span class="text-2xl shrink-0">🚫</span>
                <div>
                  <p class="font-bold text-sm mb-1">사진 사용 제한</p>
                  <p class="text-sm opacity-95 leading-relaxed">{{ detailData.photo_restriction }}</p>
                </div>
              </div>
            </div>

            <!-- 쉬운 요약 (최상단) -->
            <section v-if="detailData.easy_summary">
              <h4 class="text-sm font-bold text-slate-700 mb-2 flex items-center gap-1.5">
                <span class="w-5 h-5 bg-amber-100 text-amber-600 rounded flex items-center justify-center text-xs font-bold">E</span>
                쉬운 요약
              </h4>
              <div class="bg-amber-50/70 border border-amber-200 rounded-lg p-4">
                <p class="text-sm text-slate-700 leading-relaxed whitespace-pre-line">{{ detailData.easy_summary }}</p>
              </div>
            </section>

            <section v-if="detailData.one_line_summary">
              <h4 class="text-sm font-bold text-slate-700 mb-2 flex items-center gap-1.5">
                <span class="w-5 h-5 bg-blue-100 text-blue-600 rounded flex items-center justify-center text-xs font-bold">S</span>
                한 줄 요약
              </h4>
              <div class="bg-blue-50/50 border border-blue-100 rounded-lg p-4">
                <p class="text-sm text-slate-700 leading-relaxed whitespace-pre-line">{{ detailData.one_line_summary }}</p>
              </div>
            </section>

            <section v-if="detailData.key_findings">
              <h4 class="text-sm font-bold text-slate-700 mb-2 flex items-center gap-1.5">
                <span class="w-5 h-5 bg-emerald-100 text-emerald-600 rounded flex items-center justify-center text-xs font-bold">R</span>
                핵심 결과
              </h4>
              <div class="bg-emerald-50/50 border border-emerald-100 rounded-lg p-4">
                <p class="text-sm text-slate-700 leading-relaxed whitespace-pre-line">{{ detailData.key_findings }}</p>
              </div>
            </section>

            <section v-if="detailData.research_purpose">
              <h4 class="text-sm font-bold text-slate-700 mb-2">1) 연구 목적</h4>
              <p class="text-sm text-slate-600 leading-relaxed whitespace-pre-line bg-slate-50 rounded-lg p-4">{{ detailData.research_purpose }}</p>
            </section>

            <section v-if="detailData.study_design_detail">
              <h4 class="text-sm font-bold text-slate-700 mb-2">2) 연구 설계 및 방법</h4>
              <p class="text-sm text-slate-600 leading-relaxed whitespace-pre-line bg-slate-50 rounded-lg p-4">{{ detailData.study_design_detail }}</p>
            </section>

            <section v-if="detailData.key_results">
              <h4 class="text-sm font-bold text-slate-700 mb-2">3) 핵심 결과</h4>
              <p class="text-sm text-slate-600 leading-relaxed whitespace-pre-line bg-slate-50 rounded-lg p-4">{{ detailData.key_results }}</p>
            </section>

            <section v-if="detailData.conclusion">
              <h4 class="text-sm font-bold text-slate-700 mb-2">4) 연구 결론</h4>
              <p class="text-sm text-slate-600 leading-relaxed whitespace-pre-line bg-slate-50 rounded-lg p-4">{{ detailData.conclusion }}</p>
            </section>

            <section v-if="detailData.cautions">
              <h4 class="text-sm font-bold text-slate-700 mb-2 flex items-center gap-1.5">
                <span class="w-5 h-5 bg-amber-100 text-amber-600 rounded flex items-center justify-center text-xs font-bold">!</span>
                해석 시 주의점
              </h4>
              <div class="bg-amber-50/50 border border-amber-100 rounded-lg p-4">
                <p class="text-sm text-slate-600 leading-relaxed whitespace-pre-line">{{ detailData.cautions }}</p>
              </div>
            </section>

            <section v-if="detailData.keywords && detailData.keywords !== '[]'">
              <h4 class="text-sm font-bold text-slate-700 mb-2">키워드</h4>
              <div class="flex flex-wrap gap-1.5">
                <span v-for="kw in parseKeywords(detailData.keywords)" :key="kw"
                  class="px-2 py-1 bg-slate-100 text-slate-600 rounded text-xs">{{ kw }}</span>
              </div>
            </section>
          </div>
        </div>
      </div>
    </div>

    <!-- ===== JSON 업로드 모달 ===== -->
    <Teleport to="body">
      <div v-if="showUploadModal" class="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
        <div class="bg-white rounded-xl shadow-2xl w-full max-w-lg p-6">
          <div class="flex items-center justify-between mb-4">
            <h3 class="text-lg font-bold text-slate-800">논문 분석 결과 업로드</h3>
            <button @click="closeUploadModal" class="text-slate-400 hover:text-slate-600 text-xl">&times;</button>
          </div>

          <p class="text-xs text-slate-500 mb-4">
            <code>paper_analyzer.py</code>로 생성된 JSON 파일을 업로드하면 논문 DB에 일괄 등록됩니다.
            중복 논문(DOI/제목 동일)은 자동으로 건너뜁니다.
          </p>

          <div class="mb-4">
            <input type="file" accept=".json" @change="onFileSelect"
              class="w-full text-sm text-slate-500 file:mr-3 file:py-2 file:px-4 file:rounded-md
                     file:border-0 file:text-sm file:font-medium file:bg-blue-50 file:text-blue-700
                     hover:file:bg-blue-100 cursor-pointer" />
          </div>

          <button @click="doUpload"
            :disabled="!uploadFile || uploading"
            class="w-full py-2.5 rounded-md text-sm font-medium transition
                   disabled:bg-slate-200 disabled:text-slate-400 disabled:cursor-not-allowed
                   bg-blue-600 text-white hover:bg-blue-700">
            <template v-if="uploading">
              <span class="inline-block w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2 align-middle"></span>
              업로드 중...
            </template>
            <template v-else>업로드</template>
          </button>

          <!-- 결과 -->
          <div v-if="uploadResult" class="mt-4 p-4 rounded-lg border" :class="uploadResult.inserted > 0 ? 'bg-emerald-50 border-emerald-200' : 'bg-amber-50 border-amber-200'">
            <p class="text-sm font-medium" :class="uploadResult.inserted > 0 ? 'text-emerald-700' : 'text-amber-700'">
              {{ uploadResult.message }}
            </p>

            <div v-if="uploadResult.duplicates.length" class="mt-2">
              <p class="text-xs text-slate-500 mb-1">중복 건너뜀:</p>
              <ul class="text-xs text-slate-500 space-y-0.5">
                <li v-for="(dup, i) in uploadResult.duplicates" :key="i" class="truncate">
                  · {{ dup.title }} <span class="text-slate-400">({{ dup.reason }})</span>
                </li>
              </ul>
            </div>

            <div v-if="uploadResult.errors.length" class="mt-2">
              <p class="text-xs text-red-500 mb-1">오류:</p>
              <ul class="text-xs text-red-400 space-y-0.5">
                <li v-for="(err, i) in uploadResult.errors" :key="i">
                  · #{{ err.index }}: {{ err.error }}
                </li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

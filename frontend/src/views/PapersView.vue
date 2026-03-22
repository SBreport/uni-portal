<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { usePapersStore, type Paper } from '@/stores/papers'
import * as papersApi from '@/api/papers'

const store = usePapersStore()

const selectedPaper = ref<Paper | null>(null)
const detailLoading = ref(false)
const detailData = ref<Paper | null>(null)

onMounted(() => {
  store.loadPapers()
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
      <span class="text-xs text-slate-400">{{ store.papers.length }}건</span>
    </div>

    <!-- 필터 바 -->
    <div class="flex items-center gap-3 mb-3 flex-wrap">
      <select v-model="store.filterStatus" @change="handleSearch"
        class="px-3 py-1.5 border border-slate-300 rounded-md text-sm bg-white">
        <option value="">전체 상태</option>
        <option value="draft">초안</option>
        <option value="reviewed">검토됨</option>
        <option value="verified">검증됨</option>
      </select>

      <input v-model="store.filterSearch" placeholder="제목, 저자, 키워드 검색"
        class="px-3 py-1.5 border border-slate-300 rounded-md text-sm w-64 focus:outline-none focus:ring-1 focus:ring-blue-400"
        @input="handleSearch" />
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
          </div>

          <!-- 로딩 -->
          <div v-if="detailLoading" class="flex-1 flex items-center justify-center">
            <div class="w-6 h-6 border-2 border-blue-400 border-t-transparent rounded-full animate-spin"></div>
          </div>

          <!-- 콘텐츠 -->
          <div v-else-if="detailData" class="flex-1 overflow-auto p-5 space-y-5">

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
  </div>
</template>

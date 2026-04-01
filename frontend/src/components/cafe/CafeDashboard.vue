<script setup lang="ts">
import { onMounted, computed, ref } from 'vue'
import { useCafeStore, type SummaryRow } from '@/stores/cafe'

const emit = defineEmits<{ 'go-branch': [branchName: string] }>()
const store = useCafeStore()

// loadSummary는 CafeView에서 이미 호출 — 여기서 중복 호출하지 않음

// 접이식 유형별 상세
const showTypeDetail = ref(false)

// 확장된 행 (지점명 기준)
const expandedRows = ref<Set<string>>(new Set())
function toggleRow(name: string) {
  if (expandedRows.value.has(name)) expandedRows.value.delete(name)
  else expandedRows.value.add(name)
}

// KPI 계산
const kpi = computed(() => {
  const s = store.summary
  const total = s.reduce((a, r) => a + (r.total || 0), 0)
  const published = s.reduce((a, r) => a + (r['발행완료'] || 0), 0)
  const pending = s.reduce((a, r) => a + (r['작성대기'] || 0), 0)
  const rate = total > 0 ? Math.round((published / total) * 100) : 0
  return { total, published, pending, rate, branches: s.length }
})

// 진행률 계산
function progressRate(row: SummaryRow): number {
  if (!row.total) return 0
  return Math.round((row['발행완료'] / row.total) * 100)
}

// 진행상황 텍스트
function progressText(row: SummaryRow): string {
  const done = (row['작성완료'] || 0) + (row['검수완료'] || 0) + (row['발행완료'] || 0)
  return `${done} / ${row.total || 0}`
}

// 진행률 바 색상
function progressBarColor(rate: number): string {
  if (rate >= 80) return '#10b981'
  if (rate >= 50) return '#f59e0b'
  if (rate > 0) return '#3b82f6'
  return '#e2e8f0'
}
</script>

<template>
  <div>
    <!-- KPI 카드 -->
    <div class="grid grid-cols-5 gap-3 mb-5">
      <div v-for="item in [
        { label: '전체 원고', value: kpi.total, color: 'text-slate-700' },
        { label: '발행 완료', value: kpi.published, color: 'text-emerald-600' },
        { label: '미착수', value: kpi.pending, color: 'text-slate-400' },
        { label: '발행률', value: kpi.rate + '%', color: 'text-blue-600' },
        { label: '지점 수', value: kpi.branches, color: 'text-slate-500' },
      ]" :key="item.label"
        class="bg-white rounded-lg border border-slate-200 p-4"
      >
        <p class="text-xs text-slate-400">{{ item.label }}</p>
        <p class="text-2xl font-bold mt-1" :class="item.color">{{ item.value }}</p>
      </div>
    </div>

    <!-- 유형별 상세 토글 -->
    <div class="flex items-center gap-3 mb-3">
      <span class="text-xs text-slate-400">{{ store.summary.length }}건</span>
      <button
        @click="showTypeDetail = !showTypeDetail"
        class="text-xs px-2.5 py-1 rounded-md border transition"
        :class="showTypeDetail
          ? 'bg-blue-50 border-blue-300 text-blue-600'
          : 'bg-white border-slate-200 text-slate-500 hover:bg-slate-50'"
      >
        {{ showTypeDetail ? '▼ 유형별 상세 접기' : '▶ 유형별 상세 (정보성·후기성·슈퍼세트)' }}
      </button>
    </div>

    <!-- 메인 테이블 -->
    <div class="border border-slate-200 rounded-lg overflow-hidden">
      <div class="overflow-auto" style="max-height: calc(100vh - 320px)">
        <table class="w-full text-xs">
          <thead class="bg-slate-50 sticky top-0 z-10">
            <tr class="border-b border-slate-200">
              <th class="th-cell" style="width:90px">지점</th>
              <th class="th-cell" style="width:70px">담당자</th>
              <th class="th-cell" style="width:70px">작가</th>
              <th class="th-cell text-center" style="width:50px">총건수</th>
              <th class="th-cell" style="width:140px">진행상황</th>
              <!-- 유형별 상세 (토글) -->
              <template v-if="showTypeDetail">
                <th class="th-cell text-center th-type" style="width:70px">정보성</th>
                <th class="th-cell text-center th-type" style="width:70px">후기성</th>
                <th class="th-cell text-center th-type" style="width:70px">슈퍼세트</th>
              </template>
              <th class="th-cell">비고</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="(row, idx) in store.summary"
              :key="row.branch_name"
              class="border-b border-slate-100 hover:bg-blue-50/50 transition-colors cursor-pointer"
              :class="{ 'bg-slate-50/50': idx % 2 === 1 }"
              @click="emit('go-branch', row.branch_name)"
            >
              <!-- 지점 -->
              <td class="td-cell font-medium text-slate-800">
                {{ row.branch_name }}
              </td>

              <!-- 담당자 -->
              <td class="td-cell text-slate-500">
                {{ row.smart_manager || '—' }}
              </td>

              <!-- 작가 -->
              <td class="td-cell text-slate-500">
                {{ row.writer || '—' }}
              </td>

              <!-- 총건수 -->
              <td class="td-cell text-center font-semibold text-slate-700">
                {{ row.total || 0 }}
              </td>

              <!-- 진행상황 (프로그레스 바 + 텍스트) -->
              <td class="td-cell">
                <div class="flex items-center gap-2">
                  <div class="flex-1 h-2 bg-slate-100 rounded-full overflow-hidden">
                    <div
                      class="h-full rounded-full transition-all duration-300"
                      :style="{
                        width: progressRate(row) + '%',
                        backgroundColor: progressBarColor(progressRate(row))
                      }"
                    ></div>
                  </div>
                  <span class="text-[10px] text-slate-500 whitespace-nowrap w-14 text-right">
                    {{ progressText(row) }}
                  </span>
                  <span class="text-[10px] font-semibold w-8 text-right"
                    :style="{ color: progressBarColor(progressRate(row)) }">
                    {{ progressRate(row) }}%
                  </span>
                </div>
              </td>

              <!-- 유형별 상세 (토글) -->
              <template v-if="showTypeDetail">
                <td class="td-cell text-center td-type">
                  <span v-if="row.cnt_info" class="type-count">
                    {{ row.cnt_info_done }}/{{ row.cnt_info }}
                  </span>
                  <span v-else class="text-slate-200">—</span>
                </td>
                <td class="td-cell text-center td-type">
                  <span v-if="row.cnt_review_type" class="type-count">
                    {{ row.cnt_review_done }}/{{ row.cnt_review_type }}
                  </span>
                  <span v-else class="text-slate-200">—</span>
                </td>
                <td class="td-cell text-center td-type">
                  <span v-if="row.cnt_superset" class="type-count">
                    {{ row.cnt_superset_done }}/{{ row.cnt_superset }}
                  </span>
                  <span v-else class="text-slate-200">—</span>
                </td>
              </template>

              <!-- 비고 -->
              <td class="td-cell text-slate-400">
                <span v-if="row.progress_note" class="note-tag">{{ row.progress_note }}</span>
                <span v-else>—</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<style scoped>
.th-cell {
  padding: 8px 10px;
  text-align: left;
  font-size: 11px;
  font-weight: 600;
  color: #64748b;
  white-space: nowrap;
}
.td-cell {
  padding: 7px 10px;
  font-size: 11px;
  vertical-align: middle;
}
.th-type {
  background: #eff6ff;
}
.td-type {
  background: #fafbff;
}
.type-count {
  font-weight: 600;
  color: #334155;
}

/* 비고 태그 */
.note-tag {
  font-size: 10px;
  color: #64748b;
  background: #f1f5f9;
  padding: 1px 6px;
  border-radius: 3px;
}
</style>

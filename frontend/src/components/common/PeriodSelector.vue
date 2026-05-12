<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { getPeriods } from '@/api/events'

interface Period {
  id: number
  label: string
  year: number
  start_month: number
  end_month: number
  is_current: boolean
}

const props = defineProps<{
  periodId: number | null
}>()

const emit = defineEmits<{
  'update:periodId': [value: number | null]
}>()

const periods = ref<Period[]>([])
const loading = ref(false)
const error = ref(false)

function formatLabel(p: Period): string {
  const yy = String(p.year).slice(2)
  const label = `${yy}.${p.start_month}~${p.end_month}`
  return p.is_current ? `${label} (현재)` : label
}

onMounted(async () => {
  loading.value = true
  error.value = false
  try {
    const res = await getPeriods()
    periods.value = res.data ?? []
    // 아직 선택된 기간이 없으면 현재 기간을 자동 선택
    if (props.periodId == null) {
      const current = periods.value.find(p => p.is_current)
      if (current) emit('update:periodId', current.id)
    }
  } catch (e) {
    console.error('[PeriodSelector] 기간 목록 로드 실패:', e)
    error.value = true
  } finally {
    loading.value = false
  }
})

function onChange(e: Event) {
  const val = (e.target as HTMLSelectElement).value
  emit('update:periodId', val ? Number(val) : null)
}
</script>

<template>
  <div class="flex items-center gap-1.5 shrink-0">
    <span class="text-xs text-slate-400">기간</span>
    <select
      :value="periodId ?? ''"
      :disabled="loading || error || !periods.length"
      @change="onChange"
      class="px-2 py-1 border border-slate-300 rounded-md text-sm bg-white
             focus:outline-none focus:ring-1 focus:ring-blue-500
             disabled:bg-slate-50 disabled:text-slate-400 disabled:cursor-not-allowed"
    >
      <option v-if="loading" value="" disabled>로딩 중...</option>
      <option v-else-if="error" value="" disabled>오류</option>
      <option v-else-if="!periods.length" value="" disabled>기간 없음</option>
      <template v-else>
        <option
          v-for="p in periods"
          :key="p.id"
          :value="p.id"
        >{{ formatLabel(p) }}</option>
      </template>
    </select>
  </div>
</template>

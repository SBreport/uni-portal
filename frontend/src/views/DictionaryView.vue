<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import * as equipApi from '@/api/equipment'

// ── 시술 사전 데이터 ──
const devices = ref<any[]>([])
const loading = ref(false)
const searchQuery = ref('')

const dictForm = ref({ name: '', category: '', aliases: '', summary: '', target: '', mechanism: '', note: '' })
const dictMsg = ref('')
const showForm = ref(false)

// 필터링
const filteredDevices = computed(() => {
  if (!searchQuery.value.trim()) return devices.value
  const q = searchQuery.value.toLowerCase()
  return devices.value.filter(d =>
    d.name?.toLowerCase().includes(q) ||
    d.category?.toLowerCase().includes(q) ||
    d.summary?.toLowerCase().includes(q) ||
    d.aliases?.toLowerCase().includes(q)
  )
})

// 카테고리 통계
const categoryStats = computed(() => {
  const map: Record<string, number> = {}
  devices.value.forEach(d => {
    const cat = d.category || '미분류'
    map[cat] = (map[cat] || 0) + 1
  })
  return Object.entries(map).sort((a, b) => b[1] - a[1])
})

async function loadDevices() {
  loading.value = true
  try { devices.value = (await equipApi.getDeviceInfo()).data }
  finally { loading.value = false }
}
onMounted(() => loadDevices())

async function saveDevice() {
  if (!dictForm.value.name.trim()) return
  await equipApi.upsertDeviceInfo({ ...dictForm.value, is_verified: 1 })
  dictMsg.value = `'${dictForm.value.name}' 저장 완료`
  dictForm.value = { name: '', category: '', aliases: '', summary: '', target: '', mechanism: '', note: '' }
  await loadDevices()
  setTimeout(() => dictMsg.value = '', 3000)
}

async function deleteDevice(name: string) {
  if (!confirm(`'${name}' 시술 정보를 삭제하시겠습니까?`)) return
  await equipApi.deleteDeviceInfo(name)
  await loadDevices()
}

async function updateCounts() {
  await equipApi.updateDeviceCounts()
  dictMsg.value = '보유수 업데이트 완료'
  await loadDevices()
  setTimeout(() => dictMsg.value = '', 3000)
}

async function syncJson() {
  await equipApi.syncDeviceJson()
  dictMsg.value = 'JSON → DB 동기화 완료'
  await loadDevices()
  setTimeout(() => dictMsg.value = '', 3000)
}

function editDevice(d: any) {
  dictForm.value = {
    name: d.name || '',
    category: d.category || '',
    aliases: d.aliases || '',
    summary: d.summary || '',
    target: d.target || '',
    mechanism: d.mechanism || '',
    note: d.note || '',
  }
  showForm.value = true
}
</script>

<template>
  <div class="p-5">
    <div class="flex items-center justify-between mb-4">
      <h2 class="text-xl font-bold text-slate-800">시술사전</h2>
      <div class="flex gap-2">
        <button @click="updateCounts" class="px-3 py-1.5 border border-slate-200 rounded text-xs hover:bg-slate-50">보유수 업데이트</button>
        <button @click="syncJson" class="px-3 py-1.5 border border-slate-200 rounded text-xs hover:bg-slate-50">JSON → DB 동기화</button>
        <button @click="showForm = !showForm"
          class="px-3 py-1.5 bg-blue-600 text-white text-xs rounded hover:bg-blue-700">
          {{ showForm ? '폼 닫기' : '+ 시술 추가' }}
        </button>
      </div>
    </div>

    <!-- 알림 -->
    <div v-if="dictMsg" class="mb-3 px-4 py-2 bg-emerald-50 border border-emerald-200 rounded text-sm text-emerald-700">{{ dictMsg }}</div>

    <!-- KPI -->
    <div class="grid grid-cols-4 gap-3 mb-4">
      <div class="bg-white border border-slate-200 rounded-lg px-4 py-3 text-center">
        <p class="text-2xl font-bold text-slate-800">{{ devices.length }}</p>
        <p class="text-xs text-slate-400">전체 시술</p>
      </div>
      <div class="bg-white border border-slate-200 rounded-lg px-4 py-3 text-center">
        <p class="text-2xl font-bold text-emerald-600">{{ devices.filter(d => d.is_verified).length }}</p>
        <p class="text-xs text-slate-400">검증 완료</p>
      </div>
      <div class="bg-white border border-slate-200 rounded-lg px-4 py-3 text-center">
        <p class="text-2xl font-bold text-amber-600">{{ devices.filter(d => !d.is_verified).length }}</p>
        <p class="text-xs text-slate-400">미검증</p>
      </div>
      <div class="bg-white border border-slate-200 rounded-lg px-4 py-3 text-center">
        <p class="text-2xl font-bold text-blue-600">{{ categoryStats.length }}</p>
        <p class="text-xs text-slate-400">카테고리 수</p>
      </div>
    </div>

    <!-- 추가/수정 폼 -->
    <div v-if="showForm" class="bg-white border border-slate-200 rounded-lg p-4 mb-4">
      <h3 class="text-sm font-bold text-slate-700 mb-3">시술 정보 {{ dictForm.name ? '수정' : '추가' }}</h3>
      <div class="space-y-2">
        <div class="grid grid-cols-3 gap-2">
          <input v-model="dictForm.name" placeholder="시술명 (필수)" class="px-3 py-1.5 border border-slate-300 rounded text-sm" />
          <input v-model="dictForm.category" placeholder="카테고리" class="px-3 py-1.5 border border-slate-300 rounded text-sm" />
          <input v-model="dictForm.aliases" placeholder="별칭 (쉼표 구분)" class="px-3 py-1.5 border border-slate-300 rounded text-sm" />
        </div>
        <textarea v-model="dictForm.summary" placeholder="한줄 설명" rows="2" class="w-full px-3 py-1.5 border border-slate-300 rounded text-sm" />
        <div class="grid grid-cols-2 gap-2">
          <input v-model="dictForm.target" placeholder="적용 부위" class="px-3 py-1.5 border border-slate-300 rounded text-sm" />
          <input v-model="dictForm.note" placeholder="참고" class="px-3 py-1.5 border border-slate-300 rounded text-sm" />
        </div>
        <textarea v-model="dictForm.mechanism" placeholder="작용 원리" rows="2" class="w-full px-3 py-1.5 border border-slate-300 rounded text-sm" />
        <div class="flex gap-2">
          <button @click="saveDevice" class="px-4 py-2 bg-emerald-600 text-white text-sm rounded hover:bg-emerald-700">저장</button>
          <button @click="showForm = false; dictForm = { name: '', category: '', aliases: '', summary: '', target: '', mechanism: '', note: '' }"
            class="px-4 py-2 border border-slate-200 text-sm rounded hover:bg-slate-50">취소</button>
        </div>
      </div>
    </div>

    <!-- 검색 -->
    <div class="mb-3">
      <input v-model="searchQuery" placeholder="시술명, 카테고리, 별칭으로 검색..."
        class="w-full px-4 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
    </div>

    <!-- 테이블 -->
    <div class="bg-white border border-slate-200 rounded-lg overflow-hidden">
      <table class="w-full text-sm">
        <thead class="bg-slate-50 border-b border-slate-200">
          <tr>
            <th class="text-left px-3 py-2 font-medium text-slate-500">시술명</th>
            <th class="text-left px-3 py-2 font-medium text-slate-500">카테고리</th>
            <th class="text-left px-3 py-2 font-medium text-slate-500">설명</th>
            <th class="text-left px-3 py-2 font-medium text-slate-500">별칭</th>
            <th class="text-center px-3 py-2 font-medium text-slate-500">보유수</th>
            <th class="text-center px-3 py-2 font-medium text-slate-500">검증</th>
            <th class="text-right px-3 py-2 font-medium text-slate-500"></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="d in filteredDevices" :key="d.name" class="border-b border-slate-100 hover:bg-slate-50">
            <td class="px-3 py-1.5 font-medium">{{ d.name }}</td>
            <td class="px-3 py-1.5">
              <span class="px-2 py-0.5 bg-slate-100 rounded text-xs text-slate-600">{{ d.category || '-' }}</span>
            </td>
            <td class="px-3 py-1.5 text-slate-400 text-xs truncate max-w-xs">{{ d.summary || '-' }}</td>
            <td class="px-3 py-1.5 text-slate-400 text-xs truncate max-w-[160px]">{{ d.aliases || '-' }}</td>
            <td class="px-3 py-1.5 text-center">{{ d.usage_count }}</td>
            <td class="px-3 py-1.5 text-center">{{ d.is_verified ? '✅' : '' }}</td>
            <td class="px-3 py-1.5 text-right space-x-2">
              <button @click="editDevice(d)" class="text-blue-500 hover:text-blue-700 text-xs">수정</button>
              <button @click="deleteDevice(d.name)" class="text-red-400 hover:text-red-600 text-xs">삭제</button>
            </td>
          </tr>
        </tbody>
      </table>
      <p class="px-3 py-2 text-xs text-slate-400">
        {{ searchQuery ? `검색 결과: ${filteredDevices.length}건` : `총 ${devices.length}건` }}
      </p>
    </div>
  </div>
</template>

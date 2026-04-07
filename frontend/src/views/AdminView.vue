<script setup lang="ts">
import { ref, computed, onMounted, defineAsyncComponent } from 'vue'
import { useBranchStore } from '@/stores/branches'
import UserManagement from '@/components/admin/UserManagement.vue'
import SyncSettings from '@/components/admin/SyncSettings.vue'
import RankChecker from '@/components/admin/RankChecker.vue'
import EncyclopediaAdmin from '@/components/admin/EncyclopediaAdmin.vue'
import TabBar from '@/components/common/TabBar.vue'

// 정보관리 서브뷰 — lazy load (기존 개별 페이지를 재활용)
const BranchInfoView = defineAsyncComponent(() => import('@/views/BranchInfoView.vue'))
const EquipmentView = defineAsyncComponent(() => import('@/views/EquipmentView.vue'))
const EventsView = defineAsyncComponent(() => import('@/views/EventsView.vue'))
const TreatmentInfoView = defineAsyncComponent(() => import('@/views/TreatmentInfoView.vue'))

const branchStore = useBranchStore()
type AdminTab = 'users' | 'sync' | 'rank-checker' | 'encyclopedia' | 'info'
const activeTab = ref<AdminTab>('users')
const branches = computed(() => branchStore.branches)

const tabs = [
  { key: 'users', label: '사용자' },
  { key: 'sync', label: '데이터 동기화' },
  { key: 'rank-checker', label: 'SB체커' },
  { key: 'encyclopedia', label: '백과사전 관리' },
  { key: 'info', label: '정보관리' },
]

// 정보관리 서브탭
type InfoTab = 'branch' | 'equipment' | 'events' | 'treatment'
const infoTab = ref<InfoTab>('branch')
const infoTabs = [
  { key: 'branch', label: '지점 정보' },
  { key: 'equipment', label: '보유장비' },
  { key: 'events', label: '이벤트' },
  { key: 'treatment', label: '시술정보' },
]

onMounted(() => branchStore.loadBranches())
</script>

<template>
  <div class="p-5">
    <h2 class="text-xl font-bold text-slate-800 mb-4">관리자 모드</h2>

    <TabBar :model-value="activeTab" :tabs="tabs" @update:model-value="(v: string) => activeTab = v as AdminTab" />

    <UserManagement v-if="activeTab === 'users'" :branches="branches" />
    <SyncSettings v-if="activeTab === 'sync'" :branches="branches" />
    <RankChecker v-if="activeTab === 'rank-checker'" :branches="branches" />
    <EncyclopediaAdmin v-if="activeTab === 'encyclopedia'" />

    <!-- 정보관리: 기존 개별 뷰를 서브탭으로 배치 -->
    <div v-if="activeTab === 'info'" class="mt-4">
      <div class="flex gap-1 mb-4 border-b border-slate-200">
        <button
          v-for="t in infoTabs"
          :key="t.key"
          @click="infoTab = t.key as InfoTab"
          :class="[
            'px-3 py-2 text-sm font-medium transition border-b-2 -mb-px',
            infoTab === t.key
              ? 'border-slate-700 text-slate-800'
              : 'border-transparent text-slate-400 hover:text-slate-600'
          ]"
        >
          {{ t.label }}
        </button>
      </div>
      <BranchInfoView v-if="infoTab === 'branch'" />
      <EquipmentView v-if="infoTab === 'equipment'" />
      <EventsView v-if="infoTab === 'events'" />
      <TreatmentInfoView v-if="infoTab === 'treatment'" />
    </div>
  </div>
</template>

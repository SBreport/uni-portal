<script setup lang="ts">
import { ref } from 'vue'
import { useRoute } from 'vue-router'
import TabBar from '@/components/common/TabBar.vue'
import { defineAsyncComponent } from 'vue'

const BranchInfoView = defineAsyncComponent(() => import('@/views/BranchInfoView.vue'))
const EquipmentView = defineAsyncComponent(() => import('@/views/EquipmentView.vue'))
const EventsView = defineAsyncComponent(() => import('@/views/EventsView.vue'))
const TreatmentInfoView = defineAsyncComponent(() => import('@/views/TreatmentInfoView.vue'))

const route = useRoute()

const tabs = [
  { key: 'branch', label: '지점 정보' },
  { key: 'equipment', label: '보유장비' },
  { key: 'events', label: '이벤트' },
  { key: 'treatment', label: '시술정보' },
]

// URL query로 초기 탭 설정 가능 (예: /info?tab=events)
const activeTab = ref((route.query.tab as string) || 'branch')
</script>

<template>
  <div class="p-5 max-w-4xl">
    <div class="mb-5">
      <h2 class="text-xl font-bold text-slate-800">정보 관리</h2>
      <p class="text-sm text-slate-400 mt-1">지점 · 장비 · 이벤트 · 시술 정보를 조회하고 관리합니다</p>
    </div>

    <TabBar :tabs="tabs" v-model="activeTab" class="mb-4" />

    <BranchInfoView v-if="activeTab === 'branch'" :embedded="true" />
    <EquipmentView v-else-if="activeTab === 'equipment'" :embedded="true" />
    <EventsView v-else-if="activeTab === 'events'" :embedded="true" />
    <TreatmentInfoView v-else-if="activeTab === 'treatment'" :embedded="true" />
  </div>
</template>

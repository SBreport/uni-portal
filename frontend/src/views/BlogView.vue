<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import BlogDashboard from '@/components/blog/BlogDashboard.vue'
import BlogListTab from '@/components/blog/BlogListTab.vue'
import BlogAccounts from '@/components/blog/BlogAccounts.vue'
import TabBar from '@/components/common/TabBar.vue'

const props = defineProps<{
  mode?: 'uandi' | 'all'
}>()

const route = useRoute()

const isUandi = computed(() => props.mode !== 'all')
const pageTitle = computed(() => isUandi.value ? '블로그 관리' : '블로그 관리 (전체)')

// ── 탭 ──
const activeTab = ref<'dashboard' | 'list' | 'accounts'>('dashboard')
const tabs = [
  { key: 'dashboard', label: '대시보드' },
  { key: 'list', label: '목록' },
  { key: 'accounts', label: '계정관리' },
]

// ── 대시보드 → 목록 이동 시 필터 전달 ──
// undefined: 필터 없이 일반 진입, object: 대시보드에서 필터 지정 진입
const listFilters = ref<Record<string, any> | undefined>(undefined)
const listMounted = ref(false)

function onDashboardNavigate(_tab: string, filter?: Record<string, any>) {
  listFilters.value = filter ?? {}
  listMounted.value = true
  activeTab.value = 'list'
}

function onTabClick(tab: string) {
  activeTab.value = tab as 'dashboard' | 'list' | 'accounts'
  if (tab === 'list' && !listMounted.value) {
    listMounted.value = true
    listFilters.value = undefined
  }
}

// URL query에서 필터 읽기 (탐색기 등 외부에서 이동 시)
onMounted(() => {
  if (route.query.channel || route.query.branch_name) {
    const filter: Record<string, any> = {}
    if (route.query.channel) filter.channel = route.query.channel as string
    if (route.query.branch_name) filter.branch_name = route.query.branch_name as string
    listFilters.value = filter
    listMounted.value = true
    activeTab.value = 'list'
  }
})
</script>

<template>
  <div class="p-5 h-[calc(100vh-1rem)] flex flex-col">
    <!-- 헤더 -->
    <div class="flex items-center justify-between mb-4">
      <div>
        <h2 class="text-xl font-bold text-slate-800">{{ pageTitle }}</h2>
      </div>
    </div>

    <!-- 탭 바 -->
    <TabBar :model-value="activeTab" :tabs="tabs" @update:model-value="onTabClick" />

    <!-- 대시보드 탭 -->
    <div v-if="activeTab === 'dashboard'" class="flex-1 overflow-auto min-h-0">
      <BlogDashboard
        :branch-filter="isUandi ? 'uandi' : undefined"
        :hide-author="isUandi"
        @navigate="onDashboardNavigate"
      />
    </div>

    <!-- 목록 탭: 최초 진입 시 마운트 후 v-show로 유지 (상태 보존) -->
    <template v-if="listMounted">
      <BlogListTab
        v-show="activeTab === 'list'"
        :mode="props.mode === 'all' ? 'all' : 'uandi'"
        :initial-filters="listFilters"
      />
    </template>

    <!-- 계정관리 탭 -->
    <BlogAccounts v-if="activeTab === 'accounts'" :branch-filter="isUandi ? 'uandi' : undefined" />
  </div>
</template>

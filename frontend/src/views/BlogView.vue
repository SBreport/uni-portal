<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import BlogDashboard from '@/components/blog/BlogDashboard.vue'
import BlogListTab from '@/components/blog/BlogListTab.vue'
import BlogAccounts from '@/components/blog/BlogAccounts.vue'
import TabBar from '@/components/common/TabBar.vue'

const props = defineProps<{
  mode?: 'uandi' | 'all'
}>()

const route = useRoute()
const router = useRouter()

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

function onDashboardNavigate(_tab: string, filter?: Record<string, any>) {
  listFilters.value = filter ?? {}
  activeTab.value = 'list'
}

function onTabClick(tab: string) {
  if (tab !== 'list') listFilters.value = undefined
  activeTab.value = tab as 'dashboard' | 'list' | 'accounts'
}

// 탭 변경 시 URL 업데이트
watch(activeTab, (t) => {
  router.replace({ query: { ...route.query, tab: t === 'dashboard' ? undefined : t } })
})

// URL query에서 필터 읽기 (탐색기 등 외부에서 이동 시, 탭 복원 포함)
onMounted(() => {
  const t = route.query.tab as string
  if (t === 'list' || t === 'accounts') {
    activeTab.value = t
  }

  if (route.query.channel || route.query.branch_name) {
    const filter: Record<string, any> = {}
    if (route.query.channel) filter.channel = route.query.channel as string
    if (route.query.branch_name) filter.branch_name = route.query.branch_name as string
    listFilters.value = filter
    activeTab.value = 'list'
  }
})
</script>

<template>
  <div class="px-4 pt-3 pb-0 h-[calc(100vh-1rem)] flex flex-col">
    <!-- 헤더 -->
    <div class="flex items-center gap-2 mb-2 flex-none">
      <h2 class="text-xl font-bold text-slate-800">{{ pageTitle }}</h2>
    </div>

    <!-- 탭 바 -->
    <div class="flex-none">
      <TabBar :model-value="activeTab" :tabs="tabs" @update:model-value="onTabClick" />
    </div>

    <!-- 탭 컨테이너 -->
    <div class="flex-1 min-h-0 overflow-hidden">
      <!-- 대시보드 탭 -->
      <div v-if="activeTab === 'dashboard'" class="h-full flex flex-col overflow-auto">
        <BlogDashboard
          :branch-filter="isUandi ? 'uandi' : undefined"
          :hide-author="isUandi"
          @navigate="onDashboardNavigate"
        />
      </div>

      <!-- 목록 탭 -->
      <BlogListTab
        v-if="activeTab === 'list'"
        :mode="props.mode === 'all' ? 'all' : 'uandi'"
        :initial-filters="listFilters"
      />

      <!-- 계정관리 탭 -->
      <BlogAccounts v-if="activeTab === 'accounts'" :branch-filter="isUandi ? 'uandi' : undefined" />
    </div>
  </div>
</template>

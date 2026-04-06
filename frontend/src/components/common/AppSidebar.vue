<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const auth = useAuthStore()

// 마케팅 트리 열림/닫힘
const marketingOpen = ref(true)

// 마케팅 하위 경로에 있으면 자동 펼침
const isMarketingActive = computed(() =>
  ['/cafe', '/blog', '/place', '/webpage'].some(p => route.path.startsWith(p))
)

// 단일 메뉴 항목
interface MenuItem {
  path: string
  label: string
  icon: string
  color?: string        // 비활성 아이콘 배경색
  colorActive?: string  // 활성 아이콘 배경색
  adminOnly?: boolean   // 하위 호환: admin 전용 여부
  roles?: string[]      // effectiveRole 기반 표시 제어
}

// roles 필터 헬퍼: roles가 없으면 모두 표시, 있으면 effectiveRole이 포함된 경우만 표시
function canSee(item: MenuItem): boolean {
  if (item.adminOnly) return auth.role === 'admin'
  if (item.roles) return item.roles.includes(auth.effectiveRole)
  return true
}

// 마케팅 하위 메뉴
const marketingChildren = computed<MenuItem[]>(() => [
  {
    path: '/cafe',
    label: '카페',
    icon: 'C',
    roles: ['admin', 'editor'],
  },
  {
    path: '/blog',
    label: '블로그',
    icon: 'B',
    roles: ['admin', 'editor'],
  },
  ...(auth.role === 'admin'
    ? [{ path: '/blog-all', label: '블로그(all)', icon: 'B', adminOnly: true } as MenuItem]
    : []),
  {
    path: '/place',
    label: '플레이스',
    icon: 'P',
    roles: ['admin', 'editor', 'viewer-hq', 'viewer-branch'],
  },
  {
    path: '/webpage',
    label: '웹페이지',
    icon: 'W',
    roles: ['admin', 'editor', 'viewer-hq', 'viewer-branch'],
  },
])

// 마케팅 하위 중 현재 사용자가 볼 수 있는 항목만
const visibleMarketingChildren = computed(() =>
  marketingChildren.value.filter(canSee)
)

// 최상위 메뉴 (마케팅 제외)
const topItems: MenuItem[] = [
  { path: '/', label: 'HOME', icon: 'H' },
  {
    path: '/branch-info',
    label: '지점 정보',
    icon: 'B',
    roles: ['admin', 'editor', 'viewer-hq', 'viewer-branch'],
  },
  {
    path: '/equipment',
    label: '보유장비',
    icon: 'E',
    roles: ['admin', 'editor', 'viewer-hq', 'viewer-branch'],
  },
  {
    path: '/events',
    label: '이벤트',
    icon: 'V',
    roles: ['admin', 'editor', 'viewer-hq', 'viewer-branch'],
  },
  {
    path: '/treatment-info',
    label: '시술정보',
    icon: 'T',
    roles: ['admin', 'editor'],
  },
  {
    path: '/complaints',
    label: '민원관리',
    icon: 'M',
    roles: ['admin', 'editor', 'viewer-hq', 'viewer-branch'],
  },
]

const visibleTopItems = computed(() => topItems.filter(canSee))

const bottomItems: MenuItem[] = [
  { path: '/reports', label: '보고서', icon: 'R' },
  { path: '/admin', label: '관리자 모드', icon: 'A', adminOnly: true },
]

const visibleBottomItems = computed(() => bottomItems.filter(canSee))

function isActive(path: string) {
  if (path === '/') return route.path === '/'
  // /blog vs /blog-all 구분
  if (path === '/blog') return route.path === '/blog'
  return route.path.startsWith(path)
}

function handleLogout() {
  auth.logout()
  window.location.href = '/login'
}
</script>

<template>
  <aside class="w-48 bg-white border-r border-slate-200 flex flex-col h-screen fixed left-0 top-0">
    <!-- 로고 -->
    <div class="px-5 py-6 border-b border-slate-100">
      <h1 class="text-base font-bold text-slate-800">유앤아이의원</h1>
      <p class="text-xs text-slate-400 mt-0.5">통합 관리 시스템</p>
    </div>

    <!-- 메뉴 -->
    <nav class="flex-1 py-4 px-3 space-y-0.5 overflow-auto">
      <!-- 상위 메뉴 -->
      <router-link
        v-for="item in visibleTopItems" :key="item.path"
        :to="item.path"
        :class="[
          'flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition',
          isActive(item.path)
            ? 'bg-blue-600 text-white font-semibold'
            : 'text-slate-600 hover:bg-slate-50'
        ]"
      >
        <span class="w-5 h-5 flex items-center justify-center text-xs font-bold rounded"
          :class="isActive(item.path) ? (item.colorActive || 'bg-blue-500 text-white') : (item.color || 'bg-slate-100 text-slate-500')"
        >{{ item.icon }}</span>
        {{ item.label }}
      </router-link>

      <!-- 마케팅 (트리) -->
      <div v-if="visibleMarketingChildren.length > 0" class="pt-0.5">
        <button
          @click="marketingOpen = !marketingOpen"
          :class="[
            'w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition',
            isMarketingActive
              ? 'bg-blue-50 text-blue-700 font-semibold'
              : 'text-slate-600 hover:bg-slate-50'
          ]"
        >
          <span class="w-5 h-5 flex items-center justify-center text-xs font-bold rounded"
            :class="isMarketingActive ? 'bg-blue-100 text-blue-600' : 'bg-slate-100 text-slate-500'"
          >M</span>
          <span class="flex-1 text-left">마케팅</span>
          <svg
            class="w-3.5 h-3.5 transition-transform duration-200"
            :class="{ 'rotate-90': marketingOpen || isMarketingActive }"
            fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"
          >
            <path stroke-linecap="round" stroke-linejoin="round" d="M9 5l7 7-7 7" />
          </svg>
        </button>

        <!-- 하위 메뉴 -->
        <transition name="tree">
          <div v-show="marketingOpen || isMarketingActive" class="ml-5 mt-0.5 space-y-0.5 border-l border-slate-200 pl-2">
            <router-link
              v-for="child in visibleMarketingChildren" :key="child.path"
              :to="child.path"
              :class="[
                'flex items-center gap-2 px-2.5 py-1.5 rounded-md text-[13px] transition',
                isActive(child.path)
                  ? 'bg-blue-600 text-white font-semibold'
                  : 'text-slate-500 hover:bg-slate-50 hover:text-slate-700'
              ]"
            >
              <span class="w-4 h-4 flex items-center justify-center text-[10px] font-bold rounded"
                :class="isActive(child.path) ? (child.colorActive || 'bg-blue-500 text-white') : (child.color || 'bg-slate-100 text-slate-400')"
              >{{ child.icon }}</span>
              {{ child.label }}
            </router-link>
          </div>
        </transition>
      </div>

      <!-- 구분선 -->
      <div class="!my-2 border-t border-slate-100"></div>

      <!-- 하위 메뉴 (보고서, 관리자) -->
      <router-link
        v-for="item in visibleBottomItems" :key="item.path"
        :to="item.path"
        :class="[
          'flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition',
          isActive(item.path)
            ? 'bg-blue-600 text-white font-semibold'
            : 'text-slate-600 hover:bg-slate-50'
        ]"
      >
        <span class="w-5 h-5 flex items-center justify-center text-xs font-bold rounded"
          :class="isActive(item.path) ? (item.colorActive || 'bg-blue-500 text-white') : (item.color || 'bg-slate-100 text-slate-500')"
        >{{ item.icon }}</span>
        {{ item.label }}
      </router-link>
    </nav>

    <!-- 사용자 정보 -->
    <div class="px-4 py-4 border-t border-slate-100 text-sm">
      <p class="font-medium text-slate-700">{{ auth.username }}</p>
      <p class="text-xs text-slate-400">{{ auth.roleLabel }}</p>
      <button
        @click="handleLogout"
        class="mt-3 w-full py-1.5 border border-slate-200 rounded text-xs text-slate-500 hover:bg-slate-50 transition"
      >
        로그아웃
      </button>
    </div>
  </aside>
</template>

<style scoped>
.tree-enter-active,
.tree-leave-active {
  transition: all 0.2s ease;
  overflow: hidden;
}
.tree-enter-from,
.tree-leave-to {
  opacity: 0;
  max-height: 0;
}
.tree-enter-to,
.tree-leave-from {
  opacity: 1;
  max-height: 200px;
}
</style>

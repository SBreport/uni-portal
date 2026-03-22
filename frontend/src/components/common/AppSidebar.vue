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
  adminOnly?: boolean
}

// 마케팅 하위 메뉴
const marketingChildren: MenuItem[] = [
  { path: '/cafe', label: '카페', icon: 'C' },
  { path: '/blog', label: '블로그', icon: 'B' },
  { path: '/place', label: '플레이스', icon: 'P' },
  { path: '/webpage', label: '웹페이지', icon: 'W' },
]

// 최상위 메뉴 (마케팅 제외)
const topItems: MenuItem[] = [
  { path: '/', label: 'HOME', icon: 'H' },
  { path: '/equipment', label: '보유장비', icon: 'E' },
  { path: '/events', label: '이벤트', icon: 'V' },
  { path: '/treatment-info', label: '시술정보', icon: 'T' },
  { path: '/papers', label: '시술논문', icon: 'P' },
]

const bottomItems: MenuItem[] = [
  { path: '/reports', label: '보고서', icon: 'R' },
  { path: '/admin', label: '관리자 모드', icon: 'A', adminOnly: true },
]

function isActive(path: string) {
  if (path === '/') return route.path === '/'
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
        v-for="item in topItems" :key="item.path"
        :to="item.path"
        :class="[
          'flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition',
          isActive(item.path)
            ? 'bg-blue-600 text-white font-semibold'
            : 'text-slate-600 hover:bg-slate-50'
        ]"
      >
        <span class="w-5 h-5 flex items-center justify-center text-xs font-bold rounded"
          :class="isActive(item.path) ? 'bg-blue-500 text-white' : 'bg-slate-100 text-slate-500'"
        >{{ item.icon }}</span>
        {{ item.label }}
      </router-link>

      <!-- 마케팅 (트리) -->
      <div class="pt-0.5">
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
              v-for="child in marketingChildren" :key="child.path"
              :to="child.path"
              :class="[
                'flex items-center gap-2 px-2.5 py-1.5 rounded-md text-[13px] transition',
                isActive(child.path)
                  ? 'bg-blue-600 text-white font-semibold'
                  : 'text-slate-500 hover:bg-slate-50 hover:text-slate-700'
              ]"
            >
              <span class="w-4 h-4 flex items-center justify-center text-[10px] font-bold rounded"
                :class="isActive(child.path) ? 'bg-blue-500 text-white' : 'bg-slate-100 text-slate-400'"
              >{{ child.icon }}</span>
              {{ child.label }}
            </router-link>
          </div>
        </transition>
      </div>

      <!-- 구분선 -->
      <div class="!my-2 border-t border-slate-100"></div>

      <!-- 하위 메뉴 (보고서, 관리자) -->
      <template v-for="item in bottomItems" :key="item.path">
        <router-link
          v-if="!item.adminOnly || auth.role === 'admin'"
          :to="item.path"
          :class="[
            'flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition',
            isActive(item.path)
              ? 'bg-blue-600 text-white font-semibold'
              : 'text-slate-600 hover:bg-slate-50'
          ]"
        >
          <span class="w-5 h-5 flex items-center justify-center text-xs font-bold rounded"
            :class="isActive(item.path) ? 'bg-blue-500 text-white' : 'bg-slate-100 text-slate-500'"
          >{{ item.icon }}</span>
          {{ item.label }}
        </router-link>
      </template>
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

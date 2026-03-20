<script setup lang="ts">
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const auth = useAuthStore()

const menuItems = [
  { path: '/', label: 'HOME', icon: 'H' },
  { path: '/equipment', label: '보유장비', icon: 'E' },
  { path: '/events', label: '이벤트', icon: 'V' },
  { path: '/cafe', label: '카페', icon: 'C' },
  { path: '/blog', label: '블로그', icon: 'B' },
  { path: '/dictionary', label: '시술사전', icon: 'D' },
  { path: '/papers', label: '시술논문', icon: 'P' },
  { path: '/admin', label: '사용자 관리', icon: 'A', adminOnly: true },
]

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
    <nav class="flex-1 py-4 px-3 space-y-1">
      <template v-for="item in menuItems" :key="item.path">
        <router-link
          v-if="!item.adminOnly || auth.role === 'admin'"
          :to="item.path"
          :class="[
            'flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition',
            route.path === item.path || (item.path !== '/' && route.path.startsWith(item.path))
              ? 'bg-blue-600 text-white font-semibold'
              : 'text-slate-600 hover:bg-slate-50'
          ]"
        >
          <span class="w-5 h-5 flex items-center justify-center text-xs font-bold rounded"
            :class="route.path === item.path || (item.path !== '/' && route.path.startsWith(item.path))
              ? 'bg-blue-500 text-white'
              : 'bg-slate-100 text-slate-500'"
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

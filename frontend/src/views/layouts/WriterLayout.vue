<script setup lang="ts">
import { computed } from 'vue'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const username = computed(() => auth.username)

function handleLogout() {
  auth.logout()
  window.location.href = '/w/login'
}
</script>

<template>
  <div class="min-h-screen bg-slate-50">
    <!-- Top bar -->
    <header class="bg-white border-b border-slate-200 px-6 py-3 flex items-center justify-between">
      <div>
        <h1 class="text-sm font-bold text-slate-800">유앤아이의원 <span class="text-blue-600">작성자</span></h1>
      </div>
      <div class="flex items-center gap-4">
        <span class="text-xs text-slate-400">{{ username }}</span>
        <button @click="handleLogout" class="text-xs text-slate-400 hover:text-slate-600">로그아웃</button>
      </div>
    </header>

    <!-- Content -->
    <main class="py-6">
      <router-view />
    </main>
  </div>
</template>

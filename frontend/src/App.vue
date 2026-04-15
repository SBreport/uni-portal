<script setup lang="ts">
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import AppSidebar from '@/components/common/AppSidebar.vue'

const route = useRoute()
const auth = useAuthStore()
</script>

<template>
  <!-- 로그인 페이지: 사이드바 없음 -->
  <RouterView v-if="route.name === 'login'" />

  <!-- 인증된 페이지: 사이드바 + 콘텐츠 -->
  <div v-else class="flex min-h-screen bg-slate-50">
    <AppSidebar />
    <main class="ml-48 flex-1 min-w-0">
      <RouterView :key="route.path" />
    </main>
  </div>
</template>

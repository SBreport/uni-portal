<script setup lang="ts">
import { useAuthStore } from '@/stores/auth'
const auth = useAuthStore()
</script>

<template>
  <div class="p-6">
    <h2 class="text-xl font-bold text-slate-800 mb-4">HOME</h2>
    <div class="bg-white rounded-lg border border-slate-200 p-6">
      <p class="text-slate-600">
        <span class="font-semibold">{{ auth.username }}</span>님 환영합니다.
      </p>
      <p class="text-sm text-slate-400 mt-2">
        Fast 버전 (베타) — 좌측 메뉴에서 기능을 선택하세요.
      </p>
    </div>
  </div>
</template>

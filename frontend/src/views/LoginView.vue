<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()

const username = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

async function handleLogin() {
  error.value = ''
  if (!username.value || !password.value) {
    error.value = 'ID와 비밀번호를 입력해주세요.'
    return
  }
  loading.value = true
  try {
    await auth.login(username.value, password.value)
    router.push('/')
  } catch (e: any) {
    error.value = e.response?.data?.detail || '로그인에 실패했습니다.'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="min-h-screen flex items-center justify-center bg-slate-50">
    <div class="w-full max-w-sm px-8">
      <div class="text-center mb-10">
        <h1 class="text-2xl font-bold text-slate-800">유앤아이의원</h1>
        <p class="text-sm text-slate-500 mt-1">통합 관리 시스템 <span class="text-blue-600 font-semibold">Fast</span></p>
      </div>

      <form @submit.prevent="handleLogin" class="space-y-4">
        <div>
          <label class="block text-sm font-medium text-slate-700 mb-1">사용자 ID</label>
          <input
            v-model="username"
            type="text"
            class="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
            placeholder="ID 입력"
            autofocus
          />
        </div>
        <div>
          <label class="block text-sm font-medium text-slate-700 mb-1">비밀번호</label>
          <input
            v-model="password"
            type="password"
            class="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
            placeholder="비밀번호 입력"
          />
        </div>

        <p v-if="error" class="text-red-500 text-sm">{{ error }}</p>

        <button
          type="submit"
          :disabled="loading"
          class="w-full py-2.5 bg-blue-600 text-white rounded-lg font-medium text-sm hover:bg-blue-700 disabled:opacity-50 transition"
        >
          {{ loading ? '로그인 중...' : '로그인' }}
        </button>
      </form>

      <p class="text-center text-xs text-slate-400 mt-10">Developed by smartbranding</p>
    </div>
  </div>
</template>

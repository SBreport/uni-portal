<script setup lang="ts">
withDefaults(defineProps<{
  message?: string
  size?: 'sm' | 'md' | 'lg'
}>(), {
  message: '불러오는 중...',
  size: 'md',
})
</script>

<template>
  <div class="flex items-center justify-center">
    <div class="text-center">
      <div
        :class="[
          'border-2 border-blue-400 border-t-transparent rounded-full animate-spin mx-auto mb-2',
          size === 'sm' ? 'w-4 h-4' : size === 'lg' ? 'w-10 h-10' : 'w-6 h-6',
        ]"
      ></div>
      <p class="text-xs text-slate-400">{{ message }}</p>
    </div>
  </div>
</template>

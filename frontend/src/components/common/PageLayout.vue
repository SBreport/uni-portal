<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  mode: 'reading' | 'table' | 'detail' | 'dashboard'
}>()

const wrapClass = computed(() => {
  switch (props.mode) {
    case 'reading':
      return 'max-w-2xl mx-auto'
    case 'table':
      // w-fit: 콘텐츠 자연 폭으로 응축 (사시 모드 방지)
      // max-w-full: 콘텐츠가 화면보다 크면 화면 폭으로 잘리고 가로 스크롤
      return 'overflow-x-auto w-fit max-w-full'
    case 'detail':
      return 'flex flex-col lg:flex-row gap-6'
    case 'dashboard':
      return 'grid grid-cols-[repeat(auto-fit,minmax(280px,1fr))] gap-4'
    default:
      return ''
  }
})
</script>

<template>
  <div :class="wrapClass">
    <slot />
  </div>
</template>

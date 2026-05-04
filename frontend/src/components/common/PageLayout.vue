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
      return 'overflow-x-auto'
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

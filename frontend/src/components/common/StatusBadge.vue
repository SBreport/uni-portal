<script setup lang="ts">
withDefaults(defineProps<{
  label: string
  color: 'blue' | 'green' | 'red' | 'yellow' | 'slate' | 'purple' | 'orange'
  size?: 'xs' | 'sm'
}>(), {
  size: 'xs',
})
</script>

<template>
  <span
    :class="[
      'rounded-full font-medium',
      size === 'xs' ? 'text-[10px] px-1.5 py-0.5' : 'text-xs px-2 py-0.5',
      color === 'blue'   ? 'bg-blue-100 text-blue-700'     : '',
      color === 'green'  ? 'bg-green-100 text-green-700'   : '',
      color === 'red'    ? 'bg-red-100 text-red-700'       : '',
      color === 'yellow' ? 'bg-yellow-100 text-yellow-700' : '',
      color === 'slate'  ? 'bg-slate-100 text-slate-700'   : '',
      color === 'purple' ? 'bg-purple-100 text-purple-700' : '',
      color === 'orange' ? 'bg-orange-100 text-orange-700' : '',
    ]"
  >{{ label }}</span>
</template>

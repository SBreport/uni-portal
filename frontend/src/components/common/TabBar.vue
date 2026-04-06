<script setup lang="ts">
defineProps<{
  tabs: Array<{ key: string; label: string; count?: number }>
  modelValue: string
}>()

defineEmits<{
  'update:modelValue': [value: string]
}>()
</script>

<template>
  <div class="flex gap-4 mb-5 border-b border-slate-200">
    <button
      v-for="tab in tabs"
      :key="tab.key"
      @click="$emit('update:modelValue', tab.key)"
      :class="[
        'pb-2 text-sm font-medium border-b-2 transition-colors cursor-pointer',
        modelValue === tab.key
          ? 'border-blue-600 text-blue-600'
          : 'border-transparent text-slate-500 hover:text-slate-700'
      ]"
    >
      {{ tab.label }}<span v-if="tab.count !== undefined" class="ml-1 text-xs opacity-60">({{ tab.count }})</span>
    </button>
  </div>
</template>

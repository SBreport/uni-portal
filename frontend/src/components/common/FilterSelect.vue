<script setup lang="ts">
withDefaults(defineProps<{
  modelValue: string
  options: Array<{ value: string; label: string }>
  placeholder?: string
  allLabel?: string
}>(), {
  allLabel: '전체',
})

defineEmits<{
  'update:modelValue': [value: string]
}>()
</script>

<template>
  <select
    :value="modelValue"
    @change="$emit('update:modelValue', ($event.target as HTMLSelectElement).value)"
    class="px-3 py-1.5 border border-slate-300 rounded-md text-sm bg-white focus:outline-none focus:ring-1 focus:ring-blue-500"
  >
    <option value="">{{ placeholder ?? allLabel }}</option>
    <option v-for="opt in options" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
  </select>
</template>

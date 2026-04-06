<script setup lang="ts">
withDefaults(defineProps<{
  message?: string
  colspan?: number
  icon?: string
}>(), {
  message: '데이터가 없습니다',
})
</script>

<template>
  <!-- Table context: render tr > td -->
  <tr v-if="colspan !== undefined">
    <td :colspan="colspan" class="px-3 py-8 text-center text-slate-400">
      <span v-if="icon" class="mr-1">{{ icon }}</span>{{ message }}
    </td>
  </tr>
  <!-- Non-table context: render centered div -->
  <div v-else class="flex items-center justify-center py-8 text-slate-400 text-sm">
    <span v-if="icon" class="mr-1">{{ icon }}</span>{{ message }}
  </div>
</template>

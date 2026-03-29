<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import * as blogApi from '@/api/blog'
import { channelLabel, channelColor } from '@/utils/blogFormatters'

const accounts = ref<any[]>([])
const loading = ref(false)
const search = ref('')
const channelFilter = ref('')
const editingAccount = ref<string | null>(null)
const editForm = ref({ account_name: '', account_group: '' })
const selectedAccounts = ref<Set<string>>(new Set())

async function loadAccounts() {
  loading.value = true
  try {
    const params: any = {}
    if (channelFilter.value) params.channel = channelFilter.value
    if (search.value) params.search = search.value
    const { data } = await blogApi.getBlogAccounts(params)
    accounts.value = data.items
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

function startEdit(acc: any) {
  editingAccount.value = acc.blog_id
  editForm.value = {
    account_name: acc.account_name || '',
    account_group: acc.account_group || '',
  }
}

async function saveAccount(blogId: string) {
  try {
    await blogApi.updateBlogAccount(blogId, editForm.value)
    editingAccount.value = null
    loadAccounts()
  } catch (e) {
    console.error(e)
  }
}

function cancelEdit() { editingAccount.value = null }

function toggleAccount(blogId: string) {
  if (selectedAccounts.value.has(blogId)) {
    selectedAccounts.value.delete(blogId)
  } else {
    selectedAccounts.value.add(blogId)
  }
}

function toggleAllAccounts() {
  if (selectedAccounts.value.size === accounts.value.length) {
    selectedAccounts.value.clear()
  } else {
    selectedAccounts.value = new Set(accounts.value.map((a: any) => a.blog_id))
  }
}

const allAccountsSelected = computed(() =>
  accounts.value.length > 0 && selectedAccounts.value.size === accounts.value.length
)

onMounted(loadAccounts)
</script>

<template>
  <div class="flex-1 flex flex-col min-h-0">
    <!-- 필터 -->
    <div class="bg-white border border-slate-200 rounded-lg p-3 mb-3 flex items-center gap-2">
      <input v-model="search" @keyup.enter="loadAccounts"
             placeholder="계정 ID / 별명 검색"
             class="border border-slate-300 rounded px-2 py-1 text-sm w-56 focus:border-blue-400 focus:outline-none" />
      <button @click="loadAccounts" class="px-3 py-1 bg-blue-500 text-white text-xs rounded hover:bg-blue-600">검색</button>
      <select v-model="channelFilter" @change="loadAccounts" class="border border-slate-300 rounded px-2 py-1 text-sm">
        <option value="">전체 채널</option>
        <option value="br">브랜드</option>
        <option value="opt">최적</option>
        <option value="cafe">카페</option>
      </select>
      <span class="ml-auto text-xs text-slate-400">
        {{ accounts.length }}개 계정
        <span v-if="selectedAccounts.size > 0" class="text-blue-500 ml-1">
          ({{ selectedAccounts.size }}개 선택)
        </span>
      </span>
    </div>

    <!-- 테이블 -->
    <div class="flex-1 bg-white border border-slate-200 rounded-lg overflow-auto">
      <table class="w-full text-sm">
        <thead class="bg-slate-50 sticky top-0">
          <tr class="text-left text-xs text-slate-500 border-b">
            <th class="px-3 py-2 w-10">
              <input type="checkbox"
                     :checked="allAccountsSelected"
                     @change="toggleAllAccounts"
                     class="rounded border-slate-300" />
            </th>
            <th class="px-3 py-2 w-14">채널</th>
            <th class="px-3 py-2 w-40">블로그 ID</th>
            <th class="px-3 py-2 w-36">별명</th>
            <th class="px-3 py-2 w-36">그룹</th>
            <th class="px-3 py-2 w-20 text-right">게시글</th>
            <th class="px-3 py-2 w-24">마지막 발행</th>
            <th class="px-3 py-2 w-20"></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="acc in accounts" :key="acc.blog_id"
              class="border-b border-slate-100 hover:bg-slate-50/50"
              :class="{ 'bg-blue-50/50': selectedAccounts.has(acc.blog_id) }">
            <td class="px-3 py-2">
              <input type="checkbox"
                     :checked="selectedAccounts.has(acc.blog_id)"
                     @change="toggleAccount(acc.blog_id)"
                     class="rounded border-slate-300" />
            </td>
            <td class="px-3 py-2">
              <span class="text-[10px] px-1.5 py-0.5 rounded-full font-medium"
                    :class="channelColor(acc.channel)">
                {{ channelLabel(acc.channel) }}
              </span>
            </td>
            <td class="px-3 py-2 font-mono text-[11px] text-slate-600">{{ acc.blog_id }}</td>
            <td class="px-3 py-2">
              <template v-if="editingAccount === acc.blog_id">
                <input v-model="editForm.account_name"
                       class="border border-blue-300 rounded px-1.5 py-0.5 text-xs w-full"
                       placeholder="별명 입력" />
              </template>
              <template v-else>
                <span class="text-xs text-slate-700">{{ acc.account_name || '-' }}</span>
              </template>
            </td>
            <td class="px-3 py-2">
              <template v-if="editingAccount === acc.blog_id">
                <input v-model="editForm.account_group"
                       class="border border-blue-300 rounded px-1.5 py-0.5 text-xs w-full"
                       placeholder="그룹 입력" />
              </template>
              <template v-else>
                <span class="text-xs text-slate-500">{{ acc.account_group || '-' }}</span>
              </template>
            </td>
            <td class="px-3 py-2 text-right text-xs text-slate-600 font-medium">{{ acc.post_count }}</td>
            <td class="px-3 py-2 text-xs text-slate-400">{{ acc.last_published || '-' }}</td>
            <td class="px-3 py-2 text-right">
              <template v-if="editingAccount === acc.blog_id">
                <button @click="saveAccount(acc.blog_id)" class="text-[10px] text-blue-600 hover:underline mr-1">저장</button>
                <button @click="cancelEdit" class="text-[10px] text-slate-400 hover:underline">취소</button>
              </template>
              <template v-else>
                <button @click="startEdit(acc)" class="text-[10px] text-slate-400 hover:text-blue-600">편집</button>
              </template>
            </td>
          </tr>
          <tr v-if="!accounts.length && !loading">
            <td colspan="8" class="px-3 py-8 text-center text-slate-400 text-sm">계정이 없습니다</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

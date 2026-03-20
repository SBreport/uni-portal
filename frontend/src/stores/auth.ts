import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '@/api/client'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('token') || '')
  const username = ref(localStorage.getItem('username') || '')
  const role = ref(localStorage.getItem('role') || '')
  const branchId = ref<number | null>(
    localStorage.getItem('branch_id') ? Number(localStorage.getItem('branch_id')) : null
  )

  const isAuthenticated = computed(() => !!token.value)

  const permissions = computed(() => {
    const r = role.value
    return {
      canEditPhoto: ['branch', 'editor', 'admin'].includes(r),
      canSave: ['branch', 'editor', 'admin'].includes(r),
      canSync: r === 'admin',
      canManageUsers: r === 'admin',
      canEditDictionary: ['editor', 'admin'].includes(r),
    }
  })

  const roleLabel = computed(() => {
    const labels: Record<string, string> = {
      viewer: '뷰어', branch: '지점담당', editor: '편집자', admin: '관리자'
    }
    return labels[role.value] || role.value
  })

  async function login(id: string, password: string) {
    const { data } = await api.post('/auth/login', { username: id, password })
    token.value = data.access_token
    username.value = data.username
    role.value = data.role
    branchId.value = data.branch_id
    localStorage.setItem('token', data.access_token)
    localStorage.setItem('username', data.username)
    localStorage.setItem('role', data.role)
    if (data.branch_id != null) {
      localStorage.setItem('branch_id', String(data.branch_id))
    }
  }

  function logout() {
    token.value = ''
    username.value = ''
    role.value = ''
    branchId.value = null
    localStorage.removeItem('token')
    localStorage.removeItem('username')
    localStorage.removeItem('role')
    localStorage.removeItem('branch_id')
  }

  return { token, username, role, branchId, isAuthenticated, permissions, roleLabel, login, logout }
})

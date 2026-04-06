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
  const permissionTags = ref<string[]>(
    JSON.parse(localStorage.getItem('permissions') || '[]')
  )

  const isAuthenticated = computed(() => !!token.value)

  function hasPermission(perm: string): boolean {
    return role.value === 'admin' || permissionTags.value.includes(perm)
  }

  // Effective role that distinguishes viewer subtypes
  const effectiveRole = computed(() => {
    if (role.value === 'viewer' && branchId.value !== null) return 'viewer-branch'
    if (role.value === 'viewer' && branchId.value === null) return 'viewer-hq'
    return role.value // admin, editor, branch
  })

  // Writer/Publisher detection
  const isWriter = computed(() => hasPermission('cafe_write') || hasPermission('blog_write'))
  const isPublisher = computed(() => hasPermission('cafe_publish'))

  const permissions = computed(() => {
    const er = effectiveRole.value
    return {
      canEditPhoto: ['branch', 'editor', 'admin'].includes(er),
      canSave: ['branch', 'editor', 'admin'].includes(er),
      canSync: er === 'admin',
      canManageUsers: er === 'admin',
      canEditDictionary: ['editor', 'admin'].includes(er),
    }
  })

  const roleLabel = computed(() => {
    const labels: Record<string, string> = {
      admin: '관리자',
      editor: '대행사',
      branch: '지점담당',
      'viewer-hq': '본사',
      'viewer-branch': '지점 원장',
    }
    return labels[effectiveRole.value] || role.value
  })

  async function login(id: string, password: string) {
    const { data } = await api.post('/auth/login', { username: id, password })
    token.value = data.access_token
    username.value = data.username
    role.value = data.role
    branchId.value = data.branch_id
    permissionTags.value = data.permissions || []
    localStorage.setItem('token', data.access_token)
    localStorage.setItem('username', data.username)
    localStorage.setItem('role', data.role)
    localStorage.setItem('permissions', JSON.stringify(data.permissions || []))
    if (data.branch_id != null) {
      localStorage.setItem('branch_id', String(data.branch_id))
    }
  }

  function logout() {
    token.value = ''
    username.value = ''
    role.value = ''
    branchId.value = null
    permissionTags.value = []
    localStorage.removeItem('token')
    localStorage.removeItem('username')
    localStorage.removeItem('role')
    localStorage.removeItem('branch_id')
    localStorage.removeItem('permissions')
  }

  return {
    token, username, role, branchId, permissionTags,
    isAuthenticated, effectiveRole, isWriter, isPublisher,
    permissions, hasPermission, roleLabel,
    login, logout,
  }
})

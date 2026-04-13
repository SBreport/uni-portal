import { createRouter, createWebHistory } from 'vue-router'

// Helper: compute effectiveRole from localStorage (guard runs before Pinia)
function getEffectiveRole(): string {
  const role = localStorage.getItem('role') || ''
  const branchId = localStorage.getItem('branch_id')
  if (role === 'viewer' && branchId !== null) return 'viewer-branch'
  if (role === 'viewer' && branchId === null) return 'viewer-hq'
  return role
}

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/LoginView.vue'),
      meta: { public: true },
    },
    {
      path: '/',
      name: 'home',
      component: () => import('@/views/HomeView.vue'),
    },
    {
      path: '/equipment',
      name: 'equipment',
      component: () => import('@/views/EquipmentView.vue'),
    },
    {
      path: '/events',
      name: 'events',
      component: () => import('@/views/EventsView.vue'),
    },
    {
      path: '/treatment-info',
      name: 'treatment-info',
      component: () => import('@/views/TreatmentInfoView.vue'),
      meta: { roles: ['admin', 'editor'] },
    },
    {
      path: '/papers',
      name: 'papers',
      component: () => import('@/views/PapersView.vue'),
    },
    {
      path: '/explorer',
      name: 'explorer',
      component: () => import('@/views/ExplorerView.vue'),
    },
    {
      path: '/info',
      name: 'info',
      component: () => import('@/views/InfoView.vue'),
      meta: { roles: ['admin', 'editor'] },
    },
    {
      path: '/branch-info',
      name: 'branch-info',
      component: () => import('@/views/BranchInfoView.vue'),
    },
    // ── 마케팅 하위 ──
    {
      path: '/cafe',
      name: 'cafe',
      component: () => import('@/views/CafeView.vue'),
      meta: { roles: ['admin', 'editor'] },
    },
    {
      path: '/blog',
      name: 'blog',
      component: () => import('@/views/BlogView.vue'),
      props: { mode: 'uandi' },
      meta: { roles: ['admin', 'editor'] },
    },
    {
      path: '/blog-all',
      name: 'blog-all',
      component: () => import('@/views/BlogView.vue'),
      props: { mode: 'all' },
      meta: { adminOnly: true, roles: ['admin'] },
    },
    {
      path: '/place',
      name: 'place',
      component: () => import('@/views/PlaceView.vue'),
    },
    {
      path: '/webpage',
      name: 'webpage',
      component: () => import('@/views/WebpageView.vue'),
    },
    // ── 민원 ──
    {
      path: '/complaints',
      name: 'complaints',
      component: () => import('@/views/ComplaintsView.vue'),
    },
    // ── 보고서 ──
    {
      path: '/reports',
      name: 'reports',
      component: () => import('@/views/ReportsView.vue'),
    },
    // ── 관리자 ──
    {
      path: '/admin',
      name: 'admin',
      component: () => import('@/views/AdminView.vue'),
      meta: { roles: ['admin'] },
    },
    // ── 작성자 전용 (/w/) ──
    {
      path: '/w',
      component: () => import('@/views/layouts/WriterLayout.vue'),
      meta: { requiredPermission: 'cafe_write' },
      children: [
        {
          path: '',
          name: 'writer-home',
          component: () => import('@/views/CafeView.vue'),
        },
        {
          path: 'cafe',
          name: 'writer-cafe',
          component: () => import('@/views/CafeView.vue'),
        },
        {
          path: 'blog',
          name: 'writer-blog',
          component: () => import('@/views/BlogView.vue'),
          props: { mode: 'uandi' },
        },
      ],
    },
    // ── 발행자 전용 (/p/) ──
    {
      path: '/p',
      component: () => import('@/views/layouts/PublisherLayout.vue'),
      meta: { requiredPermission: 'cafe_publish' },
      children: [
        {
          path: '',
          name: 'publisher-home',
          component: () => import('@/views/CafeView.vue'),
        },
        {
          path: 'cafe',
          name: 'publisher-cafe',
          component: () => import('@/views/CafeView.vue'),
        },
      ],
    },
  ],
})

// 인증 가드
router.beforeEach((to) => {
  if (to.meta.public) return true

  const token = localStorage.getItem('token')
  if (!token) return { name: 'login' }

  // 권한 태그 체크 (/w, /p 레이아웃)
  if (to.meta.requiredPermission) {
    const role = localStorage.getItem('role')
    if (role === 'admin') return true
    const perms: string[] = JSON.parse(localStorage.getItem('permissions') || '[]')
    if (!perms.includes(to.meta.requiredPermission as string)) return { name: 'home' }
  }

  // meta.roles 기반 접근 제어 (adminOnly 하위 호환 포함)
  if (to.meta.adminOnly && !to.meta.roles) {
    const role = localStorage.getItem('role')
    if (role !== 'admin') return { name: 'home' }
  }
  if (to.meta.roles) {
    const effectiveRole = getEffectiveRole()
    if (!(to.meta.roles as string[]).includes(effectiveRole)) return { name: 'home' }
  }

  return true
})

export default router

import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

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
    },
    {
      path: '/papers',
      name: 'papers',
      component: () => import('@/views/PapersView.vue'),
    },
    {
      path: '/crossref',
      name: 'crossref',
      component: () => import('@/views/CrossReferenceView.vue'),
    },
    // ── 마케팅 하위 ──
    {
      path: '/cafe',
      name: 'cafe',
      component: () => import('@/views/CafeView.vue'),
    },
    {
      path: '/blog',
      name: 'blog',
      component: () => import('@/views/BlogView.vue'),
      props: { mode: 'uandi' },
    },
    {
      path: '/blog-all',
      name: 'blog-all',
      component: () => import('@/views/BlogView.vue'),
      props: { mode: 'all' },
      meta: { adminOnly: true },
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
    },
  ],
})

// 인증 가드
router.beforeEach((to) => {
  if (to.meta.public) return true
  const token = localStorage.getItem('token')
  if (!token) return { name: 'login' }
  // admin 전용 페이지 체크
  if (to.meta.adminOnly) {
    const role = localStorage.getItem('role')
    if (role !== 'admin') return { name: 'home' }
  }
  // 권한 태그 체크
  if (to.meta.requiredPermission) {
    const role = localStorage.getItem('role')
    if (role === 'admin') return true
    const perms: string[] = JSON.parse(localStorage.getItem('permissions') || '[]')
    if (!perms.includes(to.meta.requiredPermission as string)) return { name: 'home' }
  }
  return true
})

export default router

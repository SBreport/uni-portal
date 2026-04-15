/**
 * 작성자(담당자) 정보 노출 제어.
 *
 * 클라이언트(본사/지점)에게는 작성자 정보가 보여서는 안 됨.
 * uni 관계자(admin/editor)에게만 노출.
 *
 * 역할 매핑:
 *   admin  = 관리자 (모든 정보)
 *   editor = 대행사 (uni 직원)
 *   viewer = 본사 (클라이언트, 조회만)
 *   branch = 지점 (클라이언트, 해당 지점만)
 */
import { computed } from 'vue'
import { useAuthStore } from '@/stores/auth'

const AUTHOR_VISIBLE_ROLES = ['admin', 'editor']

export function useAuthorVisibility() {
  const auth = useAuthStore()
  const canSeeAuthor = computed(() => AUTHOR_VISIBLE_ROLES.includes(auth.role))
  return { canSeeAuthor }
}

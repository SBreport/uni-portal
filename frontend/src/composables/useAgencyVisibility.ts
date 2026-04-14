/**
 * 실행사(상위노출 담당 업체) 정보 노출 제어.
 *
 * 클라이언트(본사/지점)에게는 실행사 정보가 보여서는 안 됨.
 * uni 관계자(admin/editor=대행사)에게만 노출.
 *
 * 역할 매핑:
 *   admin  = 관리자 (모든 정보)
 *   editor = 대행사 (uni 직원)
 *   viewer = 본사 (클라이언트, 조회만)
 *   branch = 지점 (클라이언트, 해당 지점만)
 */
import { computed } from 'vue'
import { useAuthStore } from '@/stores/auth'

// 실행사 정보를 볼 수 있는 역할 (uni 관계자)
const AGENCY_VISIBLE_ROLES = ['admin', 'editor']

export function useAgencyVisibility() {
  const auth = useAuthStore()
  const canSeeAgency = computed(() => AGENCY_VISIBLE_ROLES.includes(auth.role))
  return { canSeeAgency }
}

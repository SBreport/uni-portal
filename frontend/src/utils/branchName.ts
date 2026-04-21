/**
 * 브랜드 접두사/접미사를 제거한 지점 표시명.
 *
 * 우선순위:
 * 1. API가 short_name을 내려줬으면 그것을 사용
 * 2. 없으면 fallback: branch_name에서 브랜드 부분 제거
 *
 * 향후 evt_branch_aliases 테이블 도입 시 fallback 제거 가능.
 */
const BRAND_STRIPS = [
  '유앤아이의원 ',
  '유앤아이의원',
  '유앤아이 ',
  '유앤아이',
  '유앤 ',
  '유앤',
]

export function stripBrand(branchName: string | undefined | null): string {
  if (!branchName) return ''
  let name = branchName
  for (const s of BRAND_STRIPS) {
    name = name.replace(s, '')
  }
  return name.replace(/^점\s*/, '').replace(/\s*점$/, '').trim() || branchName
}

export function shortName(branch: { branch?: string; short_name?: string | null } | string): string {
  if (typeof branch === 'string') return stripBrand(branch)
  return branch.short_name ?? stripBrand(branch.branch)
}

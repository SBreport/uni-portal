export function channelLabel(ch: string) {
  if (ch === 'br') return '브랜드'
  if (ch === 'opt') return '최적'
  if (ch === 'cafe') return '카페'
  return ch || '-'
}

export function channelColor(ch: string) {
  if (ch === 'br') return 'border border-slate-300 text-slate-700'
  if (ch === 'opt') return 'border border-blue-300 text-blue-700'
  if (ch === 'cafe') return 'border border-amber-300 text-amber-700'
  return 'border border-slate-300 text-slate-500'
}

export function typeColor(t: string) {
  if (t === '논문글') return 'bg-emerald-50 text-emerald-700'
  if (t === '정보성글') return 'bg-sky-50 text-sky-700'
  if (t === '홍보성글') return 'bg-amber-50 text-amber-700'
  if (t === '임상글') return 'bg-rose-50 text-rose-700'
  if (t === '키컨텐츠') return 'bg-indigo-50 text-indigo-700'
  if (t === '최적') return 'bg-blue-50 text-blue-700'
  if (t === '소개글') return 'bg-teal-50 text-teal-700'
  return 'bg-slate-100 text-slate-600'
}

export function statusColor(s: string) {
  if (s === '보고 완료') return 'text-emerald-600'
  if (s === '발행 완료') return 'text-blue-600'
  if (s === '예약 발행') return 'text-amber-600'
  if (s === '진행 취소') return 'text-red-500'
  if (s === '밀림') return 'text-slate-400'
  return 'text-slate-500'
}

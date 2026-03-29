export function channelLabel(ch: string) {
  if (ch === 'br') return '브랜드'
  if (ch === 'opt') return '최적'
  if (ch === 'cafe') return '카페'
  return ch || '-'
}

export function channelColor(ch: string) {
  if (ch === 'br') return 'bg-blue-100 text-blue-700'
  if (ch === 'opt') return 'bg-purple-100 text-purple-700'
  if (ch === 'cafe') return 'bg-orange-100 text-orange-700'
  return 'bg-slate-100 text-slate-500'
}

export function typeColor(t: string) {
  if (t === '논문글') return 'bg-emerald-100 text-emerald-700'
  if (t === '정보성글') return 'bg-sky-100 text-sky-700'
  if (t === '홍보성글') return 'bg-amber-100 text-amber-700'
  if (t === '임상글') return 'bg-rose-100 text-rose-700'
  if (t === '키컨텐츠') return 'bg-indigo-100 text-indigo-700'
  if (t === '최적') return 'bg-purple-100 text-purple-700'
  if (t === '소개글') return 'bg-teal-100 text-teal-700'
  return 'bg-slate-100 text-slate-600'
}

export function statusColor(s: string) {
  if (s === '보고 완료') return 'text-green-600'
  if (s === '발행 완료') return 'text-blue-600'
  if (s === '예약 발행') return 'text-amber-600'
  if (s === '진행 취소') return 'text-red-500'
  if (s === '밀림') return 'text-slate-400'
  return 'text-slate-500'
}

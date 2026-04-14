export function channelLabel(ch: string) {
  if (ch === 'br') return '브랜드'
  if (ch === 'opt') return '최적'
  if (ch === 'cafe') return '카페'
  return ch || '-'
}

export function channelColor(ch: string) {
  if (ch === 'br') return 'bg-blue-50 text-blue-700'
  if (ch === 'opt') return 'bg-indigo-50 text-indigo-700'
  if (ch === 'cafe') return 'bg-amber-50 text-amber-700'
  return 'bg-slate-100 text-slate-600'
}

export function typeColor(t: string) {
  if (t === '논문글') return 'bg-emerald-50 text-emerald-700'
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

import type { ReportData } from './reportSchema'

// 노션 URL 감지 정규식
const NOTION_URL_RE = /https?:\/\/[^\s]*notion\.site[^\s]*/i

// 섹션 마커 → 섹션 키 매핑
type SectionKey = 'blogDistribution' | 'place' | 'website' | 'blogExposure' | 'related' | null

function detectSection(line: string): SectionKey | undefined {
  const t = line.trim()
  if (t === '[최적블로그 배포]') return 'blogDistribution'
  if (t === '[플레이스]') return 'place'
  if (t === '[웹사이트]') return 'website'
  if (t === '[블로그 상위노출]') return 'blogExposure'
  if (t === '[함께 많이 찾는]') return 'related'
  return undefined
}

// 숫자 하나 추출 헬퍼
function extractNum(pattern: RegExp, line: string): string | null {
  const m = line.match(pattern)
  return m ? m[1] : null
}

// 줄 압축 (연속 빈 줄 → 단일 빈 줄)
function compressBlankLines(lines: string[]): string {
  const out: string[] = []
  let prevBlank = false
  for (const l of lines) {
    const blank = l.trim() === ''
    if (blank && prevBlank) continue
    out.push(l)
    prevBlank = blank
  }
  return out.join('\n').trim()
}

// ─────────────────────────────────────────────
// 섹션별 파서
// ─────────────────────────────────────────────

function parseBlogDistribution(lines: string[]): ReportData['blogDistribution'] {
  const result: ReportData['blogDistribution'] = {
    posts: '', ranked: '', keywords: '',
    summary: '', response: '', link1: '', link2: '',
  }
  const summaryLines: string[] = []

  for (const raw of lines) {
    const line = raw.trim()
    if (!line) { summaryLines.push(''); continue }

    // 노션 URL 무시
    if (NOTION_URL_RE.test(line)) continue

    // 숫자 추출 시도
    const posts = extractNum(/발행한\s*글\s+(\d+)/, line)
    if (posts) { result.posts = posts; continue }

    // 상위노출 N개 — "상위노출되고" 와 구분: 뒤에 숫자+개 가 있는 경우만
    const ranked = extractNum(/^상위노출\s+(\d+)개/, line)
    if (ranked) { result.ranked = ranked; continue }

    const keywords = extractNum(/타겟키워드\s+(\d+)/, line)
    if (keywords) { result.keywords = keywords; continue }

    summaryLines.push(raw)
  }

  result.summary = compressBlankLines(summaryLines)
  return result
}

function parsePlace(lines: string[]): ReportData['place'] {
  const result: ReportData['place'] = {
    total: '', occupied: '', dropped: '', paused: '',
    summary: '', response: '', droppedList: '', newList: '',
    pausedList: '', comment: '', link: '',
  }
  const summaryLines: string[] = []
  const commentLines: string[] = []

  // 다음 논비어 라인을 특정 필드에 넣기 위한 상태
  type ListTarget = 'droppedList' | 'newList' | 'pausedList' | null
  let nextListTarget: ListTarget = null

  for (const raw of lines) {
    const line = raw.trim()

    // 노션 URL 무시
    if (NOTION_URL_RE.test(line)) continue

    // 빈 줄: nextListTarget 상태 유지 (다음 논비어 라인을 기다림)
    if (!line) {
      summaryLines.push('')
      continue
    }

    // * 주석 라인 (코멘트 버킷)
    if (line.startsWith('*')) {
      commentLines.push(line)
      continue
    }

    // 프리픽스 라인 감지
    if (/^이탈\s*지점\s*:/.test(line)) {
      nextListTarget = 'droppedList'
      continue
    }
    if (/^신규\s*지점\s*:/.test(line)) {
      nextListTarget = 'newList'
      continue
    }
    if (/^휴식\s*지점\s*:/.test(line)) {
      nextListTarget = 'pausedList'
      continue
    }

    // 논비어 라인 — 목록 대기 중이면 할당
    if (nextListTarget) {
      result[nextListTarget] = line
      nextListTarget = null
      continue
    }

    // 숫자 추출 시도
    const total = extractNum(/총\s+(\d+)\s*지점/, line)
    if (total) { result.total = total; continue }

    const occupied = extractNum(/점유\s+(\d+)\s*지점/, line)
    if (occupied) { result.occupied = occupied; continue }

    const dropped = extractNum(/이탈\s+(\d+)\s*지점/, line)
    if (dropped) { result.dropped = dropped; continue }

    const paused = extractNum(/휴식\s+(\d+)\s*지점/, line)
    if (paused) { result.paused = paused; continue }

    summaryLines.push(raw)
  }

  result.comment = commentLines.join('\n')
  result.summary = compressBlankLines(summaryLines)
  return result
}

function parseWebsite(lines: string[]): ReportData['website'] {
  const result: ReportData['website'] = {
    total: '', visible: '', dropped: '', missing: '',
    summary: '', response: '', visibleList: '', link: '',
  }
  const summaryLines: string[] = []

  for (const raw of lines) {
    const line = raw.trim()
    if (!line) { summaryLines.push(''); continue }

    // 노션 URL 무시
    if (NOTION_URL_RE.test(line)) continue

    // 숫자 추출
    const total = extractNum(/총\s+(\d+)\s*개/, line)
    if (total) { result.total = total; continue }

    const visible = extractNum(/노출\s*지점\s*수\s+(\d+)/, line)
    if (visible) { result.visible = visible; continue }

    const dropped = extractNum(/이탈\s*지점\s*수\s+(\d+)/, line)
    if (dropped) { result.dropped = dropped; continue }

    const missing = extractNum(/미점유\s+(\d+)/, line)
    if (missing) { result.missing = missing; continue }

    // 현재 X 상위노출되고... 문장 — visibleList 추출
    const visibleMatch = line.match(/현재\s+(.+?)\s+상위노출되고/)
    if (visibleMatch) {
      result.visibleList = visibleMatch[1].trim()
      // 이 줄은 summary에서 제외 (continue)
      continue
    }

    summaryLines.push(raw)
  }

  result.summary = compressBlankLines(summaryLines)
  return result
}

function parseBlogExposure(lines: string[]): ReportData['blogExposure'] {
  const result: ReportData['blogExposure'] = {
    total: '', visible: '', dropped: '',
    summary: '', response: '', link: '',
  }
  const summaryLines: string[] = []

  for (const raw of lines) {
    const line = raw.trim()
    if (!line) { summaryLines.push(''); continue }

    // 노션 URL 무시
    if (NOTION_URL_RE.test(line)) continue

    // 숫자 추출 — "총 키워드 수"
    const total = extractNum(/총\s*키워드\s*수\s+(\d+)/, line)
    if (total) { result.total = total; continue }

    const visible = extractNum(/노출\s*수\s+(\d+)/, line)
    if (visible) { result.visible = visible; continue }

    const dropped = extractNum(/이탈\s*수\s+(\d+)/, line)
    if (dropped) { result.dropped = dropped; continue }

    summaryLines.push(raw)
  }

  result.summary = compressBlankLines(summaryLines)
  return result
}

function parseRelated(lines: string[]): ReportData['related'] {
  const result: ReportData['related'] = {
    total: '', created: '', dropped: '', newCount: '',
    summary: '', response: '', keywords: '', link: '',
  }
  const summaryLines: string[] = []
  let nextIsKeywords = false

  for (const raw of lines) {
    const line = raw.trim()
    if (!line) { summaryLines.push(''); continue }

    // 노션 URL 무시
    if (NOTION_URL_RE.test(line)) continue

    // 프리픽스: 지역명&피부과 생성키워드: 다음 논비어 라인 → keywords
    if (/지역명.*?생성키워드\s*:/.test(line)) {
      nextIsKeywords = true
      continue
    }

    if (nextIsKeywords) {
      result.keywords = line
      nextIsKeywords = false
      continue
    }

    // 숫자 추출
    const total = extractNum(/총\s*키워드\s*수\s+(\d+)/, line)
    if (total) { result.total = total; continue }

    const created = extractNum(/생성\s*키워드\s*수\s+(\d+)/, line)
    if (created) { result.created = created; continue }

    const dropped = extractNum(/이탈\s*키워드\s*수\s+(\d+)/, line)
    if (dropped) { result.dropped = dropped; continue }

    const newCount = extractNum(/신규\s*키워드\s*수\s+(\d+)/, line)
    if (newCount) { result.newCount = newCount; continue }

    summaryLines.push(raw)
  }

  result.summary = compressBlankLines(summaryLines)
  return result
}

// ─────────────────────────────────────────────
// 메인 파서 (라인 단위 상태 머신)
// ─────────────────────────────────────────────

export function parseWeeklyReportText(text: string): Partial<ReportData> {
  const lines = text.split(/\r?\n/)

  // 섹션별 라인 버킷
  const buckets: Record<SectionKey & string, string[]> = {
    blogDistribution: [],
    place: [],
    website: [],
    blogExposure: [],
    related: [],
  }

  let currentSection: SectionKey = null

  for (const line of lines) {
    const trimmed = line.trim()

    // 섹션 마커 감지
    const detected = detectSection(trimmed)
    if (detected !== undefined) {
      currentSection = detected
      continue
    }

    // 하단 감사 / 노션 보고서 제목 라인 무시
    // "[4월 N일] 상위노출 주간보고" 패턴
    if (/\[\d+월\s+\d+일\]\s+상위노출\s+주간보고/.test(trimmed)) {
      currentSection = null
      continue
    }
    if (trimmed === '감사합니다^^' || trimmed === '감사합니다^^'.trim()) {
      currentSection = null
      continue
    }

    // 노션 URL 라인 전체 무시
    if (NOTION_URL_RE.test(trimmed)) continue

    // 현재 섹션이 없으면 (인사말, 상단 설명 등) 무시
    if (!currentSection) continue

    buckets[currentSection].push(line)
  }

  const result: Partial<ReportData> = {}

  if (buckets.blogDistribution.length > 0) {
    result.blogDistribution = parseBlogDistribution(buckets.blogDistribution)
  }
  if (buckets.place.length > 0) {
    result.place = parsePlace(buckets.place)
  }
  if (buckets.website.length > 0) {
    result.website = parseWebsite(buckets.website)
  }
  if (buckets.blogExposure.length > 0) {
    result.blogExposure = parseBlogExposure(buckets.blogExposure)
  }
  if (buckets.related.length > 0) {
    result.related = parseRelated(buckets.related)
  }

  return result
}

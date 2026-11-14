import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';

const projectDir = path.dirname(new URL(import.meta.url).pathname);
const repoRoot = path.resolve(projectDir, '../../../..');
const dbPath = path.join(repoRoot, 'data/equipment.db');
const referencePath = path.join(projectDir, 'manager_reference_mapping.csv');
const subReferencePath = path.join(projectDir, 'sub_manager_reference_mapping.csv');
const OPTIMAL_SPECIALISTS = new Set(['서동균', '박주혁']);
const MONTHS = ['2026-01', '2026-02', '2026-03', '2026-04', '2026-05', '2026-06'];
const SUPPLEMENTAL_REFERENCES = [
  { specialty_group: '치과/로컬', branch: '365봄치과', manager: '' },
  { specialty_group: '치과/로컬', branch: '용인터미널퍼스트치과', manager: '배재준' },
  { specialty_group: '세무/로컬', branch: '천지세무', manager: '오현정' },
  { specialty_group: '세무/로컬', branch: '세무법인 현답', manager: '오현정' },
];
const SUPPLEMENTAL_SUB_WRITER_BRANCHES = new Set(['신현편안내과의원', '용인터미널퍼스트치과']);

function parseCSV(text) {
  const rows = [];
  let row = [];
  let field = '';
  let quoted = false;

  for (let i = 0; i < text.length; i += 1) {
    const char = text[i];
    const next = text[i + 1];
    if (quoted) {
      if (char === '"' && next === '"') {
        field += '"';
        i += 1;
      } else if (char === '"') quoted = false;
      else field += char;
      continue;
    }
    if (char === '"') quoted = true;
    else if (char === ',') {
      row.push(field);
      field = '';
    } else if (char === '\n') {
      row.push(field);
      rows.push(row);
      row = [];
      field = '';
    } else if (char !== '\r') field += char;
  }
  if (field || row.length) {
    row.push(field);
    rows.push(row);
  }
  return rows;
}

function toCSV(rows) {
  return rows.map((row) => row.map((value) => {
    const text = value == null ? '' : String(value);
    return /[",\n\r]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
  }).join(',')).join('\n') + '\n';
}

function escapeHTML(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

function fmtInt(value) {
  return Number(value || 0).toLocaleString('ko-KR');
}

function pct(numerator, denominator) {
  return denominator ? numerator / denominator : null;
}

function fmtPct(value) {
  return value == null ? '-' : `${(value * 100).toFixed(1)}%`;
}

function rateTone(value) {
  if (value == null) return 'muted';
  if (value < 0.4) return 'danger';
  if (value < 0.55) return 'warn';
  if (value < 0.7) return 'watch';
  return 'ok';
}

function cleanText(value) {
  return String(value || '').replace(/\s+/g, ' ').trim();
}

function normalizeBranchName(row) {
  let text = cleanText(row.project_branch) || cleanText(row.branch_name) || cleanText(row.target_branch);
  text = text.replace(/^\d+\s+/, '');
  text = text.replace(/\s*(최적배포|준최배포|최적|준최|최|브블|NB)\s*\d*$/i, '');
  text = text.replace(/\s+\d+_\d+$/, '');
  text = text.replace(/\s+\d+$/, '');
  text = text.replace(/\s*\(.*?\)\s*$/, '');
  text = text.replace(/\s+\d+_\d+$/, '');
  text = text.replace(/\s+\d+$/, '');
  text = text.trim();

  const aliases = {
    '유앤아이 대전': '유앤아이 대전(1)',
    '유앤아이 검단': '유앤아이 인천검단',
    '유앤아이 홍대신촌': '유앤아이 신촌홍대',
    '유앤아이 시흥배곧': '유앤아이 배곧',
    '유앤아이 미금': '유앤아이 분당미금',
    '유앤아이 분당': '유앤아이 분당미금',
    '유앤대전': '유앤아이 대전(1)',
    '유앤광명': '유앤아이 광명',
    '유앤대구': '유앤아이 대구',
    '유앤부산': '유앤아이 부산',
    '유앤김포': '유앤아이 김포',
    '유앤왕십리': '유앤아이 왕십리',
    '유앤선릉': '유앤아이 선릉',
    '유앤구로': '유앤아이 구로',
    '유앤천호': '유앤아이 천호',
    '유앤마곡': '유앤아이 마곡',
    '유앤배곧': '유앤아이 배곧',
    '유앤미금': '유앤아이 분당미금',
    '유앤창원': '유앤아이 창원',
    '유앤광주': '유앤아이 광주',
    '유앤의정부': '유앤아이 의정부',
    '유앤판교': '유앤아이 판교',
    '유앤명동': '유앤아이 명동',
    '유앤목포': '유앤아이 목포',
    '유앤평택': '유앤아이 평택',
    '유앤여의도': '유앤아이 여의도',
    '유앤산본': '유앤아이 산본',
    '유앤부평': '유앤아이 부평',
    '유앤천안': '유앤아이 천안',
    '유앤창동': '유앤아이 창동',
    '유앤찬동': '유앤아이 창동',
    '유앤하남미사': '유앤아이 하남미사',
    '유앤화성봉담': '유앤아이 화성봉담',
    '유앤경기광주': '유앤아이 경기광주',
    '유앤안양': '유앤아이 안양',
    '유앤동탄': '유앤아이 동탄',
    '유앤목동': '유앤아이 목동',
    '유앤목동 1': '유앤아이 목동',
    '유앤목동 2': '유앤아이 목동',
    '유앤광교': '유앤아이 광교',
    '유앤광교 1': '유앤아이 광교',
    '유앤광교 2': '유앤아이 광교',
    '유앤다산': '유앤아이 다산',
    '유앤잠실': '유앤아이 잠실',
    '유앤영등포': '유앤아이 영등포',
    '유앤일산': '유앤아이 일산',
    '유앤강남': '유앤아이 강남',
    '유앤홍대': '유앤아이 신촌홍대',
    '유앤수원': '유앤아이 수원',
    '유앤안산': '유앤아이 안산',
    '유앤검단': '유앤아이 인천검단',
    '유앤부천': '유앤아이 부천',
    '유앤건대': '유앤아이 건대',
    '유앤과천': '유앤아이 과천',
    '로렐의원': '로렐의원 / 최송이 수강생',
    '로렐의원 최적배포': '로렐의원 / 최송이 수강생',
    '더편한': '더편한류마마디의원',
    '더편한류마마디의원 창원': '더편한류마마디의원',
    '이효진산부인과': '이효진 여성의원',
    '이효진산부인과 최적배포': '이효진 여성의원',
    '이효진여성의원': '이효진 여성의원',
    '신현편안': '신현편안내과의원',
    '신현편안내과': '신현편안내과의원',
    '톤앤톤피부과': '톤앤톤 피부과',
    '모세정형외과': '모세정형외과의원',
    '청담위아르': '청담위아르여성병원',
    '청담위아르여성의원': '청담위아르여성병원',
    '노블와이': '노블와이성형외과',
    '벨로이스': '벨로이스의원',
    '프라임': '프라임치과의원',
    '주원튼튼': '주원튼튼한의원',
    '성모튼튼': '성모튼튼365재활의학과',
    '청담뷰엘': '청담뷰엘의원',
    '기드온치과': '기드온치과의원',
    '더스마트치과': '더스마트치과의원',
    '글로우치과': '글로우치과교정과치과의원',
    '디자인': '디자인치과',
    '디자인치과 노원': '디자인치과',
    '헤리티지': '헤리티지플란트치과 광명',
    '헤리티지플란트치과': '헤리티지플란트치과 광명',
    '맑은양평': '맑은미소치과 양평',
    '치과다운': '치과다운치과',
    '이다움': '서울이다움치과',
    '이다움4': '서울이다움치과',
    '굿플중랑': '닥터굿플란트치과 중랑',
    '에이플': '에이플러스치과',
    '세브란스': '충주연세세브란스치과',
    '참조은': '참조은+참조은nb',
    '참조은치과': '참조은+참조은nb',
    '조은': '조은피부과',
    '파인드': '파인드피부과',
    '365봄': '365봄치과',
    '365봄치과': '365봄치과',
    '용인터미널': '용인터미널퍼스트치과',
    '용인터미널퍼스트치과': '용인터미널퍼스트치과',
    '천지세무': '천지세무',
    '세무법인 현답': '세무법인 현답',
  };

  if (/^디자인\s*브블/.test(text)) text = '디자인치과';
  if (/^프라임\s*\d+/.test(text)) text = '프라임치과의원';
  if (/^천지세무\d+$/.test(text)) text = '천지세무';

  return aliases[text] || text || '(blank)';
}

function shouldIgnoreRow(row, normalizedBranch) {
  const combined = [
    normalizedBranch,
    row.branch_name,
    row.project_branch,
    row.target_branch,
    row.content_number,
    row.keyword,
    row.post_type,
    row.post_type_main,
    row.post_type_sub,
  ].map(cleanText).join(' ');
  if (!normalizedBranch || normalizedBranch === '(blank)') return '블랭크 대상';
  if (/미러링/i.test(combined)) return '미러링';
  if (/막글/i.test(combined)) return '막글';
  if (/서비스\s*기자단/i.test(combined)) return '서비스 기자단';
  return '';
}

function emptyStat() {
  return {
    count: 0,
    exposed: 0,
    noExposure: 0,
    outsideTop10: 0,
    authorMain: new Map(),
    authorSub: new Map(),
    authorRaw: new Map(),
    blogTypes: new Map(),
    first: '',
    last: '',
  };
}

function addToCounter(map, key) {
  const clean = cleanText(key) || '(blank)';
  map.set(clean, (map.get(clean) || 0) + 1);
}

function addStat(stat, row) {
  stat.count += 1;
  stat.exposed += row.top10_success;
  stat.noExposure += row.no_exposure;
  stat.outsideTop10 += row.outside_top10;
  addToCounter(stat.authorMain, row.author_main);
  addToCounter(stat.authorSub, row.author_sub);
  addToCounter(stat.authorRaw, row.author);
  addToCounter(stat.blogTypes, row.blog_type);
  if (!stat.first || row.published_at < stat.first) stat.first = row.published_at;
  if (!stat.last || row.published_at > stat.last) stat.last = row.published_at;
}

function updateMap(map, key, row) {
  const stat = map.get(key) || emptyStat();
  addStat(stat, row);
  map.set(key, stat);
  return stat;
}

function topCounter(map, limit = 6) {
  return [...map.entries()]
    .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0], 'ko'))
    .slice(0, limit)
    .map(([name, count]) => `${name} ${count}건`)
    .join(' / ');
}

function counterCount(map, key) {
  return map.get(key) || 0;
}

function statusFor(row) {
  if (!row.postCount) return ['미발행', 'muted'];
  if (row.managerAuthorMainRate >= 0.8) return ['대체로 일치', 'ok'];
  if (row.managerAuthorMainCount > 0) return ['부분 일치', 'watch'];
  if (row.blankAuthorMainCount === row.postCount) return ['담당자 공백', 'danger'];
  return ['불일치 확인', 'warn'];
}

function subStatusFor(row) {
  if (!row.subManager) return ['부사수 없음', 'muted'];
  if (!row.junePostCount) return ['6월 발행 없음', 'muted'];
  if (row.expectedCount === 0 && row.actualSubAuthorCount === 0) return ['예정 없음', 'ok'];
  if (row.expectedCount != null && row.actualSubAuthorCount >= row.expectedCount) return ['수량 충족', 'ok'];
  if (row.actualSubAuthorCount > 0) return ['부분 확인', 'watch'];
  return ['미확인', 'warn'];
}

function summarizeMonthly(months) {
  const count = months.reduce((sum, row) => sum + row.count, 0);
  const exposed = months.reduce((sum, row) => sum + row.exposed, 0);
  const noExposure = months.reduce((sum, row) => sum + row.noExposure, 0);
  const outsideTop10 = months.reduce((sum, row) => sum + row.outsideTop10, 0);
  return {
    count,
    exposed,
    exposureRate: pct(exposed, count),
    noExposure,
    outsideTop10,
  };
}

function monthlyRowsFor(map, name) {
  return MONTHS.map((month) => {
    const stat = map.get(`${name}|${month}`) || emptyStat();
    return {
      month,
      count: stat.count,
      exposed: stat.exposed,
      exposureRate: pct(stat.exposed, stat.count),
      noExposure: stat.noExposure,
      outsideTop10: stat.outsideTop10,
    };
  });
}

function monthlyRowsForManagerBranch(map, manager, branch) {
  return MONTHS.map((month) => {
    const stat = map.get(`${manager}|${branch}|${month}`) || emptyStat();
    return {
      month,
      count: stat.count,
      exposed: stat.exposed,
      exposureRate: pct(stat.exposed, stat.count),
      noExposure: stat.noExposure,
      outsideTop10: stat.outsideTop10,
    };
  });
}

function rateCell(value, tone = '') {
  return `<span class="rate ${tone}">${fmtPct(value)}</span>`;
}

const referenceRowsRaw = parseCSV(fs.readFileSync(referencePath, 'utf8'));
const referenceHeaders = referenceRowsRaw.shift();
const refIdx = Object.fromEntries(referenceHeaders.map((name, index) => [name, index]));
const referenceRows = referenceRowsRaw.map((row) => ({
  specialty_group: cleanText(row[refIdx.specialty_group]),
  branch: cleanText(row[refIdx.branch]),
  manager: cleanText(row[refIdx.manager]),
}));

for (const supplemental of SUPPLEMENTAL_REFERENCES) {
  if (!referenceRows.some((row) => row.branch === supplemental.branch)) {
    referenceRows.push(supplemental);
  }
}

const referenceMap = new Map(referenceRows.map((row) => [row.branch, row]));

const subReferenceRowsRaw = parseCSV(fs.readFileSync(subReferencePath, 'utf8'));
const subReferenceHeaders = subReferenceRowsRaw.shift();
const subRefIdx = Object.fromEntries(subReferenceHeaders.map((name, index) => [name, index]));
const subReferenceRows = subReferenceRowsRaw.map((row) => ({
  branch: cleanText(row[subRefIdx.branch]),
  subManager: cleanText(row[subRefIdx.sub_manager]),
  expectedCount: cleanText(row[subRefIdx.expected_count]) === '' ? null : Number(row[subRefIdx.expected_count]),
}));

if (!subReferenceRows.some((row) => row.branch === '용인터미널퍼스트치과')) {
  subReferenceRows.push({ branch: '용인터미널퍼스트치과', subManager: '박현지', expectedCount: null });
}

const subReferenceMap = new Map(subReferenceRows.map((row) => [row.branch, row]));

const sql = `
SELECT
  id,
  published_at,
  branch_name,
  project_branch,
  content_number,
  keyword,
  exposure_rank,
  post_type,
  post_type_main,
  post_type_sub,
  blog_channel,
  blog_id,
  title,
  status,
  published_url,
  author,
  author_main,
  author_sub
FROM blog_posts
WHERE published_at >= '2026-01-01'
  AND published_at < '2026-07-01'
ORDER BY published_at, id;
`;

const csv = execFileSync('sqlite3', ['-header', '-csv', dbPath, sql], {
  encoding: 'utf8',
  maxBuffer: 64 * 1024 * 1024,
});
const rawRows = parseCSV(csv);
const headers = rawRows.shift();
const idx = Object.fromEntries(headers.map((name, index) => [name, index]));

const rows = rawRows.map((raw) => {
  const rankRaw = raw[idx.exposure_rank];
  const rank = rankRaw === '' ? null : Number(rankRaw);
  const row = {
    id: raw[idx.id],
    published_at: raw[idx.published_at],
    branch_name: raw[idx.branch_name],
    project_branch: raw[idx.project_branch],
    content_number: raw[idx.content_number],
    keyword: raw[idx.keyword],
    exposure_rank: rank,
    post_type: raw[idx.post_type],
    post_type_main: raw[idx.post_type_main],
    post_type_sub: raw[idx.post_type_sub],
    blog_channel: raw[idx.blog_channel],
    blog_id: raw[idx.blog_id],
    title: raw[idx.title],
    status: raw[idx.status],
    published_url: raw[idx.published_url],
    author: raw[idx.author],
    author_main: raw[idx.author_main],
    author_sub: raw[idx.author_sub],
  };
  const normalizedBranch = normalizeBranchName(row);
  const ignoreReason = shouldIgnoreRow(row, normalizedBranch);
  const reference = referenceMap.get(normalizedBranch);
  const subReference = subReferenceMap.get(normalizedBranch);
  return {
    ...row,
    normalized_branch: normalizedBranch,
    analysis_ignored: Boolean(ignoreReason),
    ignore_reason: ignoreReason,
    reference_matched: Boolean(reference),
    specialty_group: reference?.specialty_group || '',
    reference_manager: reference?.manager || '',
    reference_sub_manager: subReference?.subManager || '',
    reference_sub_expected_count: subReference?.expectedCount ?? null,
    blog_type: row.blog_channel === 'opt' ? '최적 블로그' : '일반 블로그',
    top10_success: rank != null && rank >= 1 && rank <= 10 ? 1 : 0,
    no_exposure: rank == null || rank === 0 ? 1 : 0,
    outside_top10: rank != null && rank >= 11 ? 1 : 0,
  };
});

const analysisRows = rows.filter((row) => !row.analysis_ignored);

const byBranch = new Map();
const byBranchJune = new Map();
const byBranchJuneAuthor = new Map();
const unmatchedMap = new Map();
const byAuthorMain = new Map();
const byManagerMonth = new Map();
const byManagerNormalMonth = new Map();
const byManagerOptimalMonth = new Map();
const byManagerOptimalBranchMonth = new Map();
const byManagerBranchMonth = new Map();
const byManagerBranchNormalMonth = new Map();
const byManagerBranchOptimalMonth = new Map();
const byManagerDirectWriterMonth = new Map();
const bySubManagerMonth = new Map();
const bySubManagerNormalMonth = new Map();
const bySubManagerOptimalMonth = new Map();
const byOptimalSpecialistMonth = new Map();
const byManagerSubWriterMonth = new Map();
const byManagerOptimalSpecialistMonth = new Map();
for (const row of analysisRows) {
  if (row.reference_matched) {
    updateMap(byBranch, row.normalized_branch, row);
    updateMap(byAuthorMain, cleanText(row.author_main) || '(blank)', row);
    const month = row.published_at.slice(0, 7);
    const authorMain = cleanText(row.author_main) || '(blank)';
    if (row.reference_manager) {
      updateMap(byManagerMonth, `${row.reference_manager}|${month}`, row);
      updateMap(row.blog_channel === 'opt' ? byManagerOptimalMonth : byManagerNormalMonth, `${row.reference_manager}|${month}`, row);
      updateMap(byManagerBranchMonth, `${row.reference_manager}|${row.normalized_branch}|${month}`, row);
      updateMap(row.blog_channel === 'opt' ? byManagerBranchOptimalMonth : byManagerBranchNormalMonth, `${row.reference_manager}|${row.normalized_branch}|${month}`, row);
    }
    if (row.reference_manager && row.blog_channel === 'opt') {
      updateMap(byManagerOptimalBranchMonth, `${row.reference_manager}|${month}`, row);
    }
    if (row.reference_manager && row.blog_channel !== 'opt' && authorMain === row.reference_manager) {
      updateMap(byManagerDirectWriterMonth, `${row.reference_manager}|${month}`, row);
    }
    if (OPTIMAL_SPECIALISTS.has(authorMain)) {
      updateMap(byOptimalSpecialistMonth, `${authorMain}|${month}`, row);
    }
    if (row.reference_manager && row.blog_channel === 'opt' && OPTIMAL_SPECIALISTS.has(authorMain)) {
      updateMap(byManagerOptimalSpecialistMonth, `${row.reference_manager}|${month}`, row);
    }
    if (row.reference_sub_manager && authorMain === row.reference_sub_manager) {
      updateMap(bySubManagerMonth, `${authorMain}|${month}`, row);
      updateMap(row.blog_channel === 'opt' ? bySubManagerOptimalMonth : bySubManagerNormalMonth, `${authorMain}|${month}`, row);
    }
    if (row.reference_manager && row.reference_sub_manager && authorMain === row.reference_sub_manager && row.blog_channel !== 'opt') {
      updateMap(byManagerSubWriterMonth, `${row.reference_manager}|${month}`, row);
    } else if (row.reference_manager && SUPPLEMENTAL_SUB_WRITER_BRANCHES.has(row.normalized_branch) && row.blog_channel !== 'opt') {
      updateMap(byManagerSubWriterMonth, `${row.reference_manager}|${month}`, row);
    }
    if (row.published_at.startsWith('2026-06')) {
      updateMap(byBranchJune, row.normalized_branch, row);
      updateMap(byBranchJuneAuthor, `${row.normalized_branch}|${cleanText(row.author_main) || '(blank)'}`, row);
    }
  } else {
    updateMap(unmatchedMap, row.normalized_branch, row);
  }
}

const branchAuditRows = referenceRows.map((reference) => {
  const stat = byBranch.get(reference.branch) || emptyStat();
  const managerAuthorMainCount = counterCount(stat.authorMain, reference.manager);
  const managerAuthorSubCount = counterCount(stat.authorSub, reference.manager);
  const blankAuthorMainCount = counterCount(stat.authorMain, '(blank)');
  const row = {
    specialtyGroup: reference.specialty_group,
    branch: reference.branch,
    referenceManager: reference.manager,
    postCount: stat.count,
    exposedCount: stat.exposed,
    exposureRate: pct(stat.exposed, stat.count),
    managerAuthorMainCount,
    managerAuthorMainRate: pct(managerAuthorMainCount, stat.count) || 0,
    managerAuthorSubCount,
    blankAuthorMainCount,
    authorMainSummary: topCounter(stat.authorMain),
    authorSubSummary: topCounter(stat.authorSub),
    authorRawSummary: topCounter(stat.authorRaw),
    blogTypeSummary: topCounter(stat.blogTypes),
    first: stat.first,
    last: stat.last,
  };
  const [statusLabel, statusClass] = statusFor(row);
  return { ...row, statusLabel, statusClass };
}).sort((a, b) => {
  const statusOrder = { danger: 0, warn: 1, watch: 2, muted: 3, ok: 4 };
  return statusOrder[a.statusClass] - statusOrder[b.statusClass]
    || b.postCount - a.postCount
    || a.branch.localeCompare(b.branch, 'ko');
});

const subAuditRows = subReferenceRows.map((reference) => {
  const branchReference = referenceMap.get(reference.branch);
  const juneStat = byBranchJune.get(reference.branch) || emptyStat();
  const subAuthorStat = reference.subManager
    ? byBranchJuneAuthor.get(`${reference.branch}|${reference.subManager}`) || emptyStat()
    : emptyStat();
  const row = {
    specialtyGroup: branchReference?.specialty_group || '',
    branch: reference.branch,
    manager: branchReference?.manager || '',
    subManager: reference.subManager,
    expectedCount: reference.expectedCount,
    junePostCount: juneStat.count,
    juneExposedCount: juneStat.exposed,
    juneExposureRate: pct(juneStat.exposed, juneStat.count),
    actualSubAuthorCount: subAuthorStat.count,
    actualSubAuthorExposedCount: subAuthorStat.exposed,
    actualSubAuthorExposureRate: pct(subAuthorStat.exposed, subAuthorStat.count),
    expectedMatchRate: reference.expectedCount ? pct(subAuthorStat.count, reference.expectedCount) : null,
    branchAuthorMainSummary: topCounter(juneStat.authorMain),
    subAuthorBlogTypeSummary: topCounter(subAuthorStat.blogTypes),
  };
  const [statusLabel, statusClass] = subStatusFor(row);
  return { ...row, statusLabel, statusClass };
}).sort((a, b) => {
  const statusOrder = { warn: 0, watch: 1, muted: 2, ok: 3 };
  return statusOrder[a.statusClass] - statusOrder[b.statusClass]
    || b.junePostCount - a.junePostCount
    || a.branch.localeCompare(b.branch, 'ko');
});

const managerNames = [...new Set(referenceRows.map((row) => row.manager).filter(Boolean))].sort((a, b) => a.localeCompare(b, 'ko'));
const managerReferenceRows = referenceRows.filter((row) => row.manager);
const subManagerNames = [...new Set(subReferenceRows.map((row) => row.subManager).filter(Boolean))].sort((a, b) => a.localeCompare(b, 'ko'));
const subManagerNameSet = new Set(subManagerNames);

function classifyUnmatchedStat(stat) {
  const optimalCount = [...stat.authorMain.entries()]
    .filter(([name]) => OPTIMAL_SPECIALISTS.has(name))
    .reduce((sum, [, count]) => sum + count, 0);
  const subManagerCount = [...stat.authorMain.entries()]
    .filter(([name]) => subManagerNameSet.has(name))
    .reduce((sum, [, count]) => sum + count, 0);
  const managerCount = [...stat.authorMain.entries()]
    .filter(([name]) => managerNames.includes(name))
    .reduce((sum, [, count]) => sum + count, 0);
  const blankCount = counterCount(stat.authorMain, '(blank)');

  if (optimalCount > 0 && optimalCount >= subManagerCount && optimalCount >= managerCount) {
    return `최적전문 가능 ${optimalCount}건`;
  }
  if (subManagerCount > 0 && subManagerCount >= managerCount) {
    return `부사수 가능 ${subManagerCount}건`;
  }
  if (managerCount > 0) {
    return `사수/담당자 가능 ${managerCount}건`;
  }
  if (blankCount === stat.count) return '작성자 공백';
  return '기준표 외 데이터';
}

const unmatchedRows = [...unmatchedMap.entries()].map(([branch, stat]) => ({
  branch,
  postCount: stat.count,
  exposedCount: stat.exposed,
  exposureRate: pct(stat.exposed, stat.count),
  likelyRole: classifyUnmatchedStat(stat),
  authorMainSummary: topCounter(stat.authorMain),
  blogTypeSummary: topCounter(stat.blogTypes),
  first: stat.first,
  last: stat.last,
})).sort((a, b) => b.postCount - a.postCount || a.branch.localeCompare(b.branch, 'ko'));

const authorSummaryRows = [...byAuthorMain.entries()].map(([authorMain, stat]) => ({
  authorMain,
  postCount: stat.count,
  exposedCount: stat.exposed,
  exposureRate: pct(stat.exposed, stat.count),
  noExposure: stat.noExposure,
  outsideTop10: stat.outsideTop10,
  branchCount: new Set(analysisRows.filter((row) => row.reference_matched && (cleanText(row.author_main) || '(blank)') === authorMain).map((row) => row.normalized_branch)).size,
  blogTypeSummary: topCounter(stat.blogTypes),
  first: stat.first,
  last: stat.last,
})).sort((a, b) => b.postCount - a.postCount || a.authorMain.localeCompare(b.authorMain, 'ko'));

const managerMonthlyRows = managerNames.map((manager) => {
  const months = monthlyRowsFor(byManagerMonth, manager);
  const normalMonths = monthlyRowsFor(byManagerNormalMonth, manager);
  const optimalMonths = monthlyRowsFor(byManagerOptimalMonth, manager);
  return {
    manager,
    branchCount: referenceRows.filter((row) => row.manager === manager).length,
    total: summarizeMonthly(months),
    normalTotal: summarizeMonthly(normalMonths),
    optimalTotal: summarizeMonthly(optimalMonths),
    months,
    normalMonths,
    optimalMonths,
  };
}).sort((a, b) => b.total.count - a.total.count || a.manager.localeCompare(b.manager, 'ko'));

const managerDirectWriterMonthlyRows = managerNames.map((manager) => {
  const months = monthlyRowsFor(byManagerDirectWriterMonth, manager);
  return {
    manager,
    branchCount: referenceRows.filter((row) => row.manager === manager).length,
    total: summarizeMonthly(months),
    months,
  };
}).sort((a, b) => b.total.count - a.total.count || a.manager.localeCompare(b.manager, 'ko'));

const managerBranchMonthlyRows = referenceRows.map((reference) => {
  const months = monthlyRowsForManagerBranch(byManagerBranchMonth, reference.manager, reference.branch);
  const normalMonths = monthlyRowsForManagerBranch(byManagerBranchNormalMonth, reference.manager, reference.branch);
  const optimalMonths = monthlyRowsForManagerBranch(byManagerBranchOptimalMonth, reference.manager, reference.branch);
  return {
    manager: reference.manager,
    specialtyGroup: reference.specialty_group,
    branch: reference.branch,
    total: summarizeMonthly(months),
    normalTotal: summarizeMonthly(normalMonths),
    optimalTotal: summarizeMonthly(optimalMonths),
    months,
    normalMonths,
    optimalMonths,
  };
}).filter((row) => row.total.count > 0).sort((a, b) => {
  const managerCompare = a.manager.localeCompare(b.manager, 'ko');
  if (managerCompare) return managerCompare;
  return a.branch.localeCompare(b.branch, 'ko');
});

const managerOptimalBranchMonthlyRows = managerNames.map((manager) => {
  const months = monthlyRowsFor(byManagerOptimalBranchMonth, manager);
  return {
    manager,
    branchCount: referenceRows.filter((row) => row.manager === manager).length,
    total: summarizeMonthly(months),
    months,
  };
}).sort((a, b) => b.total.count - a.total.count || a.manager.localeCompare(b.manager, 'ko'));

const subManagerMonthlyRows = subManagerNames.map((name) => {
  const months = monthlyRowsFor(bySubManagerMonth, name);
  const normalMonths = monthlyRowsFor(bySubManagerNormalMonth, name);
  const optimalMonths = monthlyRowsFor(bySubManagerOptimalMonth, name);
  return {
    name,
    assignedBranchCount: subReferenceRows.filter((row) => row.subManager === name).length,
    juneAssignedCount: subReferenceRows
      .filter((row) => row.subManager === name)
      .reduce((sum, row) => sum + (row.expectedCount || 0), 0),
    total: summarizeMonthly(months),
    normalTotal: summarizeMonthly(normalMonths),
    optimalTotal: summarizeMonthly(optimalMonths),
    months,
    normalMonths,
    optimalMonths,
  };
}).sort((a, b) => b.total.count - a.total.count || a.name.localeCompare(b.name, 'ko'));

const optimalSpecialistMonthlyRows = [...OPTIMAL_SPECIALISTS].map((name) => {
  const months = monthlyRowsFor(byOptimalSpecialistMonth, name);
  return {
    name,
    total: summarizeMonthly(months),
    months,
  };
}).sort((a, b) => b.total.count - a.total.count || a.name.localeCompare(b.name, 'ko'));

const managerSubWriterMonthlyRows = managerNames.map((manager) => {
  const months = monthlyRowsFor(byManagerSubWriterMonth, manager);
  return {
    manager,
    branchCount: referenceRows.filter((row) => row.manager === manager).length,
    assignedSubBranchCount: subReferenceRows
      .filter((row) => row.subManager && referenceMap.get(row.branch)?.manager === manager).length,
    total: summarizeMonthly(months),
    months,
  };
}).sort((a, b) => b.total.count - a.total.count || a.manager.localeCompare(b.manager, 'ko'));

const managerOptimalSpecialistMonthlyRows = managerNames.map((manager) => {
  const months = monthlyRowsFor(byManagerOptimalSpecialistMonth, manager);
  return {
    manager,
    branchCount: referenceRows.filter((row) => row.manager === manager).length,
    total: summarizeMonthly(months),
    months,
  };
}).sort((a, b) => b.total.count - a.total.count || a.manager.localeCompare(b.manager, 'ko'));

const subAuthorSummaryRows = [...subAuditRows.reduce((map, row) => {
  if (!row.subManager) return map;
  const current = map.get(row.subManager) || {
    subManager: row.subManager,
    expectedCount: 0,
    actualCount: 0,
    exposedCount: 0,
    branchCount: 0,
    branches: [],
  };
  current.expectedCount += row.expectedCount || 0;
  current.actualCount += row.actualSubAuthorCount;
  current.exposedCount += row.actualSubAuthorExposedCount;
  current.branchCount += 1;
  current.branches.push(`${row.branch} ${row.actualSubAuthorCount}/${row.expectedCount ?? '-'}`);
  map.set(row.subManager, current);
  return map;
}, new Map()).values()].map((row) => ({
  ...row,
  exposureRate: pct(row.exposedCount, row.actualCount),
  expectedMatchRate: pct(row.actualCount, row.expectedCount),
  branchSummary: row.branches.join(' / '),
})).sort((a, b) => b.expectedCount - a.expectedCount || a.subManager.localeCompare(b.subManager, 'ko'));

fs.writeFileSync(path.join(projectDir, 'manager_author_column_audit.csv'), toCSV([
  ['status', 'specialty_group', 'branch', 'reference_manager', 'post_count', 'exposed_count', 'exposure_rate', 'author_main_manager_count', 'author_main_manager_rate', 'author_sub_manager_count', 'blank_author_main_count', 'author_main_summary', 'author_sub_summary', 'author_raw_summary', 'blog_type_summary', 'first_published', 'last_published'],
  ...branchAuditRows.map((row) => [
    row.statusLabel,
    row.specialtyGroup,
    row.branch,
    row.referenceManager,
    row.postCount,
    row.exposedCount,
    fmtPct(row.exposureRate),
    row.managerAuthorMainCount,
    fmtPct(row.managerAuthorMainRate),
    row.managerAuthorSubCount,
    row.blankAuthorMainCount,
    row.authorMainSummary,
    row.authorSubSummary,
    row.authorRawSummary,
    row.blogTypeSummary,
    row.first,
    row.last,
  ]),
]));

fs.writeFileSync(path.join(projectDir, 'manager_unmatched_branch_audit.csv'), toCSV([
  ['analysis_target_branch', 'likely_role', 'post_count', 'exposed_count', 'exposure_rate', 'author_main_summary', 'blog_type_summary', 'first_published', 'last_published'],
  ...unmatchedRows.map((row) => [
    row.branch,
    row.likelyRole,
    row.postCount,
    row.exposedCount,
    fmtPct(row.exposureRate),
    row.authorMainSummary,
    row.blogTypeSummary,
    row.first,
    row.last,
  ]),
]));

fs.writeFileSync(path.join(projectDir, 'author_main_summary.csv'), toCSV([
  ['author_main', 'post_count', 'exposed_count', 'exposure_rate', 'no_exposure', 'outside_top10', 'branch_count', 'blog_type_summary', 'first_published', 'last_published'],
  ...authorSummaryRows.map((row) => [
    row.authorMain,
    row.postCount,
    row.exposedCount,
    fmtPct(row.exposureRate),
    row.noExposure,
    row.outsideTop10,
    row.branchCount,
    row.blogTypeSummary,
    row.first,
    row.last,
  ]),
]));

fs.writeFileSync(path.join(projectDir, 'sub_manager_author_audit.csv'), toCSV([
  ['status', 'specialty_group', 'branch', 'manager', 'sub_manager', 'expected_count_2026_06', 'june_post_count', 'june_exposed_count', 'june_exposure_rate', 'actual_author_main_count', 'actual_author_main_exposed_count', 'actual_author_main_exposure_rate', 'actual_vs_expected_rate', 'branch_author_main_summary', 'sub_author_blog_type_summary'],
  ...subAuditRows.map((row) => [
    row.statusLabel,
    row.specialtyGroup,
    row.branch,
    row.manager,
    row.subManager,
    row.expectedCount ?? '',
    row.junePostCount,
    row.juneExposedCount,
    fmtPct(row.juneExposureRate),
    row.actualSubAuthorCount,
    row.actualSubAuthorExposedCount,
    fmtPct(row.actualSubAuthorExposureRate),
    fmtPct(row.expectedMatchRate),
    row.branchAuthorMainSummary,
    row.subAuthorBlogTypeSummary,
  ]),
]));

fs.writeFileSync(path.join(projectDir, 'sub_manager_summary.csv'), toCSV([
  ['sub_manager', 'expected_count_2026_06', 'actual_author_main_count', 'actual_vs_expected_rate', 'exposed_count', 'exposure_rate', 'branch_count', 'branch_summary'],
  ...subAuthorSummaryRows.map((row) => [
    row.subManager,
    row.expectedCount,
    row.actualCount,
    fmtPct(row.expectedMatchRate),
    row.exposedCount,
    fmtPct(row.exposureRate),
    row.branchCount,
    row.branchSummary,
  ]),
]));

fs.writeFileSync(path.join(projectDir, 'manager_monthly_summary.csv'), toCSV([
  ['manager', 'branch_count', 'normal_total_count', 'normal_total_exposed', 'normal_total_exposure_rate', 'optimal_total_count', 'optimal_total_exposed', 'optimal_total_exposure_rate', ...MONTHS.flatMap((month) => [`${month}_normal_count`, `${month}_normal_exposed`, `${month}_normal_exposure_rate`, `${month}_optimal_count`, `${month}_optimal_exposed`, `${month}_optimal_exposure_rate`])],
  ...managerMonthlyRows.map((row) => [
    row.manager,
    row.branchCount,
    row.normalTotal.count,
    row.normalTotal.exposed,
    fmtPct(row.normalTotal.exposureRate),
    row.optimalTotal.count,
    row.optimalTotal.exposed,
    fmtPct(row.optimalTotal.exposureRate),
    ...MONTHS.flatMap((month, index) => [
      row.normalMonths[index].count,
      row.normalMonths[index].exposed,
      fmtPct(row.normalMonths[index].exposureRate),
      row.optimalMonths[index].count,
      row.optimalMonths[index].exposed,
      fmtPct(row.optimalMonths[index].exposureRate),
    ]),
  ]),
]));

fs.writeFileSync(path.join(projectDir, 'manager_direct_writer_monthly_summary.csv'), toCSV([
  ['manager', 'assigned_branch_count', 'direct_total_count', 'direct_total_exposed', 'direct_total_exposure_rate', 'direct_total_no_exposure', 'direct_total_outside_top10', ...MONTHS.flatMap((month) => [`${month}_direct_count`, `${month}_direct_exposed`, `${month}_direct_exposure_rate`, `${month}_direct_no_exposure`, `${month}_direct_outside_top10`])],
  ...managerDirectWriterMonthlyRows.map((row) => [
    row.manager,
    row.branchCount,
    row.total.count,
    row.total.exposed,
    fmtPct(row.total.exposureRate),
    row.total.noExposure,
    row.total.outsideTop10,
    ...row.months.flatMap((month) => [
      month.count,
      month.exposed,
      fmtPct(month.exposureRate),
      month.noExposure,
      month.outsideTop10,
    ]),
  ]),
]));

fs.writeFileSync(path.join(projectDir, 'manager_branch_monthly_detail.csv'), toCSV([
  ['manager', 'specialty_group', 'branch', 'total_count', 'total_exposed', 'total_exposure_rate', 'normal_total_count', 'normal_total_exposed', 'normal_total_exposure_rate', 'optimal_total_count', 'optimal_total_exposed', 'optimal_total_exposure_rate', ...MONTHS.flatMap((month) => [`${month}_normal_count`, `${month}_normal_exposed`, `${month}_normal_exposure_rate`, `${month}_optimal_count`, `${month}_optimal_exposed`, `${month}_optimal_exposure_rate`])],
  ...managerBranchMonthlyRows.map((row) => [
    row.manager,
    row.specialtyGroup,
    row.branch,
    row.total.count,
    row.total.exposed,
    fmtPct(row.total.exposureRate),
    row.normalTotal.count,
    row.normalTotal.exposed,
    fmtPct(row.normalTotal.exposureRate),
    row.optimalTotal.count,
    row.optimalTotal.exposed,
    fmtPct(row.optimalTotal.exposureRate),
    ...MONTHS.flatMap((month, index) => [
      row.normalMonths[index].count,
      row.normalMonths[index].exposed,
      fmtPct(row.normalMonths[index].exposureRate),
      row.optimalMonths[index].count,
      row.optimalMonths[index].exposed,
      fmtPct(row.optimalMonths[index].exposureRate),
    ]),
  ]),
]));

fs.writeFileSync(path.join(projectDir, 'manager_optimal_branch_monthly_summary.csv'), toCSV([
  ['manager', 'assigned_branch_count', 'total_optimal_count', 'total_optimal_exposed', 'total_optimal_exposure_rate', 'total_optimal_no_exposure', 'total_optimal_outside_top10', ...MONTHS.flatMap((month) => [`${month}_optimal_count`, `${month}_optimal_exposed`, `${month}_optimal_exposure_rate`, `${month}_optimal_no_exposure`, `${month}_optimal_outside_top10`])],
  ...managerOptimalBranchMonthlyRows.map((row) => [
    row.manager,
    row.branchCount,
    row.total.count,
    row.total.exposed,
    fmtPct(row.total.exposureRate),
    row.total.noExposure,
    row.total.outsideTop10,
    ...row.months.flatMap((month) => [
      month.count,
      month.exposed,
      fmtPct(month.exposureRate),
      month.noExposure,
      month.outsideTop10,
    ]),
  ]),
]));

fs.writeFileSync(path.join(projectDir, 'sub_manager_monthly_summary.csv'), toCSV([
  ['sub_manager', 'assigned_branch_count', 'june_assigned_count', 'normal_total_count', 'normal_total_exposed', 'normal_total_exposure_rate', 'optimal_total_count', 'optimal_total_exposed', 'optimal_total_exposure_rate', ...MONTHS.flatMap((month) => [`${month}_normal_count`, `${month}_normal_exposed`, `${month}_normal_exposure_rate`, `${month}_optimal_count`, `${month}_optimal_exposed`, `${month}_optimal_exposure_rate`])],
  ...subManagerMonthlyRows.map((row) => [
    row.name,
    row.assignedBranchCount,
    row.juneAssignedCount,
    row.normalTotal.count,
    row.normalTotal.exposed,
    fmtPct(row.normalTotal.exposureRate),
    row.optimalTotal.count,
    row.optimalTotal.exposed,
    fmtPct(row.optimalTotal.exposureRate),
    ...MONTHS.flatMap((month, index) => [
      row.normalMonths[index].count,
      row.normalMonths[index].exposed,
      fmtPct(row.normalMonths[index].exposureRate),
      row.optimalMonths[index].count,
      row.optimalMonths[index].exposed,
      fmtPct(row.optimalMonths[index].exposureRate),
    ]),
  ]),
]));

fs.writeFileSync(path.join(projectDir, 'optimal_specialist_monthly_summary.csv'), toCSV([
  ['optimal_specialist', 'total_count', 'total_exposed', 'total_exposure_rate', 'total_no_exposure', 'total_outside_top10', ...MONTHS.flatMap((month) => [`${month}_count`, `${month}_exposed`, `${month}_exposure_rate`, `${month}_no_exposure`, `${month}_outside_top10`])],
  ...optimalSpecialistMonthlyRows.map((row) => [
    row.name,
    row.total.count,
    row.total.exposed,
    fmtPct(row.total.exposureRate),
    row.total.noExposure,
    row.total.outsideTop10,
    ...row.months.flatMap((month) => [
      month.count,
      month.exposed,
      fmtPct(month.exposureRate),
      month.noExposure,
      month.outsideTop10,
    ]),
  ]),
]));

fs.writeFileSync(path.join(projectDir, 'manager_sub_writer_monthly_summary.csv'), toCSV([
  ['manager', 'assigned_branch_count', 'sub_assigned_branch_count', 'total_count', 'total_exposed', 'total_exposure_rate', 'total_no_exposure', 'total_outside_top10', ...MONTHS.flatMap((month) => [`${month}_count`, `${month}_exposed`, `${month}_exposure_rate`, `${month}_no_exposure`, `${month}_outside_top10`])],
  ...managerSubWriterMonthlyRows.map((row) => [
    row.manager,
    row.branchCount,
    row.assignedSubBranchCount,
    row.total.count,
    row.total.exposed,
    fmtPct(row.total.exposureRate),
    row.total.noExposure,
    row.total.outsideTop10,
    ...row.months.flatMap((month) => [
      month.count,
      month.exposed,
      fmtPct(month.exposureRate),
      month.noExposure,
      month.outsideTop10,
    ]),
  ]),
]));

fs.writeFileSync(path.join(projectDir, 'manager_optimal_specialist_monthly_summary.csv'), toCSV([
  ['manager', 'assigned_branch_count', 'total_count', 'total_exposed', 'total_exposure_rate', 'total_no_exposure', 'total_outside_top10', ...MONTHS.flatMap((month) => [`${month}_count`, `${month}_exposed`, `${month}_exposure_rate`, `${month}_no_exposure`, `${month}_outside_top10`])],
  ...managerOptimalSpecialistMonthlyRows.map((row) => [
    row.manager,
    row.branchCount,
    row.total.count,
    row.total.exposed,
    fmtPct(row.total.exposureRate),
    row.total.noExposure,
    row.total.outsideTop10,
    ...row.months.flatMap((month) => [
      month.count,
      month.exposed,
      fmtPct(month.exposureRate),
      month.noExposure,
      month.outsideTop10,
    ]),
  ]),
]));

function metricCard(label, value, note, tone = '') {
  return `<article class="metric ${tone}"><div class="label">${label}</div><div class="value">${value}</div><div class="sub">${note}</div></article>`;
}

function badge(label, cls) {
  return `<span class="badge ${cls}">${escapeHTML(label)}</span>`;
}

function renderBranchAuditTable() {
  return `<div class="table-wrap"><table>
    <thead><tr>
      <th>상태</th><th>과목/구분</th><th>지점</th><th>사수표 사수</th><th>발행건</th><th>노출율</th>
      <th>author_main 내 사수 비중</th><th>author_sub 내 사수 건</th><th>author_main 분포</th><th>author_sub 분포</th><th>유형</th>
    </tr></thead>
    <tbody>${branchAuditRows.map((row) => `<tr class="${row.statusClass}-row">
      <td>${badge(row.statusLabel, row.statusClass)}</td>
      <td>${escapeHTML(row.specialtyGroup)}</td>
      <td class="name">${escapeHTML(row.branch)}</td>
      <td>${escapeHTML(row.referenceManager)}</td>
      <td>${fmtInt(row.postCount)}</td>
      <td><strong>${fmtPct(row.exposureRate)}</strong><span class="mini">${fmtInt(row.exposedCount)}/${fmtInt(row.postCount)}</span></td>
      <td><strong>${fmtPct(row.managerAuthorMainRate)}</strong><span class="mini">${fmtInt(row.managerAuthorMainCount)}/${fmtInt(row.postCount)}</span></td>
      <td>${fmtInt(row.managerAuthorSubCount)}</td>
      <td class="memo">${escapeHTML(row.authorMainSummary)}</td>
      <td class="memo">${escapeHTML(row.authorSubSummary)}</td>
      <td class="memo">${escapeHTML(row.blogTypeSummary)}</td>
    </tr>`).join('')}</tbody>
  </table></div>`;
}

function renderUnmatchedTable() {
  return `<div class="table-wrap"><table>
    <thead><tr><th>분석 대상 지점</th><th>분류</th><th>발행건</th><th>노출율</th><th>작성자 분포</th><th>유형</th><th>기간</th></tr></thead>
    <tbody>${unmatchedRows.slice(0, 40).map((row) => `<tr>
      <td class="name">${escapeHTML(row.branch)}</td>
      <td>${escapeHTML(row.likelyRole)}</td>
      <td>${fmtInt(row.postCount)}</td>
      <td><strong>${fmtPct(row.exposureRate)}</strong><span class="mini">${fmtInt(row.exposedCount)}/${fmtInt(row.postCount)}</span></td>
      <td class="memo">${escapeHTML(row.authorMainSummary)}</td>
      <td class="memo">${escapeHTML(row.blogTypeSummary)}</td>
      <td>${row.first} ~ ${row.last}</td>
    </tr>`).join('')}</tbody>
  </table></div>`;
}

function renderAuthorSummaryTable() {
  return `<div class="table-wrap"><table>
    <thead><tr><th>author_main</th><th>발행건</th><th>노출건</th><th>노출율</th><th>미노출</th><th>10위밖</th><th>담당 지점수</th><th>유형</th><th>기간</th></tr></thead>
    <tbody>${authorSummaryRows.map((row) => `<tr>
      <td class="name">${escapeHTML(row.authorMain)}</td>
      <td>${fmtInt(row.postCount)}</td>
      <td>${fmtInt(row.exposedCount)}</td>
      <td><strong>${fmtPct(row.exposureRate)}</strong></td>
      <td>${fmtInt(row.noExposure)}</td>
      <td>${fmtInt(row.outsideTop10)}</td>
      <td>${fmtInt(row.branchCount)}</td>
      <td class="memo">${escapeHTML(row.blogTypeSummary)}</td>
      <td>${row.first} ~ ${row.last}</td>
    </tr>`).join('')}</tbody>
  </table></div>`;
}

function monthlyCell(row) {
  if (!row.count) return '<div class="month-cell empty">-<span>0건</span></div>';
  return `<div class="month-cell ${rateTone(row.exposureRate)}"><strong>${fmtPct(row.exposureRate)}</strong><span>${fmtInt(row.exposed)}/${fmtInt(row.count)}</span></div>`;
}

function totalCell(row) {
  if (!row.count) return '<div class="month-cell empty">-<span>0건</span></div>';
  return `<div class="month-cell ${rateTone(row.exposureRate)}"><strong>${fmtPct(row.exposureRate)}</strong><span>${fmtInt(row.exposed)}/${fmtInt(row.count)} · 진입 실패 ${fmtInt(row.noExposure + row.outsideTop10)}</span></div>`;
}

function splitTypeCell(normal, optimal) {
  if (!normal.count && !optimal.count) return '<div class="month-cell empty">-<span>0건</span></div>';
  return `<div class="split-cell">
    <div class="${rateTone(normal.exposureRate)}"><b>일반</b> ${fmtPct(normal.exposureRate)} <span>${fmtInt(normal.exposed)}/${fmtInt(normal.count)}</span></div>
    <div class="${rateTone(optimal.exposureRate)}"><b>최적</b> ${fmtPct(optimal.exposureRate)} <span>${fmtInt(optimal.exposed)}/${fmtInt(optimal.count)}</span></div>
  </div>`;
}

const chartColors = ['#2563eb', '#16a34a', '#dc2626', '#9333ea', '#d97706', '#0891b2', '#be123c', '#475569'];

function renderMonthlyChangeChart(rows) {
  const width = 1240;
  const height = 430;
  const pad = { top: 34, right: 42, bottom: 58, left: 82 };
  const plotWidth = width - pad.left - pad.right;
  const plotHeight = height - pad.top - pad.bottom;
  const xFor = (index) => pad.left + (plotWidth / (MONTHS.length - 1)) * index;
  const yFor = (value) => pad.top + plotHeight - (value ?? 0) * plotHeight;
  const gridValues = [1, 0.75, 0.5, 0.25, 0];
  const series = rows.map((row, rowIndex) => {
    const points = row.months
      .map((month, index) => ({
        x: xFor(index),
        y: yFor(month.exposureRate),
        value: month.exposureRate,
        month,
        monthIndex: index,
        monthLabel: MONTHS[index].replace('2026-', '') + '월',
      }))
      .filter((point) => point.month.count > 0 && point.value != null);
    const segments = [];
    let current = [];
    points.forEach((point, index) => {
      if (index > 0 && point.monthIndex !== points[index - 1].monthIndex + 1) {
        if (current.length > 1) segments.push(current);
        current = [];
      }
      current.push(point);
    });
    if (current.length > 1) segments.push(current);
    const color = chartColors[rowIndex % chartColors.length];
    return `<g class="chart-series" data-series="${escapeHTML(row.manager)}">
      ${segments.map((segment) => `<polyline points="${segment.map((point) => `${point.x.toFixed(1)},${point.y.toFixed(1)}`).join(' ')}" fill="none" stroke="${color}" stroke-width="4.5" stroke-linecap="round" stroke-linejoin="round"/>`).join('')}
      ${points.map((point) => `<circle class="chart-point" cx="${point.x.toFixed(1)}" cy="${point.y.toFixed(1)}" r="7" fill="${color}" data-tooltip="${escapeHTML(`${row.manager} ${point.monthLabel}: ${fmtPct(point.value)} (${fmtInt(point.month.exposed)}/${fmtInt(point.month.count)})`)}"></circle>`).join('')}
    </g>`;
  }).join('');
  return `<div class="chart-wrap">
    <svg class="line-chart" viewBox="0 0 ${width} ${height}" role="img" aria-label="사수 총괄 월간 노출율 변화">
      ${gridValues.map((value) => {
        const y = yFor(value);
        return `<g>
          <line x1="${pad.left}" y1="${y.toFixed(1)}" x2="${width - pad.right}" y2="${y.toFixed(1)}" class="grid-line"/>
          <text x="${pad.left - 16}" y="${(y + 5).toFixed(1)}" text-anchor="end" class="axis-label">${(value * 100).toFixed(0)}%</text>
        </g>`;
      }).join('')}
      ${MONTHS.map((month, index) => {
        const x = xFor(index);
        return `<text x="${x.toFixed(1)}" y="${height - 20}" text-anchor="middle" class="axis-label">${month.replace('2026-', '')}월</text>`;
      }).join('')}
      ${series}
    </svg>
    <div class="chart-legend">
      <button type="button" class="chart-legend-item chart-reset active" data-series="__all">전체 보기</button>
      ${rows.map((row, index) => `<button type="button" class="chart-legend-item" data-series="${escapeHTML(row.manager)}"><i style="background:${chartColors[index % chartColors.length]}"></i>${escapeHTML(row.manager)}</button>`).join('')}
    </div>
    <div class="chart-tooltip" aria-hidden="true"></div>
  </div>`;
}

function renderManagerTotalMonthlyTable() {
  return `<div class="table-wrap"><table>
    <thead><tr><th>사수</th><th>담당 지점수</th><th>총괄 총 발행건</th><th>총괄 노출율</th>${MONTHS.map((month) => `<th>${month.replace('2026-', '')}월</th>`).join('')}</tr></thead>
    <tbody>${managerMonthlyRows.map((row) => `<tr>
      <td class="name">${escapeHTML(row.manager)}</td>
      <td>${fmtInt(row.branchCount)}</td>
      <td>${fmtInt(row.total.count)}</td>
      <td>${totalCell(row.total)}</td>
      ${row.months.map(monthlyCell).map((cell) => `<td>${cell}</td>`).join('')}
    </tr>`).join('')}</tbody>
  </table></div>`;
}

function renderManagerMonthlyTable() {
  return `<div class="table-wrap"><table>
    <thead><tr><th>사수</th><th>담당 지점수</th><th>직접 작성 총 발행건</th><th>직접 작성 노출율</th>${MONTHS.map((month) => `<th>${month.replace('2026-', '')}월</th>`).join('')}</tr></thead>
    <tbody>${managerDirectWriterMonthlyRows.map((row) => `<tr>
      <td class="name">${escapeHTML(row.manager)}</td>
      <td>${fmtInt(row.branchCount)}</td>
      <td>${fmtInt(row.total.count)}</td>
      <td>${totalCell(row.total)}</td>
      ${row.months.map(monthlyCell).map((cell) => `<td>${cell}</td>`).join('')}
    </tr>`).join('')}</tbody>
  </table></div>`;
}

function renderManagerBranchDetailTable() {
  return `<div class="table-wrap"><table>
    <thead><tr><th>사수</th><th>과목/구분</th><th>지점</th><th>총계</th><th>일반 블로그</th><th>최적 블로그</th>${MONTHS.map((month) => `<th>${month.replace('2026-', '')}월</th>`).join('')}</tr></thead>
    <tbody>${managerBranchMonthlyRows.map((row) => `<tr>
      <td class="name">${escapeHTML(row.manager)}</td>
      <td>${escapeHTML(row.specialtyGroup)}</td>
      <td class="name">${escapeHTML(row.branch)}</td>
      <td>${totalCell(row.total)}</td>
      <td>${totalCell(row.normalTotal)}</td>
      <td>${totalCell(row.optimalTotal)}</td>
      ${MONTHS.map((month, index) => `<td>${splitTypeCell(row.normalMonths[index], row.optimalMonths[index])}</td>`).join('')}
    </tr>`).join('')}</tbody>
  </table></div>`;
}

function renderManagerOverviewTable() {
  const directByManager = new Map(managerDirectWriterMonthlyRows.map((row) => [row.manager, row]));
  const subWriterByManager = new Map(managerSubWriterMonthlyRows.map((row) => [row.manager, row]));
  const optimalByManager = new Map(managerOptimalBranchMonthlyRows.map((row) => [row.manager, row]));
  return `<div class="table-wrap"><table class="summary-table">
    <thead><tr><th>사수</th><th>담당 지점수</th><th>사수 직접 원고</th><th>최적 블로그</th><th>부사수 원고</th><th>담당 지점 전체</th></tr></thead>
    <tbody>${managerMonthlyRows.map((row) => {
      const direct = directByManager.get(row.manager);
      const subWriter = subWriterByManager.get(row.manager);
      const optimal = optimalByManager.get(row.manager);
      return `<tr>
        <td class="name">${escapeHTML(row.manager)}</td>
        <td>${fmtInt(row.branchCount)}</td>
        <td>${totalCell(direct?.total || emptyStat())}</td>
        <td>${totalCell(optimal?.total || emptyStat())}</td>
        <td>${totalCell(subWriter?.total || emptyStat())}</td>
        <td>${totalCell(row.total)}</td>
      </tr>`;
    }).join('')}</tbody>
  </table></div>`;
}

function renderManagerOptimalBranchMonthlyTable() {
  return `<div class="table-wrap"><table>
    <thead><tr><th>사수</th><th>담당 지점수</th><th>최적블 총 발행건</th><th>최적블 총 노출율</th>${MONTHS.map((month) => `<th>${month.replace('2026-', '')}월</th>`).join('')}</tr></thead>
    <tbody>${managerOptimalBranchMonthlyRows.map((row) => `<tr>
      <td class="name">${escapeHTML(row.manager)}</td>
      <td>${fmtInt(row.branchCount)}</td>
      <td>${fmtInt(row.total.count)}</td>
      <td>${totalCell(row.total)}</td>
      ${row.months.map(monthlyCell).map((cell) => `<td>${cell}</td>`).join('')}
    </tr>`).join('')}</tbody>
  </table></div>`;
}

function renderSubManagerMonthlyTable() {
  return `<div class="table-wrap"><table>
    <thead><tr><th>사수</th><th>담당 지점수</th><th>부사수 배정 지점수</th><th>부사수 원고 총계</th>${MONTHS.map((month) => `<th>${month.replace('2026-', '')}월</th>`).join('')}</tr></thead>
    <tbody>${managerSubWriterMonthlyRows.map((row) => `<tr>
      <td class="name">${escapeHTML(row.manager)}</td>
      <td>${fmtInt(row.branchCount)}</td>
      <td>${fmtInt(row.assignedSubBranchCount)}</td>
      <td>${totalCell(row.total)}</td>
      ${row.months.map(monthlyCell).map((cell) => `<td>${cell}</td>`).join('')}
    </tr>`).join('')}</tbody>
  </table></div>`;
}

function renderOptimalSpecialistMonthlyTable() {
  return `<div class="table-wrap"><table>
    <thead><tr><th>사수</th><th>담당 지점수</th><th>최적전문 발행건</th><th>최적전문 노출율</th>${MONTHS.map((month) => `<th>${month.replace('2026-', '')}월</th>`).join('')}</tr></thead>
    <tbody>${managerOptimalSpecialistMonthlyRows.map((row) => `<tr>
      <td class="name">${escapeHTML(row.manager)}</td>
      <td>${fmtInt(row.branchCount)}</td>
      <td>${fmtInt(row.total.count)}</td>
      <td>${totalCell(row.total)}</td>
      ${row.months.map(monthlyCell).map((cell) => `<td>${cell}</td>`).join('')}
    </tr>`).join('')}</tbody>
  </table></div>`;
}

function renderSubManagerAuditTable() {
  return `<div class="table-wrap"><table>
    <thead><tr>
      <th>상태</th><th>과목/구분</th><th>지점</th><th>사수</th><th>부사수</th><th>6월 부사수 배정 수량</th>
      <th>6월 지점 발행</th><th>DB author_main 확인건</th><th>배정 대비 확인율</th><th>부사수 작성분 노출율</th><th>6월 author_main 분포</th><th>유형</th>
    </tr></thead>
    <tbody>${subAuditRows.map((row) => `<tr class="${row.statusClass}-row">
      <td>${badge(row.statusLabel, row.statusClass)}</td>
      <td>${escapeHTML(row.specialtyGroup)}</td>
      <td class="name">${escapeHTML(row.branch)}</td>
      <td>${escapeHTML(row.manager)}</td>
      <td>${escapeHTML(row.subManager || '-')}</td>
      <td>${row.expectedCount == null ? '-' : fmtInt(row.expectedCount)}</td>
      <td><strong>${fmtInt(row.junePostCount)}</strong><span class="mini">${fmtInt(row.juneExposedCount)}/${fmtInt(row.junePostCount)} · ${fmtPct(row.juneExposureRate)}</span></td>
      <td><strong>${fmtInt(row.actualSubAuthorCount)}</strong><span class="mini">${fmtInt(row.actualSubAuthorExposedCount)}/${fmtInt(row.actualSubAuthorCount)}</span></td>
      <td><strong>${fmtPct(row.expectedMatchRate)}</strong></td>
      <td><strong>${fmtPct(row.actualSubAuthorExposureRate)}</strong></td>
      <td class="memo">${escapeHTML(row.branchAuthorMainSummary)}</td>
      <td class="memo">${escapeHTML(row.subAuthorBlogTypeSummary)}</td>
    </tr>`).join('')}</tbody>
  </table></div>`;
}

function renderSubManagerSummaryTable() {
  return `<div class="table-wrap"><table>
    <thead><tr><th>부사수</th><th>6월 부사수 배정 수량</th><th>DB author_main 확인건</th><th>배정 대비 확인율</th><th>노출건</th><th>노출율</th><th>지점수</th><th>지점별 확인</th></tr></thead>
    <tbody>${subAuthorSummaryRows.map((row) => `<tr>
      <td class="name">${escapeHTML(row.subManager)}</td>
      <td>${fmtInt(row.expectedCount)}</td>
      <td>${fmtInt(row.actualCount)}</td>
      <td><strong>${fmtPct(row.expectedMatchRate)}</strong></td>
      <td>${fmtInt(row.exposedCount)}</td>
      <td><strong>${fmtPct(row.exposureRate)}</strong></td>
      <td>${fmtInt(row.branchCount)}</td>
      <td class="memo">${escapeHTML(row.branchSummary)}</td>
    </tr>`).join('')}</tbody>
  </table></div>`;
}

const matchedPostCount = analysisRows.filter((row) => row.reference_matched).length;
const managerMatchedPostCount = analysisRows.filter((row) => row.reference_matched && row.reference_manager).length;
const authorMainFilledCount = analysisRows.filter((row) => cleanText(row.author_main)).length;
const authorSubFilledCount = analysisRows.filter((row) => cleanText(row.author_sub)).length;
const ignoredPostCount = rows.length - analysisRows.length;
const branchMatchedCount = branchAuditRows.filter((row) => row.postCount > 0).length;
const managerBranchMatchedCount = branchAuditRows.filter((row) => row.referenceManager && row.postCount > 0).length;
const okBranchCount = branchAuditRows.filter((row) => row.statusClass === 'ok').length;
const warnBranchCount = branchAuditRows.filter((row) => ['warn', 'danger', 'watch'].includes(row.statusClass)).length;
const subAssignedBranchCount = subAuditRows.filter((row) => row.subManager).length;
const subExpectedTotal = subAuditRows.reduce((sum, row) => sum + (row.expectedCount || 0), 0);
const subActualTotal = subAuditRows.reduce((sum, row) => sum + row.actualSubAuthorCount, 0);
const subConfirmedBranchCount = subAuditRows.filter((row) => ['ok', 'watch'].includes(row.statusClass) && row.subManager).length;
const roleOverlapNames = managerNames
  .filter((name) => subAuthorSummaryRows.some((row) => row.subManager === name))
  .sort((a, b) => a.localeCompare(b, 'ko'));

const html = `<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>담당자별 상위 노출 성과 분석</title>
  <style>
    :root{--bg:#f3f6fb;--card:#fff;--ink:#172033;--muted:#66758f;--line:#dbe4f0;--head:#f7f9fc;--blue:#2563eb;--green:#16a34a;--amber:#d97706;--orange:#ea580c;--red:#dc2626}
    *{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}.page{max-width:1840px;margin:0 auto;padding:32px}header{display:flex;justify-content:space-between;gap:24px;align-items:end;margin-bottom:22px}h1{margin:0 0 8px;font-size:34px}p{margin:0;color:var(--muted);font-weight:700;line-height:1.55}.pill{border:1px solid var(--line);border-radius:999px;background:#fff;padding:10px 14px;color:var(--muted);font-weight:900;white-space:nowrap}.tabs{display:flex;gap:8px;flex-wrap:wrap;margin:18px 0 22px}.tab-btn{border:1px solid var(--line);background:#fff;color:var(--muted);font-weight:900;padding:12px 18px;border-radius:10px;cursor:pointer;font-size:16px}.tab-btn.active{background:#213148;color:#fff}.tab{display:none}.tab.active{display:block}.metrics{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px;margin-bottom:16px}.metric{background:#fff;border:1px solid var(--line);border-radius:10px;padding:17px}.label{font-size:14px;color:var(--muted);font-weight:900}.value{font-size:32px;font-weight:950;margin-top:8px}.sub{font-size:13px;color:var(--muted);margin-top:8px;font-weight:800}.metric.blue .value{color:var(--blue)}.metric.green .value{color:var(--green)}.metric.red .value{color:var(--red)}.card{background:var(--card);border:1px solid var(--line);border-radius:10px;margin-bottom:18px;overflow:hidden;box-shadow:0 12px 30px rgba(20,36,64,.04)}.card-head{display:flex;justify-content:space-between;align-items:center;gap:16px;padding:22px 24px;border-bottom:1px solid var(--line)}h2,h3{margin:0}.card-head span{color:var(--muted);font-weight:800}.note-box{padding:18px 22px;color:var(--muted);font-weight:800;line-height:1.6;background:#fbfdff}.table-wrap{overflow:auto}table{width:100%;min-width:1320px;border-collapse:collapse}.summary-table{min-width:1080px}th,td{padding:14px 16px;border-bottom:1px solid var(--line);text-align:center;font-size:15px;font-weight:700;vertical-align:middle}th{background:var(--head);color:#2f3c52;font-weight:950;white-space:nowrap}.name{font-weight:950}.memo{max-width:420px;white-space:normal;word-break:keep-all;overflow-wrap:anywhere;color:var(--muted);font-size:13px}.mini{display:block;margin-top:3px;color:var(--muted);font-size:12px}.month-cell{display:flex;flex-direction:column;gap:3px;align-items:center;border-radius:8px;padding:7px 8px}.month-cell strong{font-size:16px}.month-cell span{font-size:12px;color:var(--muted)}.month-cell.empty{color:#94a3b8;background:#f8fafc}.month-cell.ok{background:#ecfdf3;color:#147a3d}.month-cell.watch{background:#fff8dc;color:#9a5c00}.month-cell.warn{background:#fff3e8;color:#b45309}.month-cell.danger{background:#fff1f2;color:#be123c}.split-cell{display:grid;gap:5px;min-width:132px}.split-cell div{white-space:nowrap;border-radius:7px;padding:4px 6px}.split-cell div.ok{background:#ecfdf3;color:#147a3d}.split-cell div.watch{background:#fff8dc;color:#9a5c00}.split-cell div.warn{background:#fff3e8;color:#b45309}.split-cell div.danger{background:#fff1f2;color:#be123c}.split-cell b{display:inline-block;min-width:32px;color:#2f3c52}.split-cell span{color:var(--muted);font-size:12px}.badge{display:inline-flex;align-items:center;justify-content:center;min-width:68px;padding:7px 11px;border-radius:999px;font-weight:950;font-size:13px}.badge.ok{background:#dcfce7;color:#15803d}.badge.watch{background:#fef3c7;color:#a16207}.badge.warn{background:#ffedd5;color:#c2410c}.badge.danger{background:#fee2e2;color:#be123c}.badge.muted{background:#e5e7eb;color:#64748b}.ok-row{background:#fff}.watch-row{background:#fff8dc;color:#8a3c08}.warn-row{background:#fff3e6;color:#9a3412}.danger-row{background:#fff0f2;color:#b20f3a}.muted-row{background:#f8fafc;color:#64748b}@media(max-width:1100px){.page{padding:20px}header{display:block}.pill{display:inline-flex;margin-top:12px}.metrics{grid-template-columns:repeat(2,minmax(0,1fr))}}
    .chart-wrap{position:relative;padding:22px 24px 26px;overflow:auto}.line-chart{width:100%;min-width:1040px;height:auto;display:block}.grid-line{stroke:#dbe4f0;stroke-width:2}.axis-label{fill:#66758f;font-size:20px;font-weight:900}.chart-series{transition:opacity .15s ease}.chart-series.dimmed{opacity:.12}.chart-series.focused{opacity:1}.chart-series circle{stroke:#fff;stroke-width:3;cursor:pointer}.chart-legend{display:flex;gap:12px;flex-wrap:wrap;margin-top:14px}.chart-legend-item{display:inline-flex;align-items:center;gap:8px;border:1px solid var(--line);background:#fff;border-radius:999px;padding:7px 11px;color:#43536d;font-weight:900;cursor:pointer;font:inherit}.chart-legend-item.active{background:#213148;color:#fff;border-color:#213148}.chart-reset{padding:7px 13px}.chart-legend i{width:13px;height:13px;border-radius:4px;display:inline-block}.chart-tooltip{position:fixed;display:none;z-index:30;pointer-events:none;background:#172033;color:#fff;border-radius:8px;padding:9px 11px;font-weight:900;font-size:14px;box-shadow:0 12px 30px rgba(15,23,42,.22);white-space:nowrap}.chart-tooltip.active{display:block}
  </style>
</head>
<body>
  <main class="page">
    <header>
      <div>
        <h1>담당자별 상위 노출 성과 분석</h1>
        <p>사수가 맡은 지점의 일반 블로그, 최적 블로그, 부사수 원고 성과를 분리해 봅니다.</p>
      </div>
      <div class="pill">대상 기간: 2026-01-01 ~ 2026-06-30 · 데이터 검수: 2026-07-02</div>
    </header>

    <nav class="tabs">
      <button class="tab-btn active" data-tab="summary">요약</button>
      <button class="tab-btn" data-tab="manager-total-monthly">월간 변화량</button>
      <button class="tab-btn" data-tab="manager-monthly">사수</button>
      <button class="tab-btn" data-tab="manager-optimal">최적</button>
      <button class="tab-btn" data-tab="sub-manager-monthly">부사수</button>
      <button class="tab-btn" data-tab="manager-branch-detail">상세보기</button>
    </nav>

    <section id="summary" class="tab active">
      <div class="metrics">
        ${metricCard('전체 발행건', fmtInt(analysisRows.length), `분석 제외 ${fmtInt(ignoredPostCount)}건`)}
        ${metricCard('사수 담당 총 발행건', fmtInt(managerMatchedPostCount), `${fmtPct(pct(managerMatchedPostCount, analysisRows.length))}`)}
        ${metricCard('사수 담당 지점', fmtInt(managerReferenceRows.length), `발행 확인 ${fmtInt(managerBranchMatchedCount)}개`)}
        ${metricCard('부사수 배정 지점', fmtInt(subAssignedBranchCount), `확인 ${fmtInt(subConfirmedBranchCount)}개`)}
      </div>
      <section class="card">
        <div class="card-head"><h3>사수별 핵심 요약</h3><span>누적 기준 · 월별 상세는 각 탭에서 확인</span></div>
        ${renderManagerOverviewTable()}
      </section>
      <section class="card">
        <div class="card-head"><h3>역할별 해석 기준</h3><span>성과 분석 전 기준 정리</span></div>
        <div class="note-box">
          <div>최적 블로그는 사수가 맡은 지점의 전체 최적 발행 성과입니다.</div>
          <div>사수 탭은 author_main이 사수명과 일치하는 직접 작성 일반 원고만 집계합니다.</div>
          <div>최적 탭은 사수가 맡은 지점의 최적 블로그 성과만 집계합니다.</div>
          <div>부사수 월별 표는 사수가 직접 관리하는 지점에서 부사수 원고로 확인된 일반 블로그 성과를 사수 기준으로 집계합니다.</div>
          <div>서동균·박주혁 발행분은 최적 블로그와 중복성이 높아 보고서 화면에서는 제외하고, 내부 확인 CSV로만 남깁니다.</div>
          <div>사수와 부사수를 겸하는 담당자: ${escapeHTML(roleOverlapNames.join(', ') || '없음')}</div>
          <div>작성자명 전체 분포는 내부 검증 CSV로만 남기고, 보고서 본문에서는 사수/부사수 역할별 표를 우선합니다.</div>
        </div>
      </section>
    </section>

    <section id="manager-total-monthly" class="tab">
      <section class="card">
        <div class="card-head"><h3>사수 총괄 월간 변화량</h3><span>사수 담당 지점 전체 기준 · 직접/최적/부사수 발행분 포함</span></div>
        <div class="note-box">
          <div>사수가 총괄로 맡고 있는 지점의 월별 전체 노출율입니다. 사수 직접 작성 원고, 최적 블로그, 부사수 원고를 모두 포함합니다.</div>
          <div>그래프의 점에 마우스를 올리면 월별 노출율과 노출건/발행건을 확인할 수 있습니다.</div>
        </div>
        ${renderMonthlyChangeChart(managerMonthlyRows)}
        ${renderManagerTotalMonthlyTable()}
      </section>
    </section>

    <section id="manager-monthly" class="tab">
      <section class="card">
        <div class="card-head"><h3>사수 직접 작성 원고</h3><span>author_main = 사수명 · 일반 블로그만 집계</span></div>
        ${renderManagerMonthlyTable()}
      </section>
    </section>

    <section id="manager-optimal" class="tab">
      <section class="card">
        <div class="card-head"><h3>사수 담당 지점 최적 블로그</h3><span>사수가 컨트롤하는 지점의 최적 블로그 성과</span></div>
        ${renderManagerOptimalBranchMonthlyTable()}
      </section>
    </section>

    <section id="sub-manager-monthly" class="tab">
      <section class="card">
        <div class="card-head"><h3>사수별 부사수 원고 성과</h3><span>일반 블로그만 집계 · 부사수명보다 관리 사수 기준</span></div>
        ${renderSubManagerMonthlyTable()}
      </section>
    </section>

    <section id="manager-branch-detail" class="tab">
      <section class="card">
        <div class="card-head"><h3>담당 사수-월별-지점별 성과</h3><span>사수 담당 지점 기준 · 직접 작성분과 부사수/최적 발행분 포함</span></div>
        <div class="note-box">
          <div>정렬 기준은 1차 사수명 오름차순, 2차 지점명 오름차순입니다.</div>
          <div>각 행은 사수가 담당하는 지점 1개입니다. 작성자가 사수인지, 부사수인지, 최적 담당자인지와 관계없이 해당 지점을 맡은 사수의 관리 성과로 집계합니다.</div>
          <div>월별 칸은 일반 블로그와 최적 블로그를 나눠 표시합니다. 진입 실패는 미노출과 10위권 밖을 합산한 값입니다.</div>
        </div>
        ${renderManagerBranchDetailTable()}
      </section>
    </section>

  </main>
  <script>
    document.querySelectorAll('.tab-btn').forEach((button) => {
      button.addEventListener('click', () => {
        document.querySelectorAll('.tab-btn').forEach((item) => item.classList.remove('active'));
        document.querySelectorAll('.tab').forEach((item) => item.classList.remove('active'));
        button.classList.add('active');
        document.getElementById(button.dataset.tab).classList.add('active');
      });
    });
    const chartTooltip = document.querySelector('.chart-tooltip');
    document.querySelectorAll('.chart-point').forEach((point) => {
      point.addEventListener('mouseenter', (event) => {
        chartTooltip.textContent = event.currentTarget.dataset.tooltip;
        chartTooltip.classList.add('active');
      });
      point.addEventListener('mousemove', (event) => {
        chartTooltip.style.left = event.clientX + 14 + 'px';
        chartTooltip.style.top = event.clientY + 14 + 'px';
      });
      point.addEventListener('mouseleave', () => {
        chartTooltip.classList.remove('active');
      });
    });
    const chartSeries = Array.from(document.querySelectorAll('.chart-series'));
    const legendItems = Array.from(document.querySelectorAll('.chart-legend-item'));
    let pinnedSeries = '__all';

    function focusSeries(seriesName) {
      chartSeries.forEach((series) => {
        const matched = seriesName === '__all' || series.dataset.series === seriesName;
        series.classList.toggle('dimmed', !matched);
        series.classList.toggle('focused', matched && seriesName !== '__all');
      });
      legendItems.forEach((item) => {
        item.classList.toggle('active', item.dataset.series === seriesName);
      });
    }

    legendItems.forEach((item) => {
      item.addEventListener('mouseenter', () => focusSeries(item.dataset.series));
      item.addEventListener('mouseleave', () => focusSeries(pinnedSeries));
      item.addEventListener('click', () => {
        pinnedSeries = item.dataset.series;
        focusSeries(pinnedSeries);
      });
    });
  </script>
</body>
</html>`;

fs.writeFileSync(path.join(projectDir, 'manager_author_column_audit.html'), html);
fs.writeFileSync(path.join(projectDir, 'manager_performance_report.html'), html);

console.log(JSON.stringify({
  rows: analysisRows.length,
  ignoredPostCount,
  matchedPostCount,
  managerMatchedPostCount,
  referenceBranches: referenceRows.length,
  managerReferenceBranches: managerReferenceRows.length,
  branchMatchedCount,
  managerBranchMatchedCount,
  authorMainFilledCount,
  authorSubFilledCount,
  output: 'manager_author_column_audit.html',
  report: 'manager_performance_report.html',
}, null, 2));

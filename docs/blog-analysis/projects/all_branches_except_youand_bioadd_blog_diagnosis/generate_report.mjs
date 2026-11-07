import fs from 'node:fs';
import path from 'node:path';

const projectDir = path.dirname(new URL(import.meta.url).pathname);
const detailPath = path.join(projectDir, 'target_detail.csv');

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
      } else if (char === '"') {
        quoted = false;
      } else {
        field += char;
      }
      continue;
    }

    if (char === '"') {
      quoted = true;
    } else if (char === ',') {
      row.push(field);
      field = '';
    } else if (char === '\n') {
      row.push(field);
      rows.push(row);
      row = [];
      field = '';
    } else if (char !== '\r') {
      field += char;
    }
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

function pct(numerator, denominator) {
  if (!denominator) return null;
  return numerator / denominator;
}

function fmtPct(value) {
  return value == null ? '-' : `${(value * 100).toFixed(1)}%`;
}

function fmtInt(value) {
  return Number(value || 0).toLocaleString('ko-KR');
}

function escapeHTML(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

function cleanBranchName(value) {
  let text = String(value || '').trim();
  text = text.replace(/^\d+\s+/, '');
  text = text.replace(/\s+/g, ' ');
  text = text.replace(/\s*(최적배포|준최배포|브블|NB)\s*\d*$/i, '');
  text = text.replace(/\s+\d+$/, '');
  text = text.replace(/\s*\(.*?\)\s*$/, '');
  text = text.replace(/\s+/g, ' ').trim();

  if (/^디자인\s*브블/.test(text)) text = '디자인치과';
  if (/^프라임\s*\d+/.test(text)) text = '프라임치과의원';
  if (/^천지세무\d+$/.test(text)) text = '천지세무';

  const aliases = {
    '365봄': '365봄치과',
    '봄': '365봄치과',
    '굿플중랑': '닥터굿플란트치과 중랑',
    '맑은양평': '맑은미소치과 양평',
    '헤리티지': '헤리티지플란트치과 광명',
    '헤리티지플란트치과': '헤리티지플란트치과 광명',
    '더편한': '더편한류마마디의원',
    '더편한류마마디의원 창원': '더편한류마마디의원',
    '디자인': '디자인치과',
    '디자인치과 노원': '디자인치과',
    '이다움': '서울이다움치과',
    '이다움4': '서울이다움치과',
    '세브란스': '충주연세세브란스치과',
    '용인터미널': '용인터미널퍼스트치과',
    '조은': '조은피부과',
    '신현편안': '신현편안내과',
    '에이플': '에이플러스치과',
    '파인드': '파인드피부과',
    '치과다운': '치과다운치과',
    '모세정형외과': '모세정형외과의원',
    '이효진산부인과': '이효진 여성의원',
    '이효진여성의원': '이효진 여성의원',
    '톤앤톤피부과': '톤앤톤 피부과',
    '벨로이스': '벨로이스의원',
    '프라임': '프라임치과의원',
    '주원튼튼': '주원튼튼한의원',
    '성모튼튼': '성모튼튼365재활의학과',
    '청담뷰엘': '청담뷰엘의원',
    '기드온치과': '기드온치과의원',
    '더스마트치과': '더스마트치과의원',
    '참조은': '참조은+참조은nb',
    '참조은치과': '참조은+참조은nb',
  };

  return aliases[text] || text || '(blank)';
}

const referenceBranches = [
  ['로렐의원', '피부과', '솔루션'],
  ['더편한류마마디의원', '정형외과', '로컬'],
  ['이효진 여성의원', '산부인과', '로컬'],
  ['신현편안내과의원', '내과', '로컬'],
  ['두청한의원', '한의원', '로컬'],
  ['톤앤톤 피부과', '피부과', '솔루션'],
  ['모세정형외과의원', '정형외과', '솔루션'],
  ['벨로이스의원', '피부과', '로컬'],
  ['프라임치과의원', '치과', '로컬'],
  ['주원튼튼한의원', '한의원', '로컬'],
  ['성모튼튼365재활의학과', '재활의학과', '로컬'],
  ['청담뷰엘의원', '피부과', '로컬'],
  ['기드온치과의원', '치과', '로컬'],
  ['더스마트치과의원', '치과', '로컬'],
  ['디자인치과', '치과', '로컬'],
  ['헤리티지플란트치과 광명', '치과', '로컬'],
  ['맑은미소치과 양평', '치과', '로컬'],
  ['치과다운치과', '치과', '로컬'],
  ['서울이다움치과', '치과', '로컬'],
  ['닥터굿플란트치과 중랑', '치과', '로컬'],
  ['에이플러스치과', '치과', '로컬'],
  ['충주연세세브란스치과', '치과', '로컬'],
  ['참조은+참조은nb', '치과', '로컬'],
  ['365봄치과', '치과', '로컬'],
  ['용인터미널퍼스트치과', '치과', '로컬'],
  ['천지세무', '세무', '로컬'],
  ['세무법인 현답', '세무', '로컬'],
  ['조은피부과', '피부과', '로컬'],
  ['파인드피부과', '피부과', '로컬'],
  ['연세영의원', '피부과', '로컬'],
  ['클리어서울안과', '안과', '로컬'],
];

const referenceMap = new Map(referenceBranches.map(([branch, specialty, operationGroup]) => [
  branch,
  { branch, specialty, operationGroup },
]));

const extraReferenceAliases = {
  '신현편안내과': '신현편안내과의원',
  '톤앤톤피부과': '톤앤톤 피부과',
  '벨로이스': '벨로이스의원',
  '주원튼튼': '주원튼튼한의원',
  '성모튼튼': '성모튼튼365재활의학과',
  '청담뷰엘': '청담뷰엘의원',
  '기드온치과': '기드온치과의원',
  '더스마트치과': '더스마트치과의원',
  '디자인치과 노원': '디자인치과',
  '참조은': '참조은+참조은nb',
  '참조은치과': '참조은+참조은nb',
};

function referenceFor(branch) {
  const canonical = extraReferenceAliases[branch] || branch;
  return referenceMap.get(canonical) || null;
}

function normalizedBranch(row) {
  return cleanBranchName(row.project_branch || row.branch_name || row.target_branch);
}

function inferSpecialty(branch) {
  if (/치과|플란트|임플란트|구강|덴탈|이다움|참조은|헤리티지|맑은미소|굿플란트|세브란스|용인터미널|디자인|에이플러스|치과다운/.test(branch)) return '치과';
  if (/안과|라식|라섹|스마일|백내장|렌즈삽입/.test(branch)) return '안과';
  if (/한의원|한방|두청/.test(branch)) return '한의원';
  if (/산부인과|여성의원|여성병원|여성성형/.test(branch)) return '산부인과/여성의원';
  if (/정형외과|튼튼|마디|류마|통증/.test(branch)) return '정형외과/통증';
  if (/내과|건강검진|신현편안/.test(branch)) return '내과/검진';
  if (/피부과|피부|뷰엘|벨로이스|로렐|레리|톤앤톤|파인드|프라임|조은피부/.test(branch)) return '피부과/의원';
  if (/성형외과|성형/.test(branch)) return '성형외과';
  if (/세무|세무법인/.test(branch)) return '세무';
  if (/의원$|클리닉|병원$/.test(branch)) return '의원/병원';
  return '확인필요';
}

function emptyStat() {
  return {
    count: 0,
    exposed: 0,
    noExposure: 0,
    outsideTop10: 0,
    first: '',
    last: '',
    variants: new Map(),
    accounts: new Map(),
  };
}

function addStat(stat, row) {
  stat.count += 1;
  stat.exposed += row.top10_success;
  stat.noExposure += row.no_exposure;
  stat.outsideTop10 += row.outside_top10;
  if (!stat.first || row.published_at < stat.first) stat.first = row.published_at;
  if (!stat.last || row.published_at > stat.last) stat.last = row.published_at;
  const variant = row.branch_name || row.target_branch || '(blank)';
  stat.variants.set(variant, (stat.variants.get(variant) || 0) + 1);
  if (row.blog_id) stat.accounts.set(row.blog_id, (stat.accounts.get(row.blog_id) || 0) + 1);
}

function statRate(stat) {
  return pct(stat.exposed, stat.count);
}

function statusFor(rate, count = 0) {
  if (!count) return ['없음', 'muted'];
  if (rate == null) return ['없음', 'muted'];
  if (rate < 0.4) return ['위험', 'danger'];
  if (rate < 0.55) return ['주의', 'warn'];
  if (rate < 0.7) return ['관찰', 'watch'];
  return ['양호', 'ok'];
}

function topVariants(stat, limit = 4) {
  return [...stat.variants.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, limit)
    .map(([name, count]) => `${name} ${count}건`)
    .join(' / ');
}

function updateMap(map, key, row) {
  const stat = map.get(key) || emptyStat();
  addStat(stat, row);
  map.set(key, stat);
  return stat;
}

const rawRows = parseCSV(fs.readFileSync(detailPath, 'utf8'));
const headers = rawRows.shift();
const idx = Object.fromEntries(headers.map((name, index) => [name, index]));

const rows = rawRows.map((raw) => {
  const rankRaw = raw[idx.exposure_rank];
  const rank = rankRaw === '' ? null : Number(rankRaw);
  return {
    target_branch: raw[idx.target_branch],
    analysis_group: raw[idx.analysis_group],
    published_at: raw[idx.published_at],
    branch_name: raw[idx.branch_name],
    project_branch: raw[idx.project_branch],
    content_number: raw[idx.content_number],
    keyword: raw[idx.keyword],
    exposure_rank: rank,
    rank_status: raw[idx.rank_status],
    top10_success: Number(raw[idx.top10_success] || 0),
    no_exposure: Number(raw[idx.no_exposure] || 0),
    outside_top10: Number(raw[idx.outside_top10] || 0),
    post_type: raw[idx.post_type],
    post_type_main: raw[idx.post_type_main],
    post_type_sub: raw[idx.post_type_sub],
    blog_channel: raw[idx.blog_channel],
    blog_id: raw[idx.blog_id],
    title: raw[idx.title],
    status: raw[idx.status],
    published_url: raw[idx.published_url],
    id: raw[idx.id],
  };
});

const normalizedRows = rows.map((row) => {
  const branch = normalizedBranch(row);
  const reference = referenceFor(branch);
  return {
    ...row,
    normalized_branch: reference?.branch || branch,
    specialty: reference?.specialty || inferSpecialty(branch),
    operation_group: reference?.operationGroup || '기준표 외 데이터',
    reference_matched: Boolean(reference),
    blog_type: row.blog_channel === 'opt' ? '최적 블로그' : '일반 블로그',
  };
});

const unmatchedRows = normalizedRows.filter((row) => !row.reference_matched);
const analysisRows = normalizedRows.filter((row) => row.reference_matched);

const overall = emptyStat();
const byType = new Map();
const byBranch = new Map();
const bySpecialty = new Map();
const byMonthType = new Map();
const byBranchType = new Map();
const byBranchAccountType = new Map();
const byBranchMonthType = new Map();

for (const row of analysisRows) {
  addStat(overall, row);
  updateMap(byType, row.blog_type, row);
  updateMap(byBranch, row.normalized_branch, row);
  updateMap(bySpecialty, row.specialty, row);
  updateMap(byMonthType, `${row.published_at.slice(0, 7)}|${row.blog_type}`, row);
  updateMap(byMonthType, `${row.published_at.slice(0, 7)}|종합`, row);
  updateMap(byBranchType, `${row.normalized_branch}|${row.blog_type}`, row);
  updateMap(byBranchAccountType, `${row.normalized_branch}|${row.blog_type}|${row.blog_id || '(blank)'}`, row);
  updateMap(byBranchMonthType, `${row.normalized_branch}|${row.published_at.slice(0, 7)}|${row.blog_type}`, row);
  updateMap(byBranchMonthType, `${row.normalized_branch}|${row.published_at.slice(0, 7)}|종합`, row);
}

const branchRows = [...byBranch.entries()].map(([branch, stat]) => {
  const general = byBranchType.get(`${branch}|일반 블로그`) || emptyStat();
  const optimal = byBranchType.get(`${branch}|최적 블로그`) || emptyStat();
  const reference = referenceFor(branch);
  return {
    branch,
    specialty: reference?.specialty || inferSpecialty(branch),
    operationGroup: reference?.operationGroup || '기준표 외 데이터',
    stat,
    general,
    optimal,
    first: stat.first,
    last: stat.last,
    rate: statRate(stat),
    generalRate: statRate(general),
    optimalRate: statRate(optimal),
  };
}).sort((a, b) => a.first.localeCompare(b.first) || a.branch.localeCompare(b.branch, 'ko'));

const specialtyRows = [...bySpecialty.entries()].map(([specialty, stat]) => ({
  specialty,
  stat,
  rate: statRate(stat),
  branches: branchRows.filter((row) => row.specialty === specialty).length,
})).sort((a, b) => b.stat.count - a.stat.count || a.specialty.localeCompare(b.specialty, 'ko'));

const monthRows = [...byMonthType.entries()].map(([key, stat]) => {
  const [month, blogType] = key.split('|');
  return { month, blogType, stat, rate: statRate(stat) };
}).sort((a, b) => a.month.localeCompare(b.month) || a.blogType.localeCompare(b.blogType, 'ko'));

const branchAccountRows = [...byBranchAccountType.entries()].map(([key, stat]) => {
  const [branch, blogType, account] = key.split('|');
  return {
    branch,
    specialty: inferSpecialty(branch),
    blogType,
    account,
    stat,
    rate: statRate(stat),
  };
}).sort((a, b) => {
  const firstA = byBranch.get(a.branch)?.first || '';
  const firstB = byBranch.get(b.branch)?.first || '';
  return firstA.localeCompare(firstB) || a.branch.localeCompare(b.branch, 'ko') || b.stat.count - a.stat.count;
});

const minCount = 5;
const generalRankRows = branchRows
  .filter((row) => row.general.count > 0)
  .sort((a, b) => b.generalRate - a.generalRate || b.general.count - a.general.count || a.branch.localeCompare(b.branch, 'ko'));
const optimalRankRows = branchRows
  .filter((row) => row.optimal.count > 0)
  .sort((a, b) => b.optimalRate - a.optimalRate || b.optimal.count - a.optimal.count || a.branch.localeCompare(b.branch, 'ko'));
const unknownSpecialty = branchRows.filter((row) => row.specialty === '확인필요');

function specialtyGroup(specialty) {
  if (specialty === '치과') return '치과';
  if (specialty === '피부과') return '피부과';
  return '기타';
}

const months = [...new Set(analysisRows.map((row) => row.published_at.slice(0, 7)))].sort();
const monthlyBranchData = branchRows
  .map((row) => ({
    branch: row.branch,
    specialty: row.specialty,
    group: specialtyGroup(row.specialty),
    operationGroup: row.operationGroup,
    first: row.first,
    last: row.last,
    months: Object.fromEntries(months.map((month) => [
      month,
      Object.fromEntries(['종합', '일반 블로그', '최적 블로그'].map((type) => {
        const stat = byBranchMonthType.get(`${row.branch}|${month}|${type}`) || emptyStat();
        return [type, {
          count: stat.count,
          exposed: stat.exposed,
          noExposure: stat.noExposure,
          outsideTop10: stat.outsideTop10,
          rate: statRate(stat),
          status: statusFor(statRate(stat), stat.count)[1],
        }];
      })),
    ])),
  }))
  .sort((a, b) => a.first.localeCompare(b.first) || a.branch.localeCompare(b.branch, 'ko'));

const normalizedBranchCsvRows = [[
  'specialty',
  'operation_group',
  'branch',
  'first_published',
  'last_published',
  'total_count',
  'total_exposed',
  'total_exposure_rate',
  'general_count',
  'general_exposed',
  'general_exposure_rate',
  'general_no_exposure',
  'general_outside_top10',
  'optimal_count',
  'optimal_exposed',
  'optimal_exposure_rate',
  'optimal_no_exposure',
  'optimal_outside_top10',
  'variants',
]];

for (const row of branchRows) {
  normalizedBranchCsvRows.push([
    row.specialty,
    row.operationGroup,
    row.branch,
    row.first,
    row.last,
    row.stat.count,
    row.stat.exposed,
    fmtPct(row.rate),
    row.general.count,
    row.general.exposed,
    fmtPct(row.generalRate),
    row.general.noExposure,
    row.general.outsideTop10,
    row.optimal.count,
    row.optimal.exposed,
    fmtPct(row.optimalRate),
    row.optimal.noExposure,
    row.optimal.outsideTop10,
    topVariants(row.stat, 8),
  ]);
}

const accountCsvRows = [[
  'specialty',
  'branch',
  'blog_type',
  'blog_id',
  'first_published',
  'last_published',
  'published_count',
  'exposed_count',
  'exposure_rate',
  'no_exposure',
  'outside_top10',
]];

for (const row of branchAccountRows) {
  accountCsvRows.push([
    row.specialty,
    row.branch,
    row.blogType,
    row.account,
    row.stat.first,
    row.stat.last,
    row.stat.count,
    row.stat.exposed,
    fmtPct(row.rate),
    row.stat.noExposure,
    row.stat.outsideTop10,
  ]);
}

const detailCsvRows = [[
  'specialty',
  'operation_group',
  'normalized_branch',
  'blog_type',
  'reference_matched',
  ...headers,
]];

for (const row of normalizedRows) {
  detailCsvRows.push([
    row.specialty,
    row.operation_group,
    row.normalized_branch,
    row.blog_type,
    row.reference_matched ? 'Y' : 'N',
    ...headers.map((header) => row[header] ?? ''),
  ]);
}

fs.writeFileSync(path.join(projectDir, 'normalized_branch_summary.csv'), toCSV(normalizedBranchCsvRows));
fs.writeFileSync(path.join(projectDir, 'normalized_account_summary.csv'), toCSV(accountCsvRows));
fs.writeFileSync(path.join(projectDir, 'normalized_detail.csv'), toCSV(detailCsvRows));
fs.writeFileSync(path.join(projectDir, 'branch_reference_mapping.csv'), toCSV([
  ['specialty', 'operation_group', 'branch'],
  ...referenceBranches.map(([branch, specialty, operationGroup]) => [specialty, operationGroup, branch]),
]));

const unmatchedMap = new Map();
for (const row of unmatchedRows) updateMap(unmatchedMap, row.normalized_branch, row);
const unmatchedCsvRows = [[
  'specialty_guess',
  'analysis_target_branch',
  'first_published',
  'last_published',
  'published_count',
  'exposed_count',
  'exposure_rate',
  'variants',
]];
for (const [branch, stat] of [...unmatchedMap.entries()].sort((a, b) => b[1].count - a[1].count || a[0].localeCompare(b[0], 'ko'))) {
  unmatchedCsvRows.push([
    inferSpecialty(branch),
    branch,
    stat.first,
    stat.last,
    stat.count,
    stat.exposed,
    fmtPct(statRate(stat)),
    topVariants(stat, 8),
  ]);
}
fs.writeFileSync(path.join(projectDir, 'unmatched_reference_audit.csv'), toCSV(unmatchedCsvRows));

function metricCard(label, value, note, tone = '') {
  return `<div class="metric ${tone}"><div class="metric-label">${label}</div><div class="metric-value">${value}</div><div class="metric-note">${note}</div></div>`;
}

function exposureCell(rate, count, exposed) {
  if (!count) return '<span class="muted-text">-</span>';
  const cls = statusFor(rate, count)[1];
  return `<div class="rate ${cls}"><strong>${fmtPct(rate)}</strong><span>${fmtInt(exposed)}/${fmtInt(count)}</span></div>`;
}

function statusBadge(rate, count) {
  const [label, cls] = statusFor(rate, count);
  return `<span class="badge ${cls}">${label}</span>`;
}

function renderBranchTable(rowsForTable) {
  return `<div class="table-wrap"><table>
    <thead><tr>
      <th>상태</th><th>과목</th><th>구분</th><th>지점명</th><th>시작일</th><th>최근 발행일</th>
      <th>일반 블로그 노출율</th><th>최적 블로그 노출율</th><th>전체 노출율</th><th>원본 지점명</th>
    </tr></thead>
    <tbody>${rowsForTable.map((row) => {
      const comparedRates = [
        row.general.count >= minCount ? row.generalRate : null,
        row.optimal.count >= minCount ? row.optimalRate : null,
      ].filter((value) => value != null);
      const statusRate = comparedRates.length ? Math.min(...comparedRates) : row.rate;
      return `<tr class="${statusFor(statusRate, row.stat.count)[1]}-row">
        <td>${statusBadge(statusRate, row.stat.count)}</td>
        <td>${escapeHTML(row.specialty)}</td>
        <td>${escapeHTML(row.operationGroup)}</td>
        <td class="name-cell">${escapeHTML(row.branch)}</td>
        <td>${row.first}</td>
        <td>${row.last}</td>
        <td>${exposureCell(row.generalRate, row.general.count, row.general.exposed)}</td>
        <td>${exposureCell(row.optimalRate, row.optimal.count, row.optimal.exposed)}</td>
        <td>${exposureCell(row.rate, row.stat.count, row.stat.exposed)}</td>
        <td class="variants">${escapeHTML(topVariants(row.stat, 5))}</td>
      </tr>`;
    }).join('')}</tbody>
  </table></div>`;
}

function renderExposureRankCards(title, rowsForList, type) {
  return `<section class="card"><div class="card-head"><h3>${title}</h3><span>노출율 높은 순 · 동률 시 발행건 많은 순</span></div>
    <div class="compact-list all-branch-cards">${rowsForList.map((row, index) => {
      const stat = type === 'general' ? row.general : row.optimal;
      const rate = type === 'general' ? row.generalRate : row.optimalRate;
      return `<div class="compact-item ${statusFor(rate, stat.count)[1]}-row">
        <div><strong>${index + 1}. ${escapeHTML(row.branch)}</strong><span>${escapeHTML(row.specialty)} · ${escapeHTML(row.operationGroup)}</span></div>
        <div>${exposureCell(rate, stat.count, stat.exposed)}</div>
      </div>`;
    }).join('')}</div>
  </section>`;
}

function renderColorLegend() {
  return `<section class="card pad legend-card">
    <h3>색상 기준</h3>
    <div class="legend-list">
      <span class="badge ok">양호</span><b>70% 이상</b>
      <span class="badge watch">관찰</span><b>55% 이상 ~ 70% 미만</b>
      <span class="badge warn">주의</span><b>40% 이상 ~ 55% 미만</b>
      <span class="badge danger">위험</span><b>40% 미만</b>
    </div>
  </section>`;
}

function renderOverallBarChart() {
  const rowsForChart = [...branchRows]
    .sort((a, b) => b.rate - a.rate || b.stat.count - a.stat.count || a.branch.localeCompare(b.branch, 'ko'));

  return `<section class="card">
    <div class="card-head"><h3>지점별 전체 노출율</h3><span>노출율 높은 순 · 전체 지점</span></div>
    <div class="bars">${rowsForChart.map((row) => {
      const cls = statusFor(row.rate, row.stat.count)[1];
      return `<div class="bar-row">
        <div>${escapeHTML(row.branch)}</div>
        <div class="bar-track"><div class="bar-fill ${cls}" style="width:${Math.max(1, Math.round((row.rate || 0) * 100))}%"></div></div>
        <div>${fmtPct(row.rate)}</div>
      </div>`;
    }).join('')}</div>
  </section>`;
}

function renderSpecialtyTable() {
  return `<div class="table-wrap"><table>
    <thead><tr><th>과목</th><th>지점수</th><th>발행건</th><th>노출건</th><th>노출율</th><th>미노출</th><th>10위밖</th></tr></thead>
    <tbody>${specialtyRows.map((row) => `<tr>
      <td class="name-cell">${escapeHTML(row.specialty)}</td>
      <td>${fmtInt(row.branches)}</td>
      <td>${fmtInt(row.stat.count)}</td>
      <td>${fmtInt(row.stat.exposed)}</td>
      <td>${exposureCell(row.rate, row.stat.count, row.stat.exposed)}</td>
      <td>${fmtInt(row.stat.noExposure)}</td>
      <td>${fmtInt(row.stat.outsideTop10)}</td>
    </tr>`).join('')}</tbody>
  </table></div>`;
}

function renderMonthTable() {
  const months = [...new Set(monthRows.map((row) => row.month))].sort();
  const types = ['종합', '일반 블로그', '최적 블로그'];
  return `<div class="table-wrap"><table>
    <thead><tr><th>구분</th>${months.map((month) => `<th>${month}</th>`).join('')}</tr></thead>
    <tbody>${types.map((type) => `<tr>
      <td class="name-cell">${type}</td>
      ${months.map((month) => {
        const row = monthRows.find((item) => item.month === month && item.blogType === type);
        if (!row) return '<td><span class="muted-text">-</span></td>';
        return `<td><div class="month-summary-cell">${exposureCell(row.rate, row.stat.count, row.stat.exposed)}<span>발행 ${fmtInt(row.stat.count)}건</span></div></td>`;
      }).join('')}
    </tr>`).join('')}</tbody>
  </table></div>`;
}

function renderMonthlyTrendChart() {
  const types = [
    ['종합', '#2563eb'],
    ['일반 블로그', '#16a34a'],
    ['최적 블로그', '#9333ea'],
  ];
  const width = 1180;
  const height = 420;
  const pad = { top: 42, right: 54, bottom: 58, left: 62 };
  const plotWidth = width - pad.left - pad.right;
  const plotHeight = height - pad.top - pad.bottom;
  const x = (index) => pad.left + (months.length <= 1 ? plotWidth / 2 : (plotWidth * index) / (months.length - 1));
  const y = (rate) => pad.top + plotHeight - ((rate || 0) * plotHeight);
  const yTicks = [0, 0.25, 0.5, 0.75, 1];

  return `<section class="card">
    <div class="card-head"><h3>월별 노출율 추이</h3><span>가로축: 월 · 세로축: 노출율</span></div>
    <div class="trend-chart">
      <svg viewBox="0 0 ${width} ${height}" role="img" aria-label="월별 노출율 추이 그래프">
        ${yTicks.map((tick) => `
          <line x1="${pad.left}" y1="${y(tick)}" x2="${width - pad.right}" y2="${y(tick)}" stroke="#dbe4f0" stroke-width="1" />
          <text x="${pad.left - 12}" y="${y(tick) + 5}" text-anchor="end">${fmtPct(tick)}</text>
        `).join('')}
        ${months.map((month, index) => `
          <text x="${x(index)}" y="${height - 20}" text-anchor="middle">${month.replace('2026-', '')}월</text>
        `).join('')}
        ${types.map(([type, color]) => {
          const points = months.map((month, index) => {
            const row = monthRows.find((item) => item.month === month && item.blogType === type);
            return { month, index, row, rate: row?.rate ?? 0 };
          });
          const path = points.map((point, index) => `${index === 0 ? 'M' : 'L'} ${x(point.index)} ${y(point.rate)}`).join(' ');
          return `
            <path class="trend-series" data-trend-type="${type}" d="${path}" fill="none" stroke="${color}" stroke-width="4" stroke-linecap="round" stroke-linejoin="round" />
            ${points.map((point) => `
              <circle class="trend-point" data-trend-type="${type}" data-month="${point.month}" data-rate="${fmtPct(point.row?.rate)}" data-exposed="${fmtInt(point.row?.stat.exposed || 0)}" data-count="${fmtInt(point.row?.stat.count || 0)}" cx="${x(point.index)}" cy="${y(point.rate)}" r="7" fill="${color}"></circle>
            `).join('')}
          `;
        }).join('')}
      </svg>
      <div class="chart-legend">
        ${types.map(([type, color]) => `<span data-trend-type="${type}"><i style="background:${color}"></i>${type}</span>`).join('')}
      </div>
      <div class="trend-tooltip" id="trendTooltip"></div>
    </div>
  </section>`;
}

function renderMonthlyBranchDiagnosis() {
  return `<section class="card">
    <div class="card-head"><h3>지점별 월간 노출율</h3><span>과목군과 블로그 유형을 선택해서 확인</span></div>
    <div class="monthly-panel">
      <div class="monthly-controls">
        <div class="segmented" aria-label="과목군 선택">
          ${['전체', '치과', '피부과', '기타'].map((group) => `<button class="seg-btn ${group === '전체' ? 'active' : ''}" data-month-group="${group}">${group}</button>`).join('')}
        </div>
        <div class="segmented" aria-label="블로그 유형 선택">
          ${['종합', '일반 블로그', '최적 블로그'].map((type) => `<button class="seg-btn ${type === '종합' ? 'active' : ''}" data-month-type="${type}">${type}</button>`).join('')}
        </div>
      </div>
      <div id="monthlyBranchHeatmap"></div>
    </div>
  </section>`;
}

function renderAccountTable(type) {
  const rowsForTable = branchAccountRows.filter((row) => row.blogType === type);
  return `<div class="table-wrap"><table>
    <thead><tr><th>과목</th><th>지점명</th><th>계정 ID</th><th>시작일</th><th>최근 발행일</th><th>발행건</th><th>노출건</th><th>노출율</th><th>미노출</th><th>10위밖</th></tr></thead>
    <tbody>${rowsForTable.map((row) => `<tr class="${statusFor(row.rate, row.stat.count)[1]}-row">
      <td>${escapeHTML(row.specialty)}</td>
      <td class="name-cell">${escapeHTML(row.branch)}</td>
      <td><code>${escapeHTML(row.account)}</code></td>
      <td>${row.stat.first}</td>
      <td>${row.stat.last}</td>
      <td>${fmtInt(row.stat.count)}</td>
      <td>${fmtInt(row.stat.exposed)}</td>
      <td>${exposureCell(row.rate, row.stat.count, row.stat.exposed)}</td>
      <td>${fmtInt(row.stat.noExposure)}</td>
      <td>${fmtInt(row.stat.outsideTop10)}</td>
    </tr>`).join('')}</tbody>
  </table></div>`;
}

function renderDetailTable() {
  return `<div class="table-wrap"><table>
    <thead><tr><th>과목</th><th>구분</th><th>분석 대상 지점</th><th>유형</th><th>발행일</th><th>계정 ID</th><th>키워드</th><th>순위</th><th>원본 지점명</th><th>URL</th></tr></thead>
    <tbody>${analysisRows
      .sort((a, b) => a.normalized_branch.localeCompare(b.normalized_branch, 'ko') || a.published_at.localeCompare(b.published_at))
      .map((row) => `<tr>
        <td>${escapeHTML(row.specialty)}</td>
        <td>${escapeHTML(row.operation_group)}</td>
        <td class="name-cell">${escapeHTML(row.normalized_branch)}</td>
        <td>${escapeHTML(row.blog_type)}</td>
        <td>${row.published_at}</td>
        <td><code>${escapeHTML(row.blog_id)}</code></td>
        <td class="variants">${escapeHTML(row.keyword)}</td>
        <td>${row.exposure_rank == null ? '-' : row.exposure_rank}</td>
        <td class="variants">${escapeHTML(row.branch_name || row.target_branch)}</td>
        <td>${row.published_url ? `<a href="${escapeHTML(row.published_url)}">열기</a>` : '-'}</td>
      </tr>`).join('')}</tbody>
  </table></div>`;
}

function renderUnmatchedSummary() {
  const rowsForTable = [...unmatchedMap.entries()]
    .sort((a, b) => b[1].count - a[1].count || a[0].localeCompare(b[0], 'ko'))
    .slice(0, 12);

  return `<div class="table-wrap"><table>
    <thead><tr><th>추정 과목</th><th>분석 대상 지점</th><th>발행건</th><th>노출건</th><th>노출율</th><th>원본 지점명</th></tr></thead>
    <tbody>${rowsForTable.map(([branch, stat]) => `<tr>
      <td>${escapeHTML(inferSpecialty(branch))}</td>
      <td class="name-cell">${escapeHTML(branch)}</td>
      <td>${fmtInt(stat.count)}</td>
      <td>${fmtInt(stat.exposed)}</td>
      <td>${exposureCell(statRate(stat), stat.count, stat.exposed)}</td>
      <td class="variants">${escapeHTML(topVariants(stat, 5))}</td>
    </tr>`).join('')}</tbody>
  </table></div>`;
}

const general = byType.get('일반 블로그') || emptyStat();
const optimal = byType.get('최적 블로그') || emptyStat();
const unknownNote = unknownSpecialty.length
  ? `${unknownSpecialty.length}개 지점명이 과목 확인 필요입니다. 모두 소량 데이터인지 확인해 주세요.`
  : '발행 3건 이상 지점 기준으로 과목 확인 필요 항목은 없습니다.';

const html = `<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>전체 지점 블로그 노출율 진단 보고서</title>
  <style>
    :root {
      --bg: #f3f6fb;
      --card: #fff;
      --ink: #172033;
      --muted: #66758f;
      --line: #dbe4f0;
      --head: #f7f9fc;
      --blue: #2563eb;
      --green: #16a34a;
      --amber: #d97706;
      --orange: #ea580c;
      --red: #dc2626;
      --soft-green: #e8fff0;
      --soft-amber: #fff8dc;
      --soft-orange: #fff3e6;
      --soft-red: #fff0f2;
    }
    * { box-sizing: border-box; }
    body { margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: var(--bg); color: var(--ink); }
    .page { max-width: 1840px; margin: 0 auto; padding: 32px; }
    header { display: flex; justify-content: space-between; gap: 24px; align-items: flex-end; margin-bottom: 24px; }
    h1 { margin: 0 0 10px; font-size: 34px; letter-spacing: 0; }
    h2 { margin: 0; font-size: 28px; }
    h3 { margin: 0; font-size: 22px; }
    p { margin: 0; color: var(--muted); font-size: 16px; line-height: 1.55; }
    .pill-note { padding: 10px 14px; border: 1px solid var(--line); border-radius: 999px; background: #fff; color: var(--muted); font-weight: 700; white-space: nowrap; }
    .tabs { display: flex; flex-wrap: wrap; gap: 8px; margin: 18px 0 22px; }
    .tab-btn { border: 1px solid var(--line); background: #fff; color: var(--muted); font-weight: 800; padding: 12px 18px; border-radius: 10px; cursor: pointer; font-size: 16px; }
    .tab-btn.active { background: #213148; color: #fff; border-color: #213148; }
    .tab { display: none; }
    .tab.active { display: block; }
    .metrics { display: grid; grid-template-columns: repeat(6, minmax(160px, 1fr)); gap: 14px; margin-bottom: 16px; }
    .metric { background: var(--card); border: 1px solid var(--line); border-radius: 10px; padding: 18px; min-height: 120px; }
    .metric-label { color: var(--muted); font-weight: 800; font-size: 14px; }
    .metric-value { margin-top: 10px; font-size: 34px; line-height: 1; font-weight: 900; }
    .metric-note { margin-top: 10px; color: var(--muted); font-size: 14px; }
    .metric.green .metric-value { color: var(--green); }
    .metric.blue .metric-value { color: var(--blue); }
    .metric.red .metric-value { color: var(--red); }
    .grid-2 { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; }
    .card { background: var(--card); border: 1px solid var(--line); border-radius: 10px; margin-bottom: 18px; overflow: hidden; box-shadow: 0 12px 30px rgba(20, 36, 64, .04); }
    .card.pad { padding: 22px; }
    .card-head { display: flex; justify-content: space-between; align-items: center; gap: 16px; padding: 22px 24px; border-bottom: 1px solid var(--line); }
    .card-head span { color: var(--muted); font-weight: 700; font-size: 14px; }
    .table-wrap { overflow-x: auto; }
    table { width: 100%; border-collapse: collapse; min-width: 1120px; }
    th, td { padding: 15px 16px; border-bottom: 1px solid var(--line); text-align: center; vertical-align: middle; font-size: 16px; line-height: 1.45; }
    th { background: var(--head); color: #2f3c52; font-weight: 900; white-space: nowrap; }
    td { font-weight: 650; }
    .name-cell { font-weight: 900; }
    .variants { max-width: 420px; white-space: normal; word-break: keep-all; overflow-wrap: anywhere; color: var(--muted); font-size: 14px; font-weight: 600; }
    code { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; color: #39506f; font-size: 14px; }
    a { color: var(--blue); font-weight: 800; text-decoration: none; }
    .badge { display: inline-flex; align-items: center; justify-content: center; min-width: 54px; padding: 7px 11px; border-radius: 999px; font-weight: 900; font-size: 14px; }
    .badge.ok { background: #dcfce7; color: #15803d; }
    .badge.watch { background: #fef3c7; color: #a16207; }
    .badge.warn { background: #ffedd5; color: #c2410c; }
    .badge.danger { background: #fee2e2; color: #be123c; }
    .badge.muted { background: #e5e7eb; color: #64748b; }
    .rate { display: inline-flex; flex-direction: column; align-items: center; gap: 3px; min-width: 82px; }
    .rate strong { font-size: 17px; }
    .rate span { color: var(--muted); font-size: 13px; font-weight: 800; }
    .rate.ok strong { color: var(--green); }
    .rate.watch strong { color: var(--amber); }
    .rate.warn strong { color: var(--orange); }
    .rate.danger strong { color: #be123c; }
    .ok-row { background: #fff; }
    .watch-row { background: var(--soft-amber); color: #8a3c08; }
    .warn-row { background: var(--soft-orange); color: #9a3412; }
    .danger-row { background: var(--soft-red); color: #b20f3a; }
    .muted-text { color: var(--muted); }
    .compact-list { padding: 10px 18px 18px; }
    .compact-item { display: grid; grid-template-columns: 1fr auto; gap: 18px; align-items: center; padding: 14px 16px; border: 1px solid var(--line); border-radius: 8px; margin-top: 10px; }
    .compact-item strong { display: block; font-size: 17px; }
    .compact-item span { display: block; margin-top: 3px; color: var(--muted); font-size: 13px; font-weight: 800; }
    .all-branch-cards { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px; }
    .all-branch-cards .compact-item { margin-top: 0; min-height: 82px; }
    .legend-card { margin-top: 16px; }
    .legend-list { display: flex; flex-wrap: wrap; align-items: center; gap: 10px 14px; margin-top: 14px; color: var(--muted); }
    .legend-list b { margin-right: 18px; font-size: 14px; }
    .bars { padding: 18px 24px 24px; }
    .bar-row { display: grid; grid-template-columns: 190px 1fr 96px; gap: 16px; align-items: center; margin: 14px 0; font-weight: 900; }
    .bar-track { height: 18px; border-radius: 999px; background: #eaf0f8; overflow: hidden; }
    .bar-fill { height: 100%; border-radius: 999px; background: var(--blue); }
    .bar-fill.ok { background: var(--green); }
    .bar-fill.watch { background: var(--amber); }
    .bar-fill.warn { background: var(--orange); }
    .bar-fill.danger { background: var(--red); }
    .trend-chart { padding: 18px 24px 24px; }
    .trend-chart svg { width: 100%; height: auto; display: block; overflow: visible; }
    .trend-chart text { fill: var(--muted); font-size: 15px; font-weight: 800; }
    .trend-series, .trend-point, .chart-legend span { transition: opacity .15s ease, stroke-width .15s ease, transform .15s ease; }
    .trend-series.dim, .trend-point.dim, .chart-legend span.dim { opacity: .16; }
    .trend-series.active { stroke-width: 7; }
    .trend-point.active { transform-box: fill-box; transform-origin: center; transform: scale(1.3); }
    .chart-legend { display: flex; justify-content: center; flex-wrap: wrap; gap: 16px; margin-top: 10px; color: var(--muted); font-weight: 900; }
    .chart-legend span { display: inline-flex; align-items: center; gap: 8px; cursor: pointer; border: 1px solid var(--line); border-radius: 999px; padding: 7px 10px; background: #fff; }
    .chart-legend i { display: inline-block; width: 14px; height: 14px; border-radius: 4px; }
    .trend-tooltip { position: fixed; z-index: 40; pointer-events: none; opacity: 0; transform: translate(14px, 14px); background: #111827; color: #fff; border-radius: 10px; padding: 10px 12px; box-shadow: 0 16px 34px rgba(15, 23, 42, .26); min-width: 190px; font-weight: 800; line-height: 1.45; transition: opacity .12s ease; }
    .trend-tooltip strong { display: block; font-size: 14px; margin-bottom: 4px; }
    .trend-tooltip span { display: block; color: #dbeafe; font-size: 13px; }
    .month-summary-cell { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 6px; min-height: 74px; }
    .month-summary-cell > span { color: var(--muted); font-size: 13px; font-weight: 850; }
    .monthly-panel { padding: 18px 22px 24px; }
    .monthly-controls { display: flex; justify-content: space-between; flex-wrap: wrap; gap: 12px; margin-bottom: 16px; }
    .segmented { display: inline-flex; flex-wrap: wrap; gap: 6px; padding: 6px; background: #eef3fa; border: 1px solid var(--line); border-radius: 12px; }
    .seg-btn { border: 0; border-radius: 9px; padding: 10px 14px; background: transparent; color: var(--muted); font-weight: 900; font-size: 15px; cursor: pointer; }
    .seg-btn.active { background: #213148; color: #fff; box-shadow: 0 4px 12px rgba(31, 45, 66, .14); }
    .heatmap-table { min-width: 1160px; table-layout: fixed; }
    .heatmap-table th, .heatmap-table td { padding: 13px 12px; }
    .heatmap-table .branch-sticky { position: sticky; left: 0; z-index: 2; min-width: 230px; width: 230px; text-align: left; background: inherit; box-shadow: 1px 0 0 var(--line); }
    .heatmap-table th.branch-sticky { z-index: 3; background: var(--head); }
    .heatmap-table .specialty-col { width: 110px; }
    .month-cell { min-height: 62px; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 4px; border-radius: 8px; }
    .month-cell strong { font-size: 17px; }
    .month-cell span { color: var(--muted); font-size: 13px; font-weight: 850; }
    .month-cell.empty { color: #94a3b8; background: #f8fafc; }
    .month-cell.ok { background: #e8fff0; color: #15803d; }
    .month-cell.watch { background: #fff8dc; color: #a16207; }
    .month-cell.warn { background: #fff3e6; color: #c2410c; }
    .month-cell.danger { background: #fff0f2; color: #be123c; }
    .defs { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 14px; }
    .defs span { background: #fff; border: 1px solid var(--line); border-radius: 999px; padding: 9px 12px; color: var(--muted); font-weight: 800; font-size: 14px; }
    @media (max-width: 1100px) {
      .page { padding: 20px; }
      header { display: block; }
      .pill-note { display: inline-flex; margin-top: 12px; }
      .metrics { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .grid-2 { grid-template-columns: 1fr; }
      .all-branch-cards { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <main class="page">
    <header>
      <div>
        <h1>전체 지점 블로그 노출율 진단 보고서</h1>
      <p>유앤아이 계열과 bioadd lab 7개 지점을 제외한 2026년 1월~6월 데이터입니다. 지점명은 원고번호와 배포표기를 제거한 뒤, 6월 운영 지점 기준표와 매칭된 데이터만 메인 진단에 사용했습니다.</p>
        <div class="defs">
          <span>일반 블로그: 브랜드 블로그 발행 데이터</span>
          <span>최적 블로그: 최적 블로그 발행 데이터</span>
          <span>노출: 순위 1~10위</span>
          <span>미노출: 빈값 또는 0</span>
          <span>10위밖: 11위 이상</span>
        </div>
      </div>
      <div class="pill-note">기준 기간: 2026-01-01 ~ 2026-06-30</div>
    </header>

    <nav class="tabs">
      <button class="tab-btn active" data-tab="summary">요약</button>
      <button class="tab-btn" data-tab="branch">상세보기</button>
      <button class="tab-btn" data-tab="specialty">과목별</button>
      <button class="tab-btn" data-tab="monthly">월별 변화</button>
      <button class="tab-btn" data-tab="account">계정/ID</button>
      <button class="tab-btn" data-tab="detail">상세</button>
    </nav>

    <section id="summary" class="tab active">
      <div class="metrics">
        ${metricCard('발행건', fmtInt(overall.count), '기준표 매칭 데이터')}
        ${metricCard('분석 대상 지점', fmtInt(branchRows.length), '운영 지점 기준표 매칭')}
        ${metricCard('일반 블로그 노출율', fmtPct(statRate(general)), `${fmtInt(general.exposed)}/${fmtInt(general.count)}`, 'blue')}
        ${metricCard('최적 블로그 노출율', fmtPct(statRate(optimal)), `${fmtInt(optimal.exposed)}/${fmtInt(optimal.count)}`, 'green')}
        ${metricCard('전체 노출율', fmtPct(statRate(overall)), `${fmtInt(overall.exposed)}/${fmtInt(overall.count)}`)}
        ${metricCard('미노출+10위밖', fmtInt(overall.noExposure + overall.outsideTop10), `미노출 ${fmtInt(overall.noExposure)} · 10위밖 ${fmtInt(overall.outsideTop10)}`, 'red')}
      </div>
      <div class="grid-2">
        ${renderExposureRankCards('일반 블로그 전체 지점', generalRankRows, 'general')}
        ${renderExposureRankCards('최적 블로그 전체 지점', optimalRankRows, 'optimal')}
      </div>
      ${renderOverallBarChart()}
      ${renderColorLegend()}
    </section>

    <section id="branch" class="tab">
      <section class="card">
        <div class="card-head"><h3>지점별 일반/최적 블로그 노출율</h3><span>지점 시작일 기준</span></div>
        ${renderBranchTable(branchRows)}
      </section>
    </section>

    <section id="specialty" class="tab">
      <section class="card">
        <div class="card-head"><h3>과목별 노출율</h3><span>분석 대상 지점 기준</span></div>
        ${renderSpecialtyTable()}
      </section>
      <section class="card pad">
        <h3>과목 확인 메모</h3>
        <p style="margin-top:10px">${escapeHTML(unknownNote)}</p>
      </section>
    </section>

    <section id="monthly" class="tab">
      ${renderMonthlyTrendChart()}
      ${renderMonthlyBranchDiagnosis()}
      <section class="card">
        <div class="card-head"><h3>월별 집계표</h3><span>월별 발행건과 노출건 기준</span></div>
        ${renderMonthTable()}
      </section>
    </section>

    <section id="account" class="tab">
      <section class="card">
        <div class="card-head"><h3>일반 블로그 지점 x 계정 ID</h3><span>지점명과 계정 ID 기준</span></div>
        ${renderAccountTable('일반 블로그')}
      </section>
      <section class="card">
        <div class="card-head"><h3>최적 블로그 지점 x 계정 ID</h3><span>지점명과 계정 ID 기준</span></div>
        ${renderAccountTable('최적 블로그')}
      </section>
    </section>

    <section id="detail" class="tab">
      <section class="card">
        <div class="card-head"><h3>상세 데이터</h3><span>기준표 매칭 데이터</span></div>
        ${renderDetailTable()}
      </section>
    </section>
  </main>
  <script>
    const MONTHS = ${JSON.stringify(months)};
    const MONTHLY_BRANCH_DATA = ${JSON.stringify(monthlyBranchData)};
    let selectedMonthGroup = '전체';
    let selectedMonthType = '종합';

    function escapeClientHTML(value) {
      return String(value == null ? '' : value)
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#39;');
    }

    function formatClientPct(value) {
      return value == null ? '-' : (value * 100).toFixed(1) + '%';
    }

    function statusLabel(cls) {
      if (cls === 'ok') return '양호';
      if (cls === 'watch') return '관찰';
      if (cls === 'warn') return '주의';
      if (cls === 'danger') return '위험';
      return '없음';
    }

    function renderMonthlyBranchHeatmap() {
      const mount = document.getElementById('monthlyBranchHeatmap');
      if (!mount) return;
      const rows = MONTHLY_BRANCH_DATA.filter((row) => selectedMonthGroup === '전체' || row.group === selectedMonthGroup);
      const html = '<div class="table-wrap"><table class="heatmap-table">'
        + '<thead><tr><th class="branch-sticky">분석 대상 지점</th><th class="specialty-col">과목</th>'
        + MONTHS.map((month) => '<th>' + month.replace('2026-', '') + '월</th>').join('')
        + '</tr></thead><tbody>'
        + rows.map((row) => {
          return '<tr>'
            + '<td class="branch-sticky name-cell">' + escapeClientHTML(row.branch) + '</td>'
            + '<td>' + escapeClientHTML(row.specialty) + '</td>'
            + MONTHS.map((month) => {
              const stat = row.months[month][selectedMonthType];
              if (!stat.count) {
                return '<td><div class="month-cell empty"><strong>-</strong><span>0건</span></div></td>';
              }
              const title = selectedMonthType + ' ' + month + ' / ' + row.branch
                + ' / 노출 ' + stat.exposed + '건'
                + ' / 발행 ' + stat.count + '건'
                + ' / 미노출 ' + stat.noExposure + '건'
                + ' / 10위밖 ' + stat.outsideTop10 + '건';
              return '<td><div class="month-cell ' + stat.status + '" title="' + escapeClientHTML(title) + '">'
                + '<strong>' + formatClientPct(stat.rate) + '</strong>'
                + '<span>' + stat.exposed + '/' + stat.count + ' · ' + statusLabel(stat.status) + '</span>'
                + '</div></td>';
            }).join('')
            + '</tr>';
        }).join('')
        + '</tbody></table></div>';
      mount.innerHTML = html;
    }

    document.querySelectorAll('[data-month-group]').forEach((button) => {
      button.addEventListener('click', () => {
        selectedMonthGroup = button.dataset.monthGroup;
        document.querySelectorAll('[data-month-group]').forEach((item) => item.classList.remove('active'));
        button.classList.add('active');
        renderMonthlyBranchHeatmap();
      });
    });

    document.querySelectorAll('[data-month-type]').forEach((button) => {
      button.addEventListener('click', () => {
        selectedMonthType = button.dataset.monthType;
        document.querySelectorAll('[data-month-type]').forEach((item) => item.classList.remove('active'));
        button.classList.add('active');
        renderMonthlyBranchHeatmap();
      });
    });

    function highlightTrend(type) {
      document.querySelectorAll('[data-trend-type]').forEach((item) => {
        const same = item.dataset.trendType === type;
        item.classList.toggle('active', same);
        item.classList.toggle('dim', !same);
      });
    }

    function clearTrendHighlight() {
      document.querySelectorAll('[data-trend-type]').forEach((item) => {
        item.classList.remove('active', 'dim');
      });
      const tooltip = document.getElementById('trendTooltip');
      if (tooltip) tooltip.style.opacity = '0';
    }

    function showTrendTooltip(event, point) {
      const tooltip = document.getElementById('trendTooltip');
      if (!tooltip) return;
      tooltip.innerHTML = '<strong>' + point.dataset.trendType + ' · ' + point.dataset.month + '</strong>'
        + '<span>노출율 ' + point.dataset.rate + '</span>'
        + '<span>노출 ' + point.dataset.exposed + '건 / 발행 ' + point.dataset.count + '건</span>';
      tooltip.style.left = event.clientX + 'px';
      tooltip.style.top = event.clientY + 'px';
      tooltip.style.opacity = '1';
    }

    document.querySelectorAll('[data-trend-type]').forEach((item) => {
      item.addEventListener('mouseenter', () => highlightTrend(item.dataset.trendType));
      item.addEventListener('mouseleave', clearTrendHighlight);
    });

    document.querySelectorAll('.trend-point').forEach((point) => {
      point.addEventListener('mouseenter', (event) => {
        highlightTrend(point.dataset.trendType);
        showTrendTooltip(event, point);
      });
      point.addEventListener('mousemove', (event) => showTrendTooltip(event, point));
      point.addEventListener('mouseleave', clearTrendHighlight);
    });

    document.querySelectorAll('.tab-btn').forEach((button) => {
      button.addEventListener('click', () => {
        document.querySelectorAll('.tab-btn').forEach((item) => item.classList.remove('active'));
        document.querySelectorAll('.tab').forEach((item) => item.classList.remove('active'));
        button.classList.add('active');
        document.getElementById(button.dataset.tab).classList.add('active');
      });
    });

    renderMonthlyBranchHeatmap();
  </script>
</body>
</html>`;

fs.writeFileSync(path.join(projectDir, '(2026.06)all_branches_report.html'), html);

console.log(JSON.stringify({
  sourceRows: normalizedRows.length,
  analysisRows: analysisRows.length,
  branches: branchRows.length,
  general: { count: general.count, exposed: general.exposed, rate: fmtPct(statRate(general)) },
  optimal: { count: optimal.count, exposed: optimal.exposed, rate: fmtPct(statRate(optimal)) },
  unknownSpecialty: unknownSpecialty.length,
  unmatchedRows: unmatchedRows.length,
}, null, 2));

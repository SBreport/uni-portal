import fs from 'node:fs';
import path from 'node:path';

const projectDir = path.dirname(new URL(import.meta.url).pathname);
const detailPath = path.join(projectDir, 'normalized_detail.csv');
const outputHtml = '(2026.06)all_branches_june_report.html';

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

function fmtPct(value) {
  return value == null ? '-' : `${(value * 100).toFixed(1)}%`;
}

function pct(numerator, denominator) {
  return denominator ? numerator / denominator : null;
}

function emptyStat() {
  return {
    count: 0,
    exposed: 0,
    noExposure: 0,
    outsideTop10: 0,
    first: '',
    last: '',
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
  if (row.blog_id) stat.accounts.set(row.blog_id, (stat.accounts.get(row.blog_id) || 0) + 1);
}

function updateMap(map, key, row) {
  const stat = map.get(key) || emptyStat();
  addStat(stat, row);
  map.set(key, stat);
  return stat;
}

function statRate(stat) {
  return pct(stat.exposed, stat.count);
}

function statusFor(rate, count = 0) {
  if (!count || rate == null) return ['없음', 'muted'];
  if (rate < 0.4) return ['위험', 'danger'];
  if (rate < 0.55) return ['주의', 'warn'];
  if (rate < 0.7) return ['관찰', 'watch'];
  return ['양호', 'ok'];
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

function accountSummary(stat) {
  return [...stat.accounts.entries()]
    .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
    .slice(0, 3)
    .map(([account, count]) => `${account} ${count}건`)
    .join(' / ');
}

const rawRows = parseCSV(fs.readFileSync(detailPath, 'utf8'));
const headers = rawRows.shift();
const idx = Object.fromEntries(headers.map((name, index) => [name, index]));

const rows = rawRows.map((raw) => ({
  specialty: raw[idx.specialty],
  operation_group: raw[idx.operation_group],
  normalized_branch: raw[idx.normalized_branch],
  blog_type: raw[idx.blog_type],
  reference_matched: raw[idx.reference_matched],
  target_branch: raw[idx.target_branch],
  analysis_group: raw[idx.analysis_group],
  published_at: raw[idx.published_at],
  branch_name: raw[idx.branch_name],
  project_branch: raw[idx.project_branch],
  keyword: raw[idx.keyword],
  exposure_rank: raw[idx.exposure_rank] === '' ? null : Number(raw[idx.exposure_rank]),
  top10_success: Number(raw[idx.top10_success] || 0),
  no_exposure: Number(raw[idx.no_exposure] || 0),
  outside_top10: Number(raw[idx.outside_top10] || 0),
  blog_id: raw[idx.blog_id],
  title: raw[idx.title],
  published_url: raw[idx.published_url],
}));

const juneRows = rows.filter((row) => row.reference_matched === 'Y' && row.published_at.startsWith('2026-06'));

const overall = emptyStat();
const byType = new Map();
const byBranch = new Map();
const byBranchType = new Map();
const bySpecialty = new Map();

for (const row of juneRows) {
  addStat(overall, row);
  updateMap(byType, row.blog_type, row);
  updateMap(byBranch, row.normalized_branch, row);
  updateMap(byBranchType, `${row.normalized_branch}|${row.blog_type}`, row);
  updateMap(bySpecialty, row.specialty, row);
}

const branchRows = [...byBranch.entries()].map(([branch, stat]) => {
  const general = byBranchType.get(`${branch}|일반 블로그`) || emptyStat();
  const optimal = byBranchType.get(`${branch}|최적 블로그`) || emptyStat();
  const sample = juneRows.find((row) => row.normalized_branch === branch);
  return {
    branch,
    specialty: sample?.specialty || '',
    operationGroup: sample?.operation_group || '',
    stat,
    general,
    optimal,
    rate: statRate(stat),
    generalRate: statRate(general),
    optimalRate: statRate(optimal),
  };
}).sort((a, b) => (a.rate ?? 0) - (b.rate ?? 0) || b.stat.count - a.stat.count || a.branch.localeCompare(b.branch, 'ko'));

const specialtyRows = [...bySpecialty.entries()].map(([specialty, stat]) => ({
  specialty,
  stat,
  rate: statRate(stat),
  branches: branchRows.filter((row) => row.specialty === specialty).length,
})).sort((a, b) => (a.rate ?? 0) - (b.rate ?? 0) || b.stat.count - a.stat.count);

const general = byType.get('일반 블로그') || emptyStat();
const optimal = byType.get('최적 블로그') || emptyStat();

fs.writeFileSync(path.join(projectDir, 'june_branch_summary.csv'), toCSV([
  ['specialty', 'operation_group', 'branch', 'published_count', 'exposed_count', 'exposure_rate', 'no_exposure', 'outside_top10', 'general_count', 'general_exposure_rate', 'optimal_count', 'optimal_exposure_rate', 'accounts'],
  ...branchRows.map((row) => [
    row.specialty,
    row.operationGroup,
    row.branch,
    row.stat.count,
    row.stat.exposed,
    fmtPct(row.rate),
    row.stat.noExposure,
    row.stat.outsideTop10,
    row.general.count,
    fmtPct(row.generalRate),
    row.optimal.count,
    fmtPct(row.optimalRate),
    accountSummary(row.stat),
  ]),
]));

fs.writeFileSync(path.join(projectDir, 'june_detail.csv'), toCSV([
  ['specialty', 'operation_group', 'branch', 'blog_type', 'published_at', 'blog_id', 'keyword', 'exposure_rank', 'top10_success', 'published_url'],
  ...juneRows.map((row) => [
    row.specialty,
    row.operation_group,
    row.normalized_branch,
    row.blog_type,
    row.published_at,
    row.blog_id,
    row.keyword,
    row.exposure_rank ?? '',
    row.top10_success,
    row.published_url,
  ]),
]));

function metricCard(label, value, note, tone = '') {
  return `<article class="metric ${tone}"><div class="label">${label}</div><div class="value">${value}</div><div class="sub">${note}</div></article>`;
}

function renderBranchTable() {
  return `<div class="table-wrap"><table>
    <thead><tr>
      <th>상태</th><th>과목</th><th>지점</th><th>발행건</th><th>노출건</th><th>종합 노출율</th>
      <th>일반 블로그</th><th>최적 블로그</th><th>미노출</th><th>10위밖</th><th>주요 계정</th>
    </tr></thead>
    <tbody>${branchRows.map((row) => `<tr class="${statusFor(row.rate, row.stat.count)[1]}-row">
      <td>${statusBadge(row.rate, row.stat.count)}</td>
      <td>${escapeHTML(row.specialty)}</td>
      <td class="name">${escapeHTML(row.branch)}</td>
      <td>${fmtInt(row.stat.count)}</td>
      <td>${fmtInt(row.stat.exposed)}</td>
      <td>${exposureCell(row.rate, row.stat.count, row.stat.exposed)}</td>
      <td>${exposureCell(row.generalRate, row.general.count, row.general.exposed)}</td>
      <td>${exposureCell(row.optimalRate, row.optimal.count, row.optimal.exposed)}</td>
      <td>${fmtInt(row.stat.noExposure)}</td>
      <td>${fmtInt(row.stat.outsideTop10)}</td>
      <td class="memo">${escapeHTML(accountSummary(row.stat))}</td>
    </tr>`).join('')}</tbody>
  </table></div>`;
}

function renderRiskSummary() {
  const rows = branchRows.filter((row) => row.stat.count >= 5).slice(0, 6);
  return `<div class="risk-grid">${rows.map((row) => {
    const cls = statusFor(row.rate, row.stat.count)[1];
    return `<article class="risk-card ${cls}-row">
      <div>
        <strong>${escapeHTML(row.branch)}</strong>
        <span>${escapeHTML(row.specialty)} · 발행 ${fmtInt(row.stat.count)}건</span>
      </div>
      <div class="risk-rate">${fmtPct(row.rate)}<span>${fmtInt(row.stat.exposed)}/${fmtInt(row.stat.count)}</span></div>
    </article>`;
  }).join('')}</div>`;
}

function renderSpecialtyTable() {
  return `<div class="table-wrap"><table>
    <thead><tr><th>과목</th><th>지점수</th><th>발행건</th><th>노출건</th><th>노출율</th><th>미노출</th><th>10위밖</th></tr></thead>
    <tbody>${specialtyRows.map((row) => `<tr class="${statusFor(row.rate, row.stat.count)[1]}-row">
      <td class="name">${escapeHTML(row.specialty)}</td>
      <td>${fmtInt(row.branches)}</td>
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
    <thead><tr><th>과목</th><th>지점</th><th>유형</th><th>발행일</th><th>계정</th><th>키워드</th><th>순위</th><th>URL</th></tr></thead>
    <tbody>${juneRows
      .sort((a, b) => a.normalized_branch.localeCompare(b.normalized_branch, 'ko') || a.published_at.localeCompare(b.published_at))
      .map((row) => `<tr>
        <td>${escapeHTML(row.specialty)}</td>
        <td class="name">${escapeHTML(row.normalized_branch)}</td>
        <td>${escapeHTML(row.blog_type)}</td>
        <td>${row.published_at}</td>
        <td><code>${escapeHTML(row.blog_id)}</code></td>
        <td class="memo">${escapeHTML(row.keyword)}</td>
        <td>${row.exposure_rank == null ? '-' : row.exposure_rank}</td>
        <td>${row.published_url ? `<a href="${escapeHTML(row.published_url)}">열기</a>` : '-'}</td>
      </tr>`).join('')}</tbody>
  </table></div>`;
}

const html = `<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>2026년 6월 전체 지점 블로그 현황</title>
  <style>
    :root{--bg:#f3f6fb;--card:#fff;--ink:#172033;--muted:#66758f;--line:#dbe4f0;--head:#f7f9fc;--blue:#2563eb;--green:#16a34a;--amber:#d97706;--orange:#ea580c;--red:#dc2626}
    *{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}.page{max-width:1720px;margin:0 auto;padding:30px}header{display:flex;justify-content:space-between;gap:24px;align-items:end;margin-bottom:22px}h1{margin:0 0 8px;font-size:34px}p{margin:0;color:var(--muted);font-weight:700}.pill{border:1px solid var(--line);border-radius:999px;background:#fff;padding:10px 14px;color:var(--muted);font-weight:900;white-space:nowrap}.tabs{display:flex;gap:8px;flex-wrap:wrap;margin:16px 0}.tab-btn{border:1px solid var(--line);background:#fff;color:var(--muted);font-weight:900;padding:12px 18px;border-radius:10px;cursor:pointer;font-size:16px}.tab-btn.active{background:#213148;color:#fff}.tab{display:none}.tab.active{display:block}.metrics{display:grid;grid-template-columns:repeat(6,minmax(150px,1fr));gap:12px;margin-bottom:16px}.metric{background:#fff;border:1px solid var(--line);border-radius:10px;padding:17px}.label{font-size:14px;color:var(--muted);font-weight:900}.value{font-size:32px;font-weight:950;margin-top:8px}.sub{font-size:13px;color:var(--muted);margin-top:8px;font-weight:800}.metric.blue .value{color:var(--blue)}.metric.green .value{color:var(--green)}.metric.red .value{color:var(--red)}.card{background:var(--card);border:1px solid var(--line);border-radius:10px;margin-bottom:18px;overflow:hidden;box-shadow:0 12px 30px rgba(20,36,64,.04)}.card-head{display:flex;justify-content:space-between;align-items:center;gap:16px;padding:22px 24px;border-bottom:1px solid var(--line)}h2,h3{margin:0}.card-head span{color:var(--muted);font-weight:800}.table-wrap{overflow:auto}table{width:100%;min-width:1160px;border-collapse:collapse}th,td{padding:14px 16px;border-bottom:1px solid var(--line);text-align:center;font-size:16px;font-weight:700;vertical-align:middle}th{background:var(--head);color:#2f3c52;font-weight:950;white-space:nowrap}.name{font-weight:950}.memo{max-width:360px;white-space:normal;word-break:keep-all;overflow-wrap:anywhere;color:var(--muted);font-size:14px}.badge{display:inline-flex;align-items:center;justify-content:center;min-width:54px;padding:7px 11px;border-radius:999px;font-weight:950;font-size:14px}.badge.ok{background:#dcfce7;color:#15803d}.badge.watch{background:#fef3c7;color:#a16207}.badge.warn{background:#ffedd5;color:#c2410c}.badge.danger{background:#fee2e2;color:#be123c}.badge.muted{background:#e5e7eb;color:#64748b}.rate{display:inline-flex;flex-direction:column;align-items:center;gap:3px;min-width:80px}.rate strong{font-size:17px}.rate span{font-size:13px;color:var(--muted);font-weight:850}.rate.ok strong{color:var(--green)}.rate.watch strong{color:var(--amber)}.rate.warn strong{color:var(--orange)}.rate.danger strong{color:#be123c}.ok-row{background:#fff}.watch-row{background:#fff8dc;color:#8a3c08}.warn-row{background:#fff3e6;color:#9a3412}.danger-row{background:#fff0f2;color:#b20f3a}.muted-text{color:var(--muted)}code{font-size:14px;color:#39506f}a{color:var(--blue);font-weight:900;text-decoration:none}@media(max-width:1100px){.page{padding:20px}header{display:block}.pill{display:inline-flex;margin-top:12px}.metrics{grid-template-columns:repeat(2,minmax(0,1fr))}}
    .risk-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;padding:18px 22px 22px}.risk-card{display:flex;justify-content:space-between;align-items:center;gap:16px;border:1px solid var(--line);border-radius:10px;padding:16px}.risk-card strong{display:block;font-size:18px}.risk-card span{display:block;margin-top:4px;color:var(--muted);font-weight:850}.risk-rate{font-size:26px;font-weight:950;text-align:right}.risk-rate span{font-size:13px}@media(max-width:1100px){.risk-grid{grid-template-columns:1fr}}
  </style>
</head>
<body>
  <main class="page">
    <header>
      <div>
        <h1>2026년 6월 전체 지점 블로그 현황</h1>
        <p>유앤아이 계열과 bioadd lab 7개 지점을 제외한 6월 발행 데이터입니다. 기준표 매칭 지점만 포함했습니다.</p>
      </div>
      <div class="pill">기준 기간: 2026-06-01 ~ 2026-06-30</div>
    </header>

    <nav class="tabs">
      <button class="tab-btn active" data-tab="summary">요약</button>
      <button class="tab-btn" data-tab="branch">지점별</button>
      <button class="tab-btn" data-tab="specialty">과목별</button>
      <button class="tab-btn" data-tab="detail">상세</button>
    </nav>

    <section id="summary" class="tab active">
      <div class="metrics">
        ${metricCard('6월 발행건', fmtInt(overall.count), '기준표 매칭 데이터')}
        ${metricCard('6월 발행 지점', fmtInt(branchRows.length), '발행 1건 이상')}
        ${metricCard('종합 노출율', fmtPct(statRate(overall)), `${fmtInt(overall.exposed)}/${fmtInt(overall.count)}`, 'blue')}
        ${metricCard('일반 블로그 노출율', fmtPct(statRate(general)), `${fmtInt(general.exposed)}/${fmtInt(general.count)}`)}
        ${metricCard('최적 블로그 노출율', fmtPct(statRate(optimal)), `${fmtInt(optimal.exposed)}/${fmtInt(optimal.count)}`, 'green')}
        ${metricCard('미노출+10위밖', fmtInt(overall.noExposure + overall.outsideTop10), `미노출 ${fmtInt(overall.noExposure)} · 10위밖 ${fmtInt(overall.outsideTop10)}`, 'red')}
      </div>
      <section class="card">
        <div class="card-head"><h3>6월 확인 필요 지점</h3><span>발행 5건 이상 · 노출율 낮은 순</span></div>
        ${renderRiskSummary()}
      </section>
    </section>

    <section id="branch" class="tab">
      <section class="card">
        <div class="card-head"><h3>6월 지점별 상세</h3><span>일반/최적 블로그 구분</span></div>
        ${renderBranchTable()}
      </section>
    </section>

    <section id="specialty" class="tab">
      <section class="card">
        <div class="card-head"><h3>6월 과목별 현황</h3><span>노출율 낮은 순</span></div>
        ${renderSpecialtyTable()}
      </section>
    </section>

    <section id="detail" class="tab">
      <section class="card">
        <div class="card-head"><h3>6월 상세 데이터</h3><span>기준표 매칭 데이터</span></div>
        ${renderDetailTable()}
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
  </script>
</body>
</html>`;

fs.writeFileSync(path.join(projectDir, outputHtml), html);

console.log(JSON.stringify({
  outputHtml,
  juneRows: juneRows.length,
  branches: branchRows.length,
  general: { count: general.count, exposed: general.exposed, rate: fmtPct(statRate(general)) },
  optimal: { count: optimal.count, exposed: optimal.exposed, rate: fmtPct(statRate(optimal)) },
}, null, 2));

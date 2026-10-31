import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';

const projectDir = path.dirname(new URL(import.meta.url).pathname);
const repoRoot = path.resolve(projectDir, '../../../..');
const dbPath = path.join(repoRoot, 'data/equipment.db');

const targets = [
  ['글로우치과교정과치과의원', ['글로우치과', '글로우치과교정과치과의원']],
  ['날개병원', ['날개병원']],
  ['노블와이성형외과', ['노블와이', '노블와이성형외과']],
  ['아도의원', ['아도의원']],
  ['온우의원', ['온우의원']],
  ['청담미닛의원', ['청담미닛', '청담미닛의원']],
  ['청담위아르여성의원', ['청담위아르', '청담위아르여성의원', '청담위아르여성병원']],
];

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

function stat() {
  return { count: 0, exposed: 0, noExposure: 0, outsideTop10: 0, first: '', last: '', accounts: new Map() };
}

function add(statObj, row) {
  statObj.count += 1;
  statObj.exposed += row.top10_success;
  statObj.noExposure += row.no_exposure;
  statObj.outsideTop10 += row.outside_top10;
  if (!statObj.first || row.published_at < statObj.first) statObj.first = row.published_at;
  if (!statObj.last || row.published_at > statObj.last) statObj.last = row.published_at;
  if (row.blog_id) statObj.accounts.set(row.blog_id, (statObj.accounts.get(row.blog_id) || 0) + 1);
}

function rankStatus(rank) {
  if (rank == null || rank === 0) return '미노출';
  if (rank <= 5) return '상위5';
  if (rank <= 10) return '상위10';
  return '10위밖';
}

function canonicalBranch(row) {
  const text = `${row.project_branch} ${row.branch_name} ${row.content_number}`;
  for (const [branch, aliases] of targets) {
    if (aliases.some((alias) => text.includes(alias))) return branch;
  }
  return '';
}

function groupName(row) {
  return row.blog_channel === 'opt' ? '최블' : '브블/일반';
}

const sql = `
SELECT
  id, published_at, branch_name, project_branch, content_number, keyword, exposure_rank,
  post_type, post_type_main, post_type_sub, blog_channel, blog_id, title, status, published_url,
  project
FROM blog_posts
WHERE published_at >= '2026-01-01'
  AND published_at < '2026-07-01'
  AND (
    branch_name LIKE '%글로우%' OR project_branch LIKE '%글로우%' OR content_number LIKE '%글로우%' OR
    branch_name LIKE '%날개%' OR project_branch LIKE '%날개%' OR content_number LIKE '%날개%' OR
    branch_name LIKE '%노블%' OR project_branch LIKE '%노블%' OR content_number LIKE '%노블%' OR
    branch_name LIKE '%아도%' OR project_branch LIKE '%아도%' OR content_number LIKE '%아도%' OR
    branch_name LIKE '%온우%' OR project_branch LIKE '%온우%' OR content_number LIKE '%온우%' OR
    branch_name LIKE '%청담미닛%' OR project_branch LIKE '%청담미닛%' OR content_number LIKE '%청담미닛%' OR
    branch_name LIKE '%청담위아르%' OR project_branch LIKE '%청담위아르%' OR content_number LIKE '%청담위아르%'
  )
ORDER BY published_at, id;
`;

const raw = execFileSync('sqlite3', ['-header', '-csv', dbPath, sql], {
  encoding: 'utf8',
  maxBuffer: 64 * 1024 * 1024,
});
const parsed = parseCSV(raw);
const headers = parsed.shift();
const idx = Object.fromEntries(headers.map((name, index) => [name, index]));

const rows = parsed.map((rawRow) => {
  const rankRaw = rawRow[idx.exposure_rank];
  const rank = rankRaw === '' ? null : Number(rankRaw);
  const row = {
    id: rawRow[idx.id],
    published_at: rawRow[idx.published_at],
    branch_name: rawRow[idx.branch_name],
    project_branch: rawRow[idx.project_branch],
    content_number: rawRow[idx.content_number],
    keyword: rawRow[idx.keyword],
    exposure_rank: rank,
    post_type: rawRow[idx.post_type],
    post_type_main: rawRow[idx.post_type_main],
    post_type_sub: rawRow[idx.post_type_sub],
    blog_channel: rawRow[idx.blog_channel],
    blog_id: rawRow[idx.blog_id],
    title: rawRow[idx.title],
    status: rawRow[idx.status],
    published_url: rawRow[idx.published_url],
    project: rawRow[idx.project],
  };
  const branch = canonicalBranch(row);
  const noExposure = rank == null || rank === 0 ? 1 : 0;
  const outsideTop10 = rank != null && rank >= 11 ? 1 : 0;
  return {
    ...row,
    target_branch: branch,
    analysis_group: groupName(row),
    rank_status: rankStatus(rank),
    top10_success: rank != null && rank >= 1 && rank <= 10 ? 1 : 0,
    failure: noExposure + outsideTop10,
    no_exposure: noExposure,
    outside_top10: outsideTop10,
  };
}).filter((row) => row.target_branch && !/서비스/.test(`${row.branch_name} ${row.project_branch} ${row.content_number}`));

const detailHeader = [
  'target_branch', 'analysis_group', 'published_at', 'branch_name', 'content_number', 'keyword',
  'exposure_rank', 'rank_status', 'top10_success', 'failure', 'post_type', 'post_type_main',
  'post_type_sub', 'blog_channel', 'blog_id', 'account_name', 'title', 'status', 'published_url',
  'project', 'project_branch', 'id',
];

fs.writeFileSync(path.join(projectDir, 'bioadd_lab_target_detail.csv'), '\ufeff' + toCSV([
  detailHeader,
  ...rows.map((row) => [
    row.target_branch, row.analysis_group, row.published_at, row.branch_name, row.content_number,
    row.keyword, row.exposure_rank ?? '', row.rank_status, row.top10_success, row.failure,
    row.post_type, row.post_type_main, row.post_type_sub, row.blog_channel, row.blog_id, '',
    row.title, row.status, row.published_url, row.project, row.project_branch, row.id,
  ]),
]));

function rowsFor(branch, type = null) {
  return rows.filter((row) => row.target_branch === branch && (!type || row.analysis_group === type));
}

function summarize(list) {
  const s = stat();
  for (const row of list) add(s, row);
  return s;
}

const summaryRows = [];
for (const [branch] of targets) {
  for (const label of ['합계', '브블/일반', '최블']) {
    const list = label === '합계' ? rowsFor(branch) : rowsFor(branch, label);
    const s = summarize(list);
    summaryRows.push({
      branch,
      label,
      ...s,
      failure: s.noExposure + s.outsideTop10,
      rate: pct(s.exposed, s.count),
    });
  }
}
const overall = summarize(rows);
for (const label of ['합계', '브블/일반', '최블']) {
  const list = label === '합계' ? rows : rows.filter((row) => row.analysis_group === label);
  const s = summarize(list);
  summaryRows.push({
    branch: '전체',
    label,
    ...s,
    failure: s.noExposure + s.outsideTop10,
    rate: pct(s.exposed, s.count),
  });
}

fs.writeFileSync(path.join(projectDir, 'bioadd_lab_target_summary.csv'), '\ufeff' + toCSV([
  ['target_branch', 'analysis_group', 'first_published', 'last_published', 'published_count', 'top10_success', 'success_rate', 'failure', 'failure_rate', 'no_exposure', 'outside_top10'],
  ...summaryRows.map((row) => [
    row.branch, row.label, row.first, row.last, row.count, row.exposed, fmtPct(row.rate),
    row.failure, fmtPct(pct(row.failure, row.count)), row.noExposure, row.outsideTop10,
  ]),
]));

const monthRows = [];
for (const [branch] of targets) {
  for (const type of ['브블/일반', '최블']) {
    for (const month of ['2026-01', '2026-02', '2026-03', '2026-04', '2026-05', '2026-06']) {
      const list = rows.filter((row) => row.target_branch === branch && row.analysis_group === type && row.published_at.startsWith(month));
      if (!list.length) continue;
      const s = summarize(list);
      monthRows.push({
        branch,
        type,
        month,
        ...s,
        failure: s.noExposure + s.outsideTop10,
        rate: pct(s.exposed, s.count),
      });
    }
  }
}

fs.writeFileSync(path.join(projectDir, 'bioadd_lab_monthly_summary.csv'), '\ufeff' + toCSV([
  ['target_branch', 'analysis_group', 'month', 'published_count', 'failure', 'failure_rate', 'no_exposure', 'outside_top10', 'top10_success', 'success_rate'],
  ...monthRows.map((row) => [
    row.branch, row.type, row.month, row.count, row.failure, fmtPct(pct(row.failure, row.count)),
    row.noExposure, row.outsideTop10, row.exposed, fmtPct(row.rate),
  ]),
]));

function statusClass(rate) {
  if (rate == null) return 'muted';
  if (rate < 0.4) return 'danger';
  if (rate < 0.55) return 'warn';
  if (rate < 0.7) return 'watch';
  return 'ok';
}

function tableRows(label) {
  return summaryRows
    .filter((row) => row.branch !== '전체' && row.label === label)
    .sort((a, b) => a.first.localeCompare(b.first, 'ko') || a.branch.localeCompare(b.branch, 'ko'))
    .map((row) => `<tr class="${statusClass(row.rate)}"><td>${escapeHTML(row.branch)}</td><td>${escapeHTML(row.label)}</td><td>${row.first || '-'}</td><td>${row.last || '-'}</td><td>${fmtInt(row.count)}</td><td>${fmtInt(row.exposed)}</td><td><b>${fmtPct(row.rate)}</b></td><td>${fmtInt(row.failure)}</td></tr>`)
    .join('');
}

function monthlyTable(type) {
  const months = ['2026-04', '2026-05', '2026-06'];
  return `<table><thead><tr><th>지점</th>${months.map((month) => `<th>${month.slice(5)}월</th>`).join('')}<th>기간</th></tr></thead><tbody>${targets.map(([branch]) => {
    const cells = months.map((month) => {
      const row = monthRows.find((item) => item.branch === branch && item.type === type && item.month === month);
      return row ? `<td class="${statusClass(row.rate)}"><b>${fmtPct(row.rate)}</b><span>${fmtInt(row.exposed)}/${fmtInt(row.count)}</span></td>` : '<td class="empty">-</td>';
    }).join('');
    const total = summaryRows.find((row) => row.branch === branch && row.label === type);
    return `<tr><td>${escapeHTML(branch)}</td>${cells}<td><b>${fmtPct(total?.rate)}</b></td></tr>`;
  }).join('')}</tbody></table>`;
}

const totalGeneral = summaryRows.find((row) => row.branch === '전체' && row.label === '브블/일반');
const totalOptimal = summaryRows.find((row) => row.branch === '전체' && row.label === '최블');

const html = `<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>바이오애드랩 분석 보고서</title><style>
:root{--bg:#f5f7fa;--card:#fff;--ink:#172033;--muted:#667085;--line:#d8dee8;--blue:#1d4ed8;--green:#16a34a;--red:#be123c;--amber:#92400e}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}.page{max-width:1380px;margin:0 auto;padding:28px 22px 64px}header{border-bottom:1px solid var(--line);padding-bottom:18px}h1{margin:0;font-size:34px}.subtitle{margin:8px 0 0;color:var(--muted);font-weight:800}.metrics{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:10px;margin:20px 0}.metric,.panel{background:#fff;border:1px solid var(--line);border-radius:8px;box-shadow:0 10px 22px rgba(15,23,42,.06)}.metric{padding:14px 16px}.label{font-size:13px;color:#475569;font-weight:850}.value{font-size:30px;font-weight:950;margin-top:6px}.sub{font-size:13px;color:#64748b;margin-top:4px}.tabs{display:flex;gap:6px;position:sticky;top:0;background:rgba(245,247,250,.96);padding:12px 0}.tab{border:1px solid var(--line);background:#fff;border-radius:7px;padding:9px 13px;font-weight:900;cursor:pointer}.tab.active{background:var(--blue);color:#fff}.section{display:none}.section.active{display:block}.panel{margin-top:16px;overflow:hidden}.panel-title{display:flex;justify-content:space-between;gap:12px;padding:14px 16px;border-bottom:1px solid #e8edf4}.panel-title h3{margin:0}.table-wrap{overflow:auto}table{width:100%;border-collapse:collapse;white-space:nowrap}th,td{padding:10px 12px;border-bottom:1px solid #e8edf4;text-align:center}th{background:#f8fafc}.ok b{color:var(--green)}.watch b{color:var(--amber)}.warn b{color:#c2410c}.danger b{color:var(--red)}td span{display:block;font-size:12px;color:var(--muted)}.empty{color:#94a3b8}.note{padding:14px 16px;color:var(--muted);font-weight:800}.detail-table{font-size:13px}.grid-2{display:grid;grid-template-columns:1fr 1fr;gap:14px}@media(max-width:1000px){.metrics,.grid-2{grid-template-columns:1fr}}
</style></head><body><main class="page"><header><h1>바이오애드랩 분석 보고서</h1><p class="subtitle">타겟 7개 지점 · 기간 2026년 1월~6월 · 일반 블로그/최적 블로그 분리 · 서비스 발행 제외</p></header><nav class="tabs"><button class="tab active" data-tab="overview">요약</button><button class="tab" data-tab="branch">지점별 성과</button><button class="tab" data-tab="monthly">월별 변화</button><button class="tab" data-tab="detail">상세 데이터</button></nav>
<section id="overview" class="section active"><div class="metrics"><article class="metric"><div class="label">전체 발행건</div><div class="value">${fmtInt(overall.count)}</div><div class="sub">일반+최적</div></article><article class="metric"><div class="label">전체 성공률</div><div class="value">${fmtPct(pct(overall.exposed, overall.count))}</div><div class="sub">${fmtInt(overall.exposed)}/${fmtInt(overall.count)}</div></article><article class="metric"><div class="label">일반 블로그</div><div class="value">${fmtInt(totalGeneral.count)}</div><div class="sub">성공률 ${fmtPct(totalGeneral.rate)}</div></article><article class="metric"><div class="label">최적 블로그</div><div class="value">${fmtInt(totalOptimal.count)}</div><div class="sub">성공률 ${fmtPct(totalOptimal.rate)}</div></article><article class="metric"><div class="label">진입 실패</div><div class="value">${fmtInt(overall.noExposure + overall.outsideTop10)}</div><div class="sub">미노출+10위밖</div></article></div><section class="panel"><div class="panel-title"><h3>지점별 요약</h3><span>전체 발행 기준</span></div><div class="table-wrap"><table><thead><tr><th>지점</th><th>구분</th><th>시작일</th><th>최근 발행일</th><th>발행건</th><th>성공건</th><th>성공률</th><th>진입 실패</th></tr></thead><tbody>${tableRows('합계')}</tbody></table></div></section></section>
<section id="branch" class="section"><section class="panel"><div class="panel-title"><h3>지점별 일반/최적 성과</h3></div><div class="table-wrap"><table><thead><tr><th>지점</th><th>구분</th><th>시작일</th><th>최근 발행일</th><th>발행건</th><th>성공건</th><th>성공률</th><th>진입 실패</th></tr></thead><tbody>${tableRows('브블/일반')}${tableRows('최블')}</tbody></table></div></section></section>
<section id="monthly" class="section"><div class="grid-2"><section class="panel"><div class="panel-title"><h3>일반 블로그 월별 성공률</h3></div><div class="table-wrap">${monthlyTable('브블/일반')}</div></section><section class="panel"><div class="panel-title"><h3>최적 블로그 월별 성공률</h3></div><div class="table-wrap">${monthlyTable('최블')}</div></section></div></section>
<section id="detail" class="section"><section class="panel"><div class="panel-title"><h3>상세 데이터</h3></div><div class="table-wrap"><table class="detail-table"><thead><tr><th>지점</th><th>구분</th><th>발행일</th><th>콘텐츠번호</th><th>키워드</th><th>순위</th><th>상태</th><th>blog_id</th></tr></thead><tbody>${rows.map((row) => `<tr><td>${escapeHTML(row.target_branch)}</td><td>${escapeHTML(row.analysis_group === '최블' ? '최적 블로그' : '일반 블로그')}</td><td>${row.published_at}</td><td>${escapeHTML(row.content_number)}</td><td>${escapeHTML(row.keyword)}</td><td>${row.exposure_rank ?? ''}</td><td>${escapeHTML(row.rank_status)}</td><td>${escapeHTML(row.blog_id)}</td></tr>`).join('')}</tbody></table></div></section></section></main><script>document.querySelectorAll('.tab').forEach(btn=>btn.addEventListener('click',()=>{document.querySelectorAll('.tab').forEach(x=>x.classList.remove('active'));document.querySelectorAll('.section').forEach(x=>x.classList.remove('active'));btn.classList.add('active');document.getElementById(btn.dataset.tab).classList.add('active');}));</script></body></html>`;

fs.writeFileSync(path.join(projectDir, 'bioadd_lab_report.html'), html);
console.log(JSON.stringify({ detailRows: rows.length, total: overall.count, general: totalGeneral.count, optimal: totalOptimal.count, output: 'bioadd_lab_report.html' }, null, 2));

import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';

const projectDir = path.dirname(new URL(import.meta.url).pathname);
const repoRoot = path.resolve(projectDir, '../../../..');
const dbPath = path.join(repoRoot, 'data/equipment.db');
const MONTHS = ['2026-01', '2026-02', '2026-03', '2026-04', '2026-05', '2026-06'];

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

function pct(n, d) {
  return d ? n / d : null;
}

function fmtPct(value) {
  return value == null ? '-' : `${(value * 100).toFixed(1)}%`;
}

function fmtInt(value) {
  return Number(value || 0).toLocaleString('ko-KR');
}

function rankStatus(rank) {
  if (rank == null || rank === 0) return '실패_미도달';
  if (rank <= 5) return '상위5';
  if (rank <= 10) return '상위10';
  return '10위밖';
}

function blogCategory(row) {
  return row.project || row.branch_name || row.project_branch || row.content_number || '(미분류)';
}

function groupOf(row) {
  const text = `${row.project} ${row.branch_name} ${row.project_branch} ${row.content_number}`;
  if (/유앤|유앤아이/.test(text)) return '유앤';
  if (/대전NB|대전준최|준최|NB/.test(text)) return '기타';
  return '로컬';
}

function stat() {
  return { count: 0, ranked: 0, unranked: 0, failure: 0, top5: 0, top10: 0, outsideTop10: 0, rankSum: 0, rankCount: 0 };
}

function add(s, row) {
  s.count += 1;
  if (row.rank == null) s.unranked += 1;
  else s.ranked += 1;
  if (row.noExposure) s.failure += 1;
  if (row.top5) s.top5 += 1;
  if (row.top10) s.top10 += 1;
  if (row.outsideTop10) s.outsideTop10 += 1;
  if (row.rank && row.rank > 0) {
    s.rankSum += row.rank;
    s.rankCount += 1;
  }
}

function avgRank(s) {
  return s.rankCount ? (s.rankSum / s.rankCount).toFixed(2) : '';
}

function statusClass(rate) {
  if (rate == null) return 'muted';
  if (rate < 0.4) return 'danger';
  if (rate < 0.55) return 'warn';
  if (rate < 0.7) return 'watch';
  return 'ok';
}

const sql = `
SELECT
  id, published_at, branch_name, project_branch, content_number, keyword, exposure_rank,
  title, author_main, author, status, published_url, project, blog_id, created_at, updated_at
FROM blog_posts
WHERE published_at >= '2026-01-01'
  AND published_at < '2026-07-01'
  AND blog_channel = 'opt'
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
    month: rawRow[idx.published_at].slice(0, 7),
    published_at: rawRow[idx.published_at],
    branch_name: rawRow[idx.branch_name],
    project_branch: rawRow[idx.project_branch],
    content_number: rawRow[idx.content_number],
    keyword: rawRow[idx.keyword],
    rank,
    title: rawRow[idx.title],
    author: rawRow[idx.author_main] || rawRow[idx.author],
    status: rawRow[idx.status],
    url: rawRow[idx.published_url],
    project: rawRow[idx.project],
    blog_id: rawRow[idx.blog_id],
    created_at: rawRow[idx.created_at],
    updated_at: rawRow[idx.updated_at],
  };
  return {
    ...row,
    category: blogCategory(row),
    group: groupOf(row),
    top5: rank != null && rank >= 1 && rank <= 5 ? 1 : 0,
    top10: rank != null && rank >= 1 && rank <= 10 ? 1 : 0,
    noExposure: rank == null || rank === 0 ? 1 : 0,
    outsideTop10: rank != null && rank >= 11 ? 1 : 0,
  };
});

fs.writeFileSync(path.join(projectDir, 'optimal_blog_2026H1_detail.csv'), '\ufeff' + toCSV([
  ['발행월', '발행일', '블로그카테고리', '블로그ID', '발행지점', '콘텐츠번호', '키워드', '순위', '순위상태', '상위5성공', '상위10성공', '미도달실패', '제목', '담당자', '상태', 'URL', '원본종류', '프로젝트월', '프로젝트지점', '작성_등록일', '수정일', 'post_id'],
  ...rows.map((row) => [
    row.month, row.published_at, row.category, row.blog_id, row.branch_name, row.content_number,
    row.keyword, row.rank ?? '', rankStatus(row.rank), row.top5, row.top10, row.noExposure,
    row.title, row.author, row.status, row.url, row.project || row.category, row.month,
    row.project_branch, row.created_at, row.updated_at, row.id,
  ]),
]));

function summarize(list) {
  const s = stat();
  for (const row of list) add(s, row);
  return s;
}

function summaryRow(month, group, list) {
  const s = summarize(list);
  return [
    month,
    group,
    s.count,
    s.ranked,
    s.unranked,
    s.noExposure ?? s.failure,
    fmtPct(pct(s.failure, s.count)).replace('%', ''),
    s.top5,
    fmtPct(pct(s.top5, s.count)).replace('%', ''),
    s.top10,
    fmtPct(pct(s.top10, s.count)).replace('%', ''),
    s.outsideTop10,
    fmtPct(pct(s.outsideTop10, s.count)).replace('%', ''),
    avgRank(s),
  ];
}

const groupCsv = [['월', '그룹', '발행건', '순위기록', '미기록', '실패', '실패율', '상위5', '상위5율', '상위10', '상위10율', '10위밖', '10위밖율', '평균순위_0제외']];
for (const month of MONTHS) {
  for (const group of ['유앤', '로컬', '기타']) {
    const list = rows.filter((row) => row.month === month && row.group === group);
    if (list.length) groupCsv.push(summaryRow(month, group, list));
  }
}
fs.writeFileSync(path.join(projectDir, 'optimal_blog_2026H1_monthly_by_group.csv'), '\ufeff' + toCSV(groupCsv));

const byAccount = [['월', '그룹', '블로그카테고리', '블로그ID', '발행건', '순위기록', '미기록', '실패', '실패율', '상위5', '상위5율', '상위10', '상위10율', '10위밖', '10위밖율', '평균순위_0제외']];
for (const month of MONTHS) {
  const keys = [...new Set(rows.filter((row) => row.month === month).map((row) => `${row.group}\t${row.category}\t${row.blog_id}`))].sort();
  for (const key of keys) {
    const [group, category, blogId] = key.split('\t');
    const list = rows.filter((row) => row.month === month && row.group === group && row.category === category && row.blog_id === blogId);
    const s = summarize(list);
    byAccount.push([
      month, group, category, blogId, s.count, s.ranked, s.unranked, s.failure,
      fmtPct(pct(s.failure, s.count)).replace('%', ''), s.top5,
      fmtPct(pct(s.top5, s.count)).replace('%', ''), s.top10,
      fmtPct(pct(s.top10, s.count)).replace('%', ''), s.outsideTop10,
      fmtPct(pct(s.outsideTop10, s.count)).replace('%', ''), avgRank(s),
    ]);
  }
}
fs.writeFileSync(path.join(projectDir, 'optimal_blog_2026H1_monthly_by_blog.csv'), '\ufeff' + toCSV(byAccount));

const overall = summarize(rows);
const groupTotals = ['유앤', '로컬', '기타'].map((group) => ({ group, stat: summarize(rows.filter((row) => row.group === group)) }));
const monthlyRows = groupCsv.slice(1);
const accountRows = byAccount.slice(1).sort((a, b) => Number(b[4]) - Number(a[4])).slice(0, 40);

function statCell(s) {
  return `<strong>${fmtPct(pct(s.top10, s.count))}</strong><span>${fmtInt(s.top10)}/${fmtInt(s.count)} · 실패 ${fmtInt(s.failure + s.outsideTop10)}</span>`;
}

const html = `<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>2026H1 최적블로그 유앤/로컬 성과</title><style>
:root{--bg:#f3f6fb;--card:#fff;--ink:#172033;--muted:#66758f;--line:#dbe4f0;--blue:#2563eb;--green:#16a34a;--red:#be123c;--amber:#a16207}*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}.page{max-width:1500px;margin:0 auto;padding:32px}h1{margin:0;font-size:34px}p{color:var(--muted);font-weight:800}.tabs{display:flex;gap:8px;margin:20px 0;position:sticky;top:0;background:rgba(243,246,251,.96);padding:10px 0}.tab{border:1px solid var(--line);border-radius:9px;background:#fff;padding:10px 15px;font-weight:900;cursor:pointer}.tab.active{background:#213148;color:#fff}.section{display:none}.section.active{display:block}.metrics{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:12px}.metric,.card{background:var(--card);border:1px solid var(--line);border-radius:10px;box-shadow:0 12px 30px rgba(20,36,64,.04)}.metric{padding:17px}.label{color:var(--muted);font-weight:900}.value{font-size:32px;font-weight:950;margin-top:8px}.sub{font-size:13px;color:var(--muted);margin-top:5px}.card{margin-top:18px;overflow:hidden}.card-head{display:flex;justify-content:space-between;gap:12px;padding:18px 20px;border-bottom:1px solid var(--line)}.card-head h3{margin:0}.table-wrap{overflow:auto}table{width:100%;min-width:900px;border-collapse:collapse}th,td{padding:12px 14px;border-bottom:1px solid var(--line);text-align:center}th{background:#f7f9fc}.ok strong{color:var(--green)}.watch strong{color:var(--amber)}.warn strong{color:#c2410c}.danger strong{color:var(--red)}td span{display:block;color:var(--muted);font-size:12px;margin-top:3px}@media(max-width:1000px){.metrics{grid-template-columns:1fr 1fr}}
</style></head><body><main class="page"><header><h1>2026H1 최적블로그 성과 분석</h1><p>유앤/로컬 최적블로그 · 기준 기간 2026년 1월~6월 · 성공 기준 상위10 진입</p></header><nav class="tabs"><button class="tab active" data-tab="summary">요약</button><button class="tab" data-tab="monthly">월별</button><button class="tab" data-tab="account">계정</button><button class="tab" data-tab="detail">상세</button></nav>
<section id="summary" class="section active"><div class="metrics"><article class="metric"><div class="label">발행건</div><div class="value">${fmtInt(overall.count)}</div><div class="sub">최적블로그 전체</div></article><article class="metric"><div class="label">상위10 성공률</div><div class="value">${fmtPct(pct(overall.top10, overall.count))}</div><div class="sub">${fmtInt(overall.top10)}/${fmtInt(overall.count)}</div></article><article class="metric"><div class="label">진입 실패</div><div class="value">${fmtInt(overall.failure + overall.outsideTop10)}</div><div class="sub">미노출+10위밖</div></article><article class="metric"><div class="label">유앤 발행건</div><div class="value">${fmtInt(groupTotals.find((row) => row.group === '유앤').stat.count)}</div><div class="sub">${fmtPct(pct(groupTotals.find((row) => row.group === '유앤').stat.top10, groupTotals.find((row) => row.group === '유앤').stat.count))}</div></article><article class="metric"><div class="label">로컬 발행건</div><div class="value">${fmtInt(groupTotals.find((row) => row.group === '로컬').stat.count)}</div><div class="sub">${fmtPct(pct(groupTotals.find((row) => row.group === '로컬').stat.top10, groupTotals.find((row) => row.group === '로컬').stat.count))}</div></article></div><section class="card"><div class="card-head"><h3>그룹별 누적 성과</h3></div><div class="table-wrap"><table><thead><tr><th>그룹</th><th>발행건</th><th>상위10</th><th>성공률</th><th>진입 실패</th><th>평균순위</th></tr></thead><tbody>${groupTotals.map(({ group, stat: s }) => `<tr class="${statusClass(pct(s.top10, s.count))}"><td>${group}</td><td>${fmtInt(s.count)}</td><td>${fmtInt(s.top10)}</td><td><strong>${fmtPct(pct(s.top10, s.count))}</strong></td><td>${fmtInt(s.failure + s.outsideTop10)}</td><td>${avgRank(s)}</td></tr>`).join('')}</tbody></table></div></section></section>
<section id="monthly" class="section"><section class="card"><div class="card-head"><h3>월별 그룹 성과</h3></div><div class="table-wrap"><table><thead><tr><th>월</th><th>그룹</th><th>발행건</th><th>상위10</th><th>성공률</th><th>진입 실패</th><th>평균순위</th></tr></thead><tbody>${monthlyRows.map((row) => `<tr class="${statusClass(pct(Number(row[9]), Number(row[2])))}"><td>${row[0]}</td><td>${row[1]}</td><td>${fmtInt(row[2])}</td><td>${fmtInt(row[9])}</td><td><strong>${row[10]}%</strong></td><td>${fmtInt(Number(row[5]) + Number(row[11]))}</td><td>${row[13]}</td></tr>`).join('')}</tbody></table></div></section></section>
<section id="account" class="section"><section class="card"><div class="card-head"><h3>계정별 상위 40개</h3><span>발행건 많은 순</span></div><div class="table-wrap"><table><thead><tr><th>월</th><th>그룹</th><th>카테고리</th><th>블로그ID</th><th>발행건</th><th>상위10</th><th>성공률</th><th>진입 실패</th></tr></thead><tbody>${accountRows.map((row) => `<tr class="${statusClass(pct(Number(row[11]), Number(row[4])))}"><td>${row[0]}</td><td>${row[1]}</td><td>${escapeHTML(row[2])}</td><td>${escapeHTML(row[3])}</td><td>${fmtInt(row[4])}</td><td>${fmtInt(row[11])}</td><td><strong>${row[12]}%</strong></td><td>${fmtInt(Number(row[7]) + Number(row[13]))}</td></tr>`).join('')}</tbody></table></div></section></section>
<section id="detail" class="section"><section class="card"><div class="card-head"><h3>상세 데이터</h3></div><div class="table-wrap"><table><thead><tr><th>발행일</th><th>그룹</th><th>카테고리</th><th>블로그ID</th><th>발행지점</th><th>키워드</th><th>순위</th><th>상태</th></tr></thead><tbody>${rows.map((row) => `<tr><td>${row.published_at}</td><td>${row.group}</td><td>${escapeHTML(row.category)}</td><td>${escapeHTML(row.blog_id)}</td><td>${escapeHTML(row.branch_name)}</td><td>${escapeHTML(row.keyword)}</td><td>${row.rank ?? ''}</td><td>${rankStatus(row.rank)}</td></tr>`).join('')}</tbody></table></div></section></section></main><script>document.querySelectorAll('.tab').forEach(btn=>btn.addEventListener('click',()=>{document.querySelectorAll('.tab').forEach(x=>x.classList.remove('active'));document.querySelectorAll('.section').forEach(x=>x.classList.remove('active'));btn.classList.add('active');document.getElementById(btn.dataset.tab).classList.add('active');}));</script></body></html>`;

fs.writeFileSync(path.join(projectDir, 'optimal_blog_2026H1_report.html'), html);
console.log(JSON.stringify({ rows: rows.length, total: overall.count, top10: overall.top10, output: 'optimal_blog_2026H1_report.html' }, null, 2));

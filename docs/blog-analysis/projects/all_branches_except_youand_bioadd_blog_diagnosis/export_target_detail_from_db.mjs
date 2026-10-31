import fs from 'node:fs';
import path from 'node:path';
import { execFileSync } from 'node:child_process';

const projectDir = path.dirname(new URL(import.meta.url).pathname);
const repoRoot = path.resolve(projectDir, '../../../..');
const dbPath = path.join(repoRoot, 'data/equipment.db');

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

function rankStatus(rank) {
  if (rank == null || rank === 0) return '미노출';
  if (rank <= 5) return '상위5';
  if (rank <= 10) return '상위10';
  return '10위밖';
}

const sql = `
SELECT
  COALESCE(NULLIF(project_branch, ''), NULLIF(branch_name, ''), NULLIF(content_number, ''), '') AS target_branch,
  CASE WHEN blog_channel = 'opt' THEN '최적 블로그' ELSE '일반 블로그' END AS analysis_group,
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
  id
FROM blog_posts
WHERE published_at >= '2026-01-01'
  AND published_at < '2026-07-01'
ORDER BY published_at, id;
`;

const raw = execFileSync('sqlite3', ['-header', '-csv', dbPath, sql], {
  encoding: 'utf8',
  maxBuffer: 64 * 1024 * 1024,
});
const parsed = parseCSV(raw);
const headers = parsed.shift();
const idx = Object.fromEntries(headers.map((name, index) => [name, index]));

const output = [[
  'target_branch',
  'analysis_group',
  'published_at',
  'branch_name',
  'project_branch',
  'content_number',
  'keyword',
  'exposure_rank',
  'rank_status',
  'top10_success',
  'no_exposure',
  'outside_top10',
  'post_type',
  'post_type_main',
  'post_type_sub',
  'blog_channel',
  'blog_id',
  'title',
  'status',
  'published_url',
  'id',
]];

for (const row of parsed) {
  const rankRaw = row[idx.exposure_rank];
  const rank = rankRaw === '' ? null : Number(rankRaw);
  const noExposure = rank == null || rank === 0 ? 1 : 0;
  const outsideTop10 = rank != null && rank >= 11 ? 1 : 0;
  output.push([
    row[idx.target_branch],
    row[idx.analysis_group],
    row[idx.published_at],
    row[idx.branch_name],
    row[idx.project_branch],
    row[idx.content_number],
    row[idx.keyword],
    rankRaw,
    rankStatus(rank),
    rank != null && rank >= 1 && rank <= 10 ? 1 : 0,
    noExposure,
    outsideTop10,
    row[idx.post_type],
    row[idx.post_type_main],
    row[idx.post_type_sub],
    row[idx.blog_channel],
    row[idx.blog_id],
    row[idx.title],
    row[idx.status],
    row[idx.published_url],
    row[idx.id],
  ]);
}

fs.writeFileSync(path.join(projectDir, 'target_detail.csv'), toCSV(output));
console.log(JSON.stringify({ output: 'target_detail.csv', rows: output.length - 1 }, null, 2));

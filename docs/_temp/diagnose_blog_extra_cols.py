"""
CSV 추가 컬럼 진단:
- blog_channel: 최적(opt) / 브랜드(br) 구분
- branch_name: 지점명
"""
import sqlite3
from pathlib import Path

DB = Path(__file__).resolve().parents[2] / "data" / "equipment.db"
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

def section(name):
    print(f"\n{'='*60}\n{name}\n{'='*60}")

def run(sql, params=()):
    cur.execute(sql, params)
    cols = [d[0] for d in cur.description]
    rows = cur.fetchall()
    widths = [max(len(c), max((len(str(r[i])) for r in rows), default=0)) for i, c in enumerate(cols)]
    print(" | ".join(c.ljust(widths[i]) for i, c in enumerate(cols)))
    print("-+-".join("-" * w for w in widths))
    for r in rows:
        print(" | ".join(str(r[i]).ljust(widths[i]) for i in range(len(cols))))
    print(f"({len(rows)} rows)")

# 키워드 추적 대상에만 한정 (기존 export 조건 동일)
BASE_WHERE = """
WHERE keyword IS NOT NULL AND keyword <> ''
  AND blog_id IS NOT NULL AND blog_id <> ''
  AND post_number IS NOT NULL AND post_number <> ''
  AND published_at IS NOT NULL AND published_at <> ''
  AND (platform IS NULL OR platform <> 'cafe')
  AND COALESCE(NULLIF(clean_title,''), NULLIF(title,''), NULLIF(scraped_title,'')) IS NOT NULL
"""

# 1. blog_channel 분포 (최적/브랜드)
section("1. blog_channel (최적/브랜드) 분포")
run(f"""
SELECT
  COALESCE(NULLIF(blog_channel,''), '(없음)') AS channel,
  COUNT(*) AS cnt
FROM blog_posts
{BASE_WHERE}
GROUP BY channel
ORDER BY cnt DESC
""")

# 2. branch_name 채움률
section("2. branch_name (지점명) 채움률")
run(f"""
SELECT
  COUNT(*) AS total,
  SUM(CASE WHEN branch_name IS NOT NULL AND branch_name <> '' THEN 1 ELSE 0 END) AS has_branch,
  SUM(CASE WHEN branch_name IS NULL OR branch_name = '' THEN 1 ELSE 0 END) AS missing_branch
FROM blog_posts
{BASE_WHERE}
""")

# 3. branch_name TOP 30
section("3. branch_name TOP 30 (지점별 발행량)")
run(f"""
SELECT
  COALESCE(NULLIF(branch_name,''), '(없음)') AS branch,
  COUNT(*) AS posts
FROM blog_posts
{BASE_WHERE}
GROUP BY branch
ORDER BY posts DESC
LIMIT 30
""")

# 4. branch_name × blog_channel 교차표 (TOP 15 지점만)
section("4. 지점 × 채널 교차표 (TOP 15 지점)")
run(f"""
WITH top_branches AS (
  SELECT branch_name
  FROM blog_posts
  {BASE_WHERE}
    AND branch_name IS NOT NULL AND branch_name <> ''
  GROUP BY branch_name
  ORDER BY COUNT(*) DESC
  LIMIT 15
)
SELECT
  bp.branch_name AS 지점,
  SUM(CASE WHEN bp.blog_channel = 'br' THEN 1 ELSE 0 END) AS 브랜드,
  SUM(CASE WHEN bp.blog_channel = 'opt' THEN 1 ELSE 0 END) AS 최적,
  SUM(CASE WHEN bp.blog_channel IS NULL OR bp.blog_channel = '' THEN 1 ELSE 0 END) AS 미분류,
  COUNT(*) AS 합계
FROM blog_posts bp
JOIN top_branches tb ON tb.branch_name = bp.branch_name
{BASE_WHERE.replace("WHERE", "AND")}
GROUP BY bp.branch_name
ORDER BY 합계 DESC
""")

# 5. blog_channel 미분류 행 샘플 (있다면)
section("5. blog_channel 미분류 행 샘플 5건")
run(f"""
SELECT
  keyword,
  blog_id,
  post_type,
  branch_name,
  published_at
FROM blog_posts
{BASE_WHERE}
  AND (blog_channel IS NULL OR blog_channel = '')
ORDER BY published_at DESC
LIMIT 5
""")

# 6. 미리보기: 추가 컬럼 포함 샘플 10건
section("6. 신규 양식 미리보기 (순번|키워드|블로그계정|글번호|발행일|채널|지점|제목) 10건")
run(f"""
SELECT
  ROW_NUMBER() OVER (ORDER BY published_at DESC, id DESC) AS 순번,
  keyword AS 키워드,
  blog_id AS 블로그계정,
  post_number AS 글번호,
  published_at AS 발행일,
  CASE
    WHEN blog_channel = 'br' THEN '브랜드'
    WHEN blog_channel = 'opt' THEN '최적'
    ELSE '(미분류)'
  END AS 채널,
  COALESCE(NULLIF(branch_name,''), '(없음)') AS 지점,
  substr(COALESCE(NULLIF(clean_title,''), NULLIF(title,''), NULLIF(scraped_title,'')), 1, 30) AS 제목
FROM blog_posts
{BASE_WHERE}
ORDER BY published_at DESC, id DESC
LIMIT 10
""")

conn.close()

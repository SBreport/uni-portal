"""
블로그 키워드 추적용 DB 추출 진단 스크립트
- 추출 양식: 순번 | 키워드 | 블로그계정 | 발행일 | 제목
- 데이터 품질, 누락, 중복, 분포를 점검
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

# 1. 전체 건수
section("1. 전체 건수")
run("SELECT COUNT(*) AS total FROM blog_posts")

# 2. 필수 컬럼 채움률
section("2. 필수 컬럼 채움률 (키워드 추적에 필요한 5개)")
run("""
SELECT
  COUNT(*)                                                                 AS total,
  SUM(CASE WHEN keyword       IS NOT NULL AND keyword       <> '' THEN 1 ELSE 0 END) AS has_keyword,
  SUM(CASE WHEN blog_id       IS NOT NULL AND blog_id       <> '' THEN 1 ELSE 0 END) AS has_blog_id,
  SUM(CASE WHEN post_number   IS NOT NULL AND post_number   <> '' THEN 1 ELSE 0 END) AS has_post_number,
  SUM(CASE WHEN published_at  IS NOT NULL AND published_at  <> '' THEN 1 ELSE 0 END) AS has_published_at,
  SUM(CASE WHEN COALESCE(NULLIF(clean_title,''), NULLIF(title,''), NULLIF(scraped_title,'')) IS NOT NULL THEN 1 ELSE 0 END) AS has_title
FROM blog_posts
""")

# 3. 키워드 추적에 즉시 쓸 수 있는 "완전한" 행 수
section("3. 즉시 추출 가능한 완전 데이터 (5개 필수 모두 채워진 행)")
run("""
SELECT COUNT(*) AS ready_rows
FROM blog_posts
WHERE keyword IS NOT NULL AND keyword <> ''
  AND blog_id IS NOT NULL AND blog_id <> ''
  AND post_number IS NOT NULL AND post_number <> ''
  AND published_at IS NOT NULL AND published_at <> ''
  AND COALESCE(NULLIF(clean_title,''), NULLIF(title,''), NULLIF(scraped_title,'')) IS NOT NULL
""")

# 4. 플랫폼별 분포
section("4. 플랫폼별 분포 (네이버 블로그/카페)")
run("""
SELECT
  COALESCE(platform, '(없음)') AS platform,
  COUNT(*) AS cnt
FROM blog_posts
GROUP BY platform
ORDER BY cnt DESC
""")

# 5. 키워드 있는 데이터의 발행 연도 분포
section("5. 키워드 있는 데이터의 발행연도 분포")
run("""
SELECT
  substr(published_at, 1, 4) AS year,
  COUNT(*) AS cnt
FROM blog_posts
WHERE keyword IS NOT NULL AND keyword <> ''
  AND published_at IS NOT NULL AND published_at <> ''
GROUP BY year
ORDER BY year DESC
""")

# 6. 키워드 고유 개수 (얼마나 다양한 키워드를 추적해야 하나)
section("6. 키워드 다양성")
run("""
SELECT
  COUNT(*) AS rows_with_keyword,
  COUNT(DISTINCT keyword) AS unique_keywords
FROM blog_posts
WHERE keyword IS NOT NULL AND keyword <> ''
""")

# 7. 키워드 + 블로그계정 조합 (실제 순위 측정 단위)
section("7. (키워드 × 블로그ID) 고유 조합 수 = 실제 순위 측정 단위 수")
run("""
SELECT COUNT(*) AS unique_keyword_blog_pairs
FROM (
  SELECT DISTINCT keyword, blog_id
  FROM blog_posts
  WHERE keyword IS NOT NULL AND keyword <> ''
    AND blog_id IS NOT NULL AND blog_id <> ''
)
""")

# 8. 상위 키워드 (가장 많이 발행된 키워드 TOP 20)
section("8. TOP 20 키워드 (발행 빈도)")
run("""
SELECT
  keyword,
  COUNT(*) AS posts,
  COUNT(DISTINCT blog_id) AS blog_accounts
FROM blog_posts
WHERE keyword IS NOT NULL AND keyword <> ''
GROUP BY keyword
ORDER BY posts DESC
LIMIT 20
""")

# 9. 상위 블로그 계정
section("9. TOP 10 블로그 계정 (발행 빈도)")
run("""
SELECT
  blog_id,
  COUNT(*) AS posts,
  COUNT(DISTINCT keyword) AS keywords
FROM blog_posts
WHERE blog_id IS NOT NULL AND blog_id <> ''
GROUP BY blog_id
ORDER BY posts DESC
LIMIT 10
""")

# 10. 추출 샘플 (요청한 양식 그대로 10건)
section("10. 추출 샘플 — 요청 양식 (순번 | 키워드 | 블로그계정 | 발행일 | 제목) 최신 10건")
run("""
SELECT
  ROW_NUMBER() OVER (ORDER BY published_at DESC, id DESC) AS 순번,
  keyword AS 키워드,
  blog_id AS 블로그계정,
  published_at AS 발행일,
  substr(COALESCE(NULLIF(clean_title,''), NULLIF(title,''), NULLIF(scraped_title,'')), 1, 40) AS 제목
FROM blog_posts
WHERE keyword IS NOT NULL AND keyword <> ''
  AND blog_id IS NOT NULL AND blog_id <> ''
  AND published_at IS NOT NULL AND published_at <> ''
ORDER BY published_at DESC, id DESC
LIMIT 10
""")

# 11. 빠진 데이터 — 누락 원인 분포
section("11. 키워드 없는 행의 원인 (글 종류 분포)")
run("""
SELECT
  COALESCE(NULLIF(post_type_main, ''), '(없음)') AS post_type_main,
  COUNT(*) AS cnt
FROM blog_posts
WHERE keyword IS NULL OR keyword = ''
GROUP BY post_type_main
ORDER BY cnt DESC
LIMIT 10
""")

conn.close()

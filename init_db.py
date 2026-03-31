"""
SQLite DB 초기화 스크립트
- equipment.db 생성
- 테이블 스키마 정의
- 실행: python init_db.py
"""

import sqlite3
import os

DB_DIR = os.path.join(os.path.dirname(__file__), "data")
DB_PATH = os.path.join(DB_DIR, "equipment.db")


def init_db():
    os.makedirs(DB_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # 지점 테이블
    c.execute("""
    CREATE TABLE IF NOT EXISTS branches (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        name        TEXT UNIQUE NOT NULL,
        created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 카테고리 테이블
    c.execute("""
    CREATE TABLE IF NOT EXISTS categories (
        id    INTEGER PRIMARY KEY AUTOINCREMENT,
        name  TEXT UNIQUE NOT NULL
    )
    """)

    # 장비 테이블 (핵심)
    c.execute("""
    CREATE TABLE IF NOT EXISTS equipment (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        branch_id     INTEGER NOT NULL REFERENCES branches(id),
        category_id   INTEGER NOT NULL REFERENCES categories(id),
        name          TEXT NOT NULL,
        name_original TEXT,
        quantity      INTEGER DEFAULT 1,
        photo_status  BOOLEAN DEFAULT 0,
        note          TEXT DEFAULT '',
        source        TEXT DEFAULT 'sheets',
        created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 사용자 테이블
    c.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        username      TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role          TEXT DEFAULT 'viewer',
        branch_id     INTEGER REFERENCES branches(id),
        memo          TEXT DEFAULT '',
        created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 동기화 로그 테이블
    c.execute("""
    CREATE TABLE IF NOT EXISTS sync_log (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        sync_type   TEXT NOT NULL,
        added       INTEGER DEFAULT 0,
        skipped     INTEGER DEFAULT 0,
        conflicts   INTEGER DEFAULT 0,
        detail      TEXT,
        synced_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 장비 인덱스
    c.execute("CREATE INDEX IF NOT EXISTS idx_equipment_branch ON equipment(branch_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_equipment_category ON equipment(category_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_equipment_name ON equipment(name)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_users_branch ON users(branch_id)")

    # ============================================================
    # 이벤트 테이블 (evt_ 접두사 — 장비 테이블과 분리)
    # ============================================================

    # 이벤트 지역 (서울/경기/인천/지방)
    c.execute("""
    CREATE TABLE IF NOT EXISTS evt_regions (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        name        TEXT NOT NULL UNIQUE,
        sort_order  INTEGER DEFAULT 0
    )
    """)

    # 이벤트 지점 (43개 — 시트 탭 매칭용 short_name 포함)
    c.execute("""
    CREATE TABLE IF NOT EXISTS evt_branches (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        region_id   INTEGER NOT NULL REFERENCES evt_regions(id),
        name        TEXT NOT NULL UNIQUE,
        short_name  TEXT,
        is_active   INTEGER DEFAULT 1,
        created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 이벤트 기간 (2개월 단위: 3~4월, 5~6월 등)
    c.execute("""
    CREATE TABLE IF NOT EXISTS evt_periods (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        year        INTEGER NOT NULL,
        start_month INTEGER NOT NULL,
        end_month   INTEGER NOT NULL,
        label       TEXT NOT NULL,
        source_url  TEXT,
        starts_at   TEXT NOT NULL,
        ends_at     TEXT NOT NULL,
        is_current  INTEGER DEFAULT 0,
        ingested_at TIMESTAMP,
        created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(year, start_month)
    )
    """)

    # 이벤트 시술 카테고리 (보톡스/필러/레이저리프팅 등)
    c.execute("""
    CREATE TABLE IF NOT EXISTS evt_categories (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        name         TEXT NOT NULL UNIQUE,
        display_name TEXT,
        sort_order   INTEGER DEFAULT 0,
        is_active    INTEGER DEFAULT 1
    )
    """)

    # 카테고리 별명 매핑 (비표준 시트 카테고리명 → 표준)
    c.execute("""
    CREATE TABLE IF NOT EXISTS evt_category_aliases (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        category_id INTEGER NOT NULL REFERENCES evt_categories(id) ON DELETE CASCADE,
        alias       TEXT NOT NULL,
        branch_id   INTEGER REFERENCES evt_branches(id) ON DELETE SET NULL
    )
    """)

    # 시술 마스터 (개별 시술/브랜드 + 설명 사전)
    c.execute("""
    CREATE TABLE IF NOT EXISTS evt_treatments (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        category_id INTEGER REFERENCES evt_categories(id),
        name        TEXT NOT NULL,
        brand       TEXT,
        description TEXT,
        is_verified INTEGER DEFAULT 0,
        is_active   INTEGER DEFAULT 1,
        created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 이벤트 상품 (핵심 팩트 테이블)
    c.execute("""
    CREATE TABLE IF NOT EXISTS evt_items (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        event_period_id  INTEGER NOT NULL REFERENCES evt_periods(id) ON DELETE CASCADE,
        branch_id        INTEGER NOT NULL REFERENCES evt_branches(id) ON DELETE CASCADE,
        category_id      INTEGER NOT NULL REFERENCES evt_categories(id),
        raw_event_name   TEXT NOT NULL,
        raw_category     TEXT,
        display_name     TEXT,
        session_count    INTEGER,
        session_unit     TEXT DEFAULT '회',
        is_package       INTEGER DEFAULT 0,
        regular_price    INTEGER,
        event_price      INTEGER,
        discount_rate    REAL,
        notes            TEXT,
        row_order        INTEGER,
        is_active        INTEGER DEFAULT 1,
        created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 패키지 구성요소 (이벤트 상품 → 개별 시술 분해)
    c.execute("""
    CREATE TABLE IF NOT EXISTS evt_item_components (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        event_item_id   INTEGER NOT NULL REFERENCES evt_items(id) ON DELETE CASCADE,
        treatment_id    INTEGER REFERENCES evt_treatments(id) ON DELETE SET NULL,
        raw_component   TEXT,
        dosage          TEXT,
        session_count   INTEGER,
        component_order INTEGER DEFAULT 0
    )
    """)

    # 이벤트 수집 로그
    c.execute("""
    CREATE TABLE IF NOT EXISTS evt_ingestion_logs (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        event_period_id  INTEGER NOT NULL REFERENCES evt_periods(id),
        status           TEXT NOT NULL DEFAULT 'started',
        total_branches   INTEGER,
        total_items      INTEGER,
        error_log        TEXT,
        started_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        completed_at     TIMESTAMP
    )
    """)

    # ============================================================
    # 시술/장비 기초 정보 사전 (device_info)
    # ============================================================
    c.execute("""
    CREATE TABLE IF NOT EXISTS device_info (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        name        TEXT NOT NULL UNIQUE,
        category    TEXT DEFAULT '',
        summary     TEXT DEFAULT '',
        target      TEXT DEFAULT '',
        mechanism   TEXT DEFAULT '',
        note        TEXT DEFAULT '',
        aliases     TEXT DEFAULT '',
        usage_count INTEGER DEFAULT 0,
        is_verified INTEGER DEFAULT 0,
        created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    c.execute("CREATE INDEX IF NOT EXISTS idx_device_info_name ON device_info(name)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_device_info_category ON device_info(category)")

    # 이벤트 인덱스
    c.execute("CREATE INDEX IF NOT EXISTS idx_evt_branches_region ON evt_branches(region_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_evt_items_period_branch ON evt_items(event_period_id, branch_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_evt_items_branch_cat ON evt_items(branch_id, category_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_evt_items_cat_period ON evt_items(category_id, event_period_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_evt_items_price ON evt_items(event_price)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_evt_components_item ON evt_item_components(event_item_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_evt_components_treat ON evt_item_components(treatment_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_evt_treatments_name ON evt_treatments(name)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_evt_cat_aliases_alias ON evt_category_aliases(alias)")

    # ============================================================
    # 카페 마케팅 테이블 (cafe_ 접두사)
    # ============================================================

    # 카페 원고 기간 (월 단위)
    c.execute("""
    CREATE TABLE IF NOT EXISTS cafe_periods (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        year        INTEGER NOT NULL,
        month       INTEGER NOT NULL,
        label       TEXT NOT NULL,
        source_url  TEXT,
        is_current  INTEGER DEFAULT 0,
        created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(year, month)
    )
    """)

    # 카페 지점-월 메타데이터 (담당자, 발행건수 등)
    c.execute("""
    CREATE TABLE IF NOT EXISTS cafe_branch_periods (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        cafe_period_id      INTEGER NOT NULL REFERENCES cafe_periods(id) ON DELETE CASCADE,
        branch_id           INTEGER NOT NULL REFERENCES evt_branches(id),
        smart_manager       TEXT DEFAULT '',
        writer              TEXT DEFAULT '',
        publisher           TEXT DEFAULT '',
        publish_count       INTEGER DEFAULT 0,
        review_count        INTEGER DEFAULT 0,
        superset_count      INTEGER DEFAULT 0,
        self_made           TEXT DEFAULT '',
        report_link         TEXT DEFAULT '',
        comment_link        TEXT DEFAULT '',
        photo_link          TEXT DEFAULT '',
        general_photo_link  TEXT DEFAULT '',
        progress_note       TEXT DEFAULT '',
        created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(cafe_period_id, branch_id)
    )
    """)

    # 카페 원고 (월 20건)
    c.execute("""
    CREATE TABLE IF NOT EXISTS cafe_articles (
        id                  INTEGER PRIMARY KEY AUTOINCREMENT,
        branch_period_id    INTEGER NOT NULL REFERENCES cafe_branch_periods(id) ON DELETE CASCADE,
        article_order       INTEGER NOT NULL,
        keyword             TEXT DEFAULT '',
        category            TEXT DEFAULT '',
        equipment_name      TEXT DEFAULT '',
        photo_ref           TEXT DEFAULT '',
        title               TEXT DEFAULT '',
        body                TEXT DEFAULT '',
        status              TEXT DEFAULT '작성대기',
        published_url       TEXT DEFAULT '',
        published_at        TIMESTAMP,
        published_by        TEXT DEFAULT '',
        status_updated_at   TIMESTAMP,
        created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 카페 원고 댓글/대댓글 (원고당 3슬롯)
    c.execute("""
    CREATE TABLE IF NOT EXISTS cafe_comments (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        article_id      INTEGER NOT NULL REFERENCES cafe_articles(id) ON DELETE CASCADE,
        slot_number     INTEGER NOT NULL CHECK(slot_number BETWEEN 1 AND 3),
        comment_text    TEXT DEFAULT '',
        reply_text      TEXT DEFAULT '',
        created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(article_id, slot_number)
    )
    """)

    # 카페 원고 피드백 (이력 누적)
    c.execute("""
    CREATE TABLE IF NOT EXISTS cafe_feedbacks (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        article_id  INTEGER NOT NULL REFERENCES cafe_articles(id) ON DELETE CASCADE,
        author      TEXT NOT NULL,
        content     TEXT NOT NULL,
        created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 카페 원고 상태 변경 이력
    c.execute("""
    CREATE TABLE IF NOT EXISTS cafe_status_log (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        article_id  INTEGER NOT NULL REFERENCES cafe_articles(id) ON DELETE CASCADE,
        old_status  TEXT NOT NULL,
        new_status  TEXT NOT NULL,
        changed_by  TEXT DEFAULT '',
        note        TEXT DEFAULT '',
        changed_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 카페 동기화 로그
    c.execute("""
    CREATE TABLE IF NOT EXISTS cafe_sync_log (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        cafe_period_id  INTEGER NOT NULL REFERENCES cafe_periods(id),
        status          TEXT NOT NULL DEFAULT 'started',
        total_branches  INTEGER DEFAULT 0,
        total_articles  INTEGER DEFAULT 0,
        error_log       TEXT,
        started_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        completed_at    TIMESTAMP
    )
    """)

    # 카페 인덱스
    c.execute("CREATE INDEX IF NOT EXISTS idx_cafe_bp_period ON cafe_branch_periods(cafe_period_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_cafe_bp_branch ON cafe_branch_periods(branch_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_cafe_articles_bp ON cafe_articles(branch_period_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_cafe_articles_status ON cafe_articles(status)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_cafe_comments_article ON cafe_comments(article_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_cafe_feedbacks_article ON cafe_feedbacks(article_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_cafe_status_log_article ON cafe_status_log(article_id)")

    # ============================================================
    # 논문/연구 자료 테이블 (papers)
    # ============================================================

    # 논문 메타 + AI 요약
    c.execute("""
    CREATE TABLE IF NOT EXISTS papers (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        device_info_id  INTEGER REFERENCES device_info(id) ON DELETE SET NULL,
        treatment_id    INTEGER REFERENCES evt_treatments(id) ON DELETE SET NULL,
        doi             TEXT DEFAULT '',
        title           TEXT NOT NULL,
        title_ko        TEXT DEFAULT '',
        authors         TEXT DEFAULT '',
        journal         TEXT DEFAULT '',
        pub_year        INTEGER,
        pub_date        TEXT DEFAULT '',
        abstract_summary TEXT DEFAULT '',
        key_findings    TEXT DEFAULT '',
        keywords        TEXT DEFAULT '[]',
        evidence_level  INTEGER DEFAULT 0,
        study_type      TEXT DEFAULT '',
        sample_size     TEXT DEFAULT '',
        source_url      TEXT DEFAULT '',
        source_file     TEXT DEFAULT '',
        status          TEXT DEFAULT 'draft',
        one_line_summary    TEXT DEFAULT '',
        research_purpose    TEXT DEFAULT '',
        study_design_detail TEXT DEFAULT '',
        key_results         TEXT DEFAULT '',
        conclusion          TEXT DEFAULT '',
        quotable_stats      TEXT DEFAULT '[]',
        cautions            TEXT DEFAULT '',
        follow_up_period    TEXT DEFAULT '',
        photo_restriction   TEXT DEFAULT '',
        created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    c.execute("CREATE INDEX IF NOT EXISTS idx_papers_device ON papers(device_info_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_papers_treatment ON papers(treatment_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_papers_year ON papers(pub_year)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_papers_status ON papers(status)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_papers_doi ON papers(doi)")

    # ── 블로그 게시글 테이블 ──
    c.execute("""
    CREATE TABLE IF NOT EXISTS blog_posts (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        content_number  TEXT DEFAULT '',
        title           TEXT DEFAULT '',
        keyword         TEXT DEFAULT '',
        tags            TEXT DEFAULT '',
        post_type       TEXT DEFAULT '',
        blog_channel    TEXT DEFAULT 'br',
        blog_id         TEXT DEFAULT '',
        post_number     TEXT DEFAULT '',
        platform        TEXT DEFAULT 'blog',
        published_url   TEXT DEFAULT '',
        backup_url      TEXT DEFAULT '',
        author          TEXT DEFAULT '',
        published_at    TEXT DEFAULT '',
        deadline_at     TEXT DEFAULT '',
        status          TEXT DEFAULT '',
        project         TEXT DEFAULT '',
        exposure_rank   TEXT DEFAULT '',
        note            TEXT DEFAULT '',
        created_at      TEXT DEFAULT (datetime('now','localtime')),
        updated_at      TEXT DEFAULT (datetime('now','localtime')),
        UNIQUE(platform, blog_id, post_number)
    )
    """)
    c.execute("CREATE INDEX IF NOT EXISTS idx_blog_posts_channel ON blog_posts(blog_channel)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_blog_posts_type ON blog_posts(post_type)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_blog_posts_blog_id ON blog_posts(blog_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_blog_posts_published ON blog_posts(published_at)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_blog_posts_keyword ON blog_posts(keyword)")

    # ── blog_posts 가공 컬럼 마이그레이션 ──
    _blog_enrich_cols = [
        ("branch_name", "TEXT DEFAULT ''"),
        ("slot_number", "TEXT DEFAULT ''"),
        ("post_type_main", "TEXT DEFAULT ''"),
        ("post_type_sub", "TEXT DEFAULT ''"),
        ("project_month", "TEXT DEFAULT ''"),
        ("project_branch", "TEXT DEFAULT ''"),
        ("status_clean", "TEXT DEFAULT ''"),
        ("clean_title", "TEXT DEFAULT ''"),
        ("author_main", "TEXT DEFAULT ''"),
        ("author_sub", "TEXT DEFAULT ''"),
        ("needs_review", "INTEGER DEFAULT 0"),
        ("scraped_title", "TEXT DEFAULT ''"),
    ]
    for col_name, col_def in _blog_enrich_cols:
        try:
            c.execute(f"ALTER TABLE blog_posts ADD COLUMN {col_name} {col_def}")
        except Exception:
            pass  # 이미 존재
    c.execute("CREATE INDEX IF NOT EXISTS idx_blog_posts_branch ON blog_posts(branch_name)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_blog_posts_type_main ON blog_posts(post_type_main)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_blog_posts_project_month ON blog_posts(project_month)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_blog_posts_author_main ON blog_posts(author_main)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_blog_posts_needs_review ON blog_posts(needs_review)")

    # ── 블로그 계정 매핑 테이블 ──
    c.execute("""
    CREATE TABLE IF NOT EXISTS blog_accounts (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        blog_id         TEXT UNIQUE NOT NULL,
        account_name    TEXT DEFAULT '',
        account_group   TEXT DEFAULT '',
        channel         TEXT DEFAULT '',
        note            TEXT DEFAULT '',
        blog_nickname   TEXT DEFAULT '',
        blog_title      TEXT DEFAULT '',
        created_at      TEXT DEFAULT (datetime('now','localtime'))
    )
    """)
    c.execute("CREATE INDEX IF NOT EXISTS idx_blog_accounts_channel ON blog_accounts(channel)")

    # blog_accounts 컬럼 마이그레이션 (기존 DB에 컬럼이 없는 경우)
    existing_cols = {row[1] for row in c.execute("PRAGMA table_info(blog_accounts)").fetchall()}
    for col_name in ["blog_nickname", "blog_title"]:
        if col_name not in existing_cols:
            c.execute(f"ALTER TABLE blog_accounts ADD COLUMN {col_name} TEXT DEFAULT ''")

    # ── 블로그 CSV 동기화 로그 ──
    c.execute("""
    CREATE TABLE IF NOT EXISTS blog_sync_log (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        filename        TEXT NOT NULL,
        csv_modified_at TEXT NOT NULL,
        total_rows      INTEGER DEFAULT 0,
        imported_rows   INTEGER DEFAULT 0,
        skipped_rows    INTEGER DEFAULT 0,
        blog_channel    TEXT DEFAULT '',
        imported_at     TEXT DEFAULT (datetime('now','localtime'))
    )
    """)

    # ── Notion 동기화 로그 ──
    c.execute("""
    CREATE TABLE IF NOT EXISTS notion_sync_log (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        sync_type       TEXT NOT NULL DEFAULT 'incremental',
        notion_pages    INTEGER DEFAULT 0,
        matched         INTEGER DEFAULT 0,
        updated         INTEGER DEFAULT 0,
        new_posts       INTEGER DEFAULT 0,
        last_edited_cutoff TEXT DEFAULT '',
        synced_at       TEXT DEFAULT (datetime('now','localtime'))
    )
    """)

    # ── 논문-블로그 연동 테이블 ──
    c.execute("""
    CREATE TABLE IF NOT EXISTS paper_blog_links (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        paper_id     INTEGER NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
        blog_post_id INTEGER REFERENCES blog_posts(id) ON DELETE SET NULL,
        blog_url     TEXT NOT NULL DEFAULT '',
        blog_title   TEXT NOT NULL DEFAULT '',
        link_type    TEXT NOT NULL DEFAULT 'reference',
        note         TEXT DEFAULT '',
        created_at   TEXT DEFAULT (datetime('now','localtime')),
        UNIQUE(paper_id, blog_url)
    )
    """)
    c.execute("CREATE INDEX IF NOT EXISTS idx_paper_blog_paper ON paper_blog_links(paper_id)")
    # blog_post_id 컬럼 마이그레이션 (기존 테이블에 없을 수 있음)
    try:
        c.execute("ALTER TABLE paper_blog_links ADD COLUMN blog_post_id INTEGER REFERENCES blog_posts(id) ON DELETE SET NULL")
    except Exception:
        pass  # 이미 존재
    c.execute("CREATE INDEX IF NOT EXISTS idx_paper_blog_post ON paper_blog_links(blog_post_id)")

    # 논문-장비 다대다 연결 테이블
    c.execute("""
    CREATE TABLE IF NOT EXISTS paper_devices (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        paper_id        INTEGER NOT NULL REFERENCES papers(id) ON DELETE CASCADE,
        device_info_id  INTEGER NOT NULL REFERENCES device_info(id) ON DELETE CASCADE,
        match_type      TEXT NOT NULL DEFAULT 'direct',
        match_keyword   TEXT DEFAULT '',
        is_verified     INTEGER DEFAULT 0,
        created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(paper_id, device_info_id)
    )
    """)
    c.execute("CREATE INDEX IF NOT EXISTS idx_paper_devices_paper ON paper_devices(paper_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_paper_devices_device ON paper_devices(device_info_id)")

    # ── 앱 설정 (key-value) ──
    c.execute("""
    CREATE TABLE IF NOT EXISTS app_settings (
        key         TEXT PRIMARY KEY,
        value       TEXT NOT NULL DEFAULT '',
        updated_at  TEXT DEFAULT (datetime('now','localtime'))
    )
    """)

    # ============================================================
    # 마이그레이션: 기존 DB에 새 컬럼 추가 (이미 있으면 무시)
    # ============================================================
    migrations = [
        ("papers", "one_line_summary", "TEXT DEFAULT ''"),
        ("papers", "research_purpose", "TEXT DEFAULT ''"),
        ("papers", "study_design_detail", "TEXT DEFAULT ''"),
        ("papers", "key_results", "TEXT DEFAULT ''"),
        ("papers", "conclusion", "TEXT DEFAULT ''"),
        ("papers", "quotable_stats", "TEXT DEFAULT '[]'"),
        ("papers", "cautions", "TEXT DEFAULT ''"),
        ("papers", "follow_up_period", "TEXT DEFAULT ''"),
        ("papers", "photo_restriction", "TEXT DEFAULT ''"),
        ("papers", "file_hash", "TEXT DEFAULT ''"),
        ("papers", "easy_summary", "TEXT DEFAULT ''"),
    ]
    for table, col, col_type in migrations:
        try:
            c.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}")
        except Exception:
            pass  # 이미 존재

    conn.commit()

    # ============================================================
    # Seed 데이터 (이벤트)
    # ============================================================
    _seed_event_data(conn)

    conn.close()
    print(f"DB 생성 완료: {DB_PATH}")

    # 테이블 확인
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = c.fetchall()
    print(f"생성된 테이블: {[t[0] for t in tables]}")
    conn.close()


def _seed_event_data(conn):
    """이벤트 지역/지점/카테고리/별명 초기 데이터 삽입"""
    c = conn.cursor()

    # 이미 데이터가 있으면 스킵
    c.execute("SELECT COUNT(*) FROM evt_regions")
    if c.fetchone()[0] > 0:
        return

    # 지역 (4개)
    regions = [("서울", 1), ("경기", 2), ("인천", 3), ("지방", 4)]
    c.executemany("INSERT INTO evt_regions (name, sort_order) VALUES (?, ?)", regions)

    # 지점 (43개)
    branches_data = {
        "서울": [
            ("강남점", "강남"), ("건대점", "건대"), ("명동점", "명동"), ("목동점", "목동"),
            ("선릉점", "선릉"), ("잠실점", "잠실"), ("창동점", "창동"), ("천호점", "천호"),
            ("왕십리점", "왕십리"), ("여의도점", "여의도"), ("영등포점", "영등포"), ("홍대점", "홍대"),
        ],
        "경기": [
            ("경기광주점", "경기광주"), ("과천점", "과천"), ("광교점", "광교"), ("광명점", "광명"),
            ("구로점", "구로"), ("김포점", "김포"), ("다산점", "다산"), ("동탄점", "동탄"),
            ("마곡점", "마곡"), ("분당미금점", "분당미금"), ("산본점", "산본"), ("수원점", "수원"),
            ("시흥배곧점", "시흥배곧"), ("의정부점", "의정부"), ("안산점", "안산"), ("안양점", "안양"),
            ("판교점", "판교"), ("평택점", "평택"), ("하남미사점", "하남미사"),
            ("화성봉담점", "화성봉담"), ("일산점", "일산"),
        ],
        "인천": [
            ("인천검단점", "인천검단"), ("부천점", "부천"), ("부평점", "부평"),
        ],
        "지방": [
            ("대구점", "대구"), ("대전점", "대전"), ("광주점", "광주"), ("부산점", "부산"),
            ("목포점", "목포"), ("창원점", "창원"), ("천안점", "천안"),
        ],
    }
    for region_name, branch_list in branches_data.items():
        c.execute("SELECT id FROM evt_regions WHERE name = ?", (region_name,))
        region_id = c.fetchone()[0]
        for name, short_name in branch_list:
            c.execute(
                "INSERT INTO evt_branches (region_id, name, short_name) VALUES (?, ?, ?)",
                (region_id, name, short_name),
            )

    # 시술 카테고리 (16종)
    categories = [
        ("단독이벤트", "단독이벤트", 1),
        ("레이저리프팅", "레이저리프팅", 2),
        ("실리프팅", "실리프팅", 3),
        ("보톡스", "보톡스", 4),
        ("필러", "필러", 5),
        ("색소", "색소/기미/잡티", 6),
        ("스킨케어", "스킨케어", 7),
        ("스킨부스터", "스킨부스터", 8),
        ("여드름", "여드름/모공", 9),
        ("제모", "제모", 10),
        ("비만", "비만/체형", 11),
        ("활력주사", "활력주사", 12),
        ("윤곽", "윤곽주사", 13),
        ("첫방문이벤트", "첫방문이벤트", 14),
        ("요일이벤트", "요일한정이벤트", 15),
        ("기타", "기타", 99),
    ]
    c.executemany(
        "INSERT INTO evt_categories (name, display_name, sort_order) VALUES (?, ?, ?)",
        categories,
    )

    # 카테고리 별명 매핑
    aliases = [
        ("레이저리프팅", "레이저리프팅 / 울써마지 외에 선티켓팅 가능"),
        ("레이저리프팅", "레이져리프팅"),
        ("보톡스", "쁘띠 / 아쎄라 선티켓팅 가능 외에 당일소진"),
        ("보톡스", "보톡스 / 윤곽 > 보툴리눔 톡신으로 노출"),
        ("보톡스", "보톡스 / 윤곽"),
        ("색소", "색소 선티켓팅 가능"),
        ("색소", "기미 / 잡티 / 홍조"),
        ("여드름", "여드름 선티켓팅가능"),
        ("여드름", "여드름 / 모공"),
        ("제모", "제모 선티켓팅 가능"),
        ("비만", "비만 (선티켓팅 가능)"),
        ("첫방문이벤트", "첫방문 이벤트"),
        ("요일이벤트", "화수목 이벤트(원장님 지정 불가 / 1회 한정)"),
    ]
    for cat_name, alias in aliases:
        c.execute("SELECT id FROM evt_categories WHERE name = ?", (cat_name,))
        row = c.fetchone()
        if row:
            c.execute(
                "INSERT INTO evt_category_aliases (category_id, alias) VALUES (?, ?)",
                (row[0], alias),
            )

    conn.commit()
    print("이벤트 seed 데이터 삽입 완료")

    # 시술 사전 시드 데이터
    _seed_treatment_dictionary(conn)


def _seed_treatment_dictionary(conn):
    """미용의료 시술 기초 사전 (60+개) — 관리자 검수 전 is_verified=0"""
    c = conn.cursor()

    # 이미 사전 데이터가 있으면 스킵
    c.execute("SELECT COUNT(*) FROM evt_treatments WHERE description IS NOT NULL")
    if c.fetchone()[0] > 0:
        return

    # 카테고리 ID 매핑 (name → id)
    c.execute("SELECT id, name FROM evt_categories")
    cat_map = {row[1]: row[0] for row in c.fetchall()}

    # (카테고리명, 시술명, 브랜드, 설명)
    treatments = [
        # ── 보톡스 ──
        ("보톡스", "보톡스", "앨러간", "미국 앨러간사 보툴리눔 톡신. 주름 개선, 사각턱 축소, 다한증 치료에 사용"),
        ("보톡스", "디스포트", "입센", "영국 입센사 보툴리눔 톡신. 보톡스 대비 확산 범위가 넓어 넓은 부위에 적합"),
        ("보톡스", "제오민", "멀츠", "독일 멀츠사 보톡스. 순수 톡신으로 항체 생성 위험이 낮음"),
        ("보톡스", "보툴렉스", "휴젤", "국산 보툴리눔 톡신. 앨러간 보톡스와 동일 기전, 가격 경쟁력 보유"),
        ("보톡스", "나보타", "대웅제약", "국산 보툴리눔 톡신. FDA 승인(제시), 주름·사각턱에 사용"),
        ("보톡스", "코어톡스", "메디톡스", "국산 보툴리눔 톡신. 상온 보관 가능한 제품 특성"),
        ("보톡스", "리즈톡스", "휴온스", "국산 보툴리눔 톡신. 주름, 사각턱, 종아리 축소에 사용"),
        ("보톡스", "엑스민", "휴메딕스", "국산 보툴리눔 톡신. 미간·눈가 주름 개선 목적"),

        # ── 필러 ──
        ("필러", "쥬비덤", "앨러간", "미국 앨러간사 HA 필러. 바이크로스 기술로 자연스러운 볼륨감 제공"),
        ("필러", "레스틸렌", "갈더마", "스웨덴 갈더마사 HA 필러. NASHA 기술 기반, 입술·볼·턱 볼륨"),
        ("필러", "벨로테로", "멀츠", "독일 멀츠사 HA 필러. CPM 기술로 균일한 분포, 잔주름에 적합"),
        ("필러", "엘란세", "시넥론", "네덜란드산 PCL 콜라겐 자극 필러. 즉각적 볼륨 + 콜라겐 재생"),
        ("필러", "에네필", "LG화학", "국산 HA 필러. 무분별 가교 결합 기술로 자연스러운 결과"),
        ("필러", "이브아르", "LG화학", "국산 HA 필러. 균일 입자 크기, 코·턱·볼 성형에 사용"),

        # ── 레이저리프팅 ──
        ("레이저리프팅", "울쎄라", "멀츠", "미국 FDA 승인 HIFU 리프팅. 초음파로 SMAS층 직접 자극하여 탄력 개선"),
        ("레이저리프팅", "슈링크", "클래시스", "국산 HIFU 리프팅. 울쎄라 대비 통증이 적고 시술 시간이 짧음"),
        ("레이저리프팅", "써마지", "솔타메디컬", "고주파(RF) 리프팅. 콜라겐 수축·재생으로 피부 탄력 개선"),
        ("레이저리프팅", "인모드", "인모드", "RF 기반 복합 리프팅. FX·미니FX·포마V 등 다양한 모드 제공"),
        ("레이저리프팅", "올리지오", "엘리안", "국산 고주파 리프팅. 써마지와 유사한 RF 방식, 가격 경쟁력"),
        ("레이저리프팅", "볼뉴머", "비비안메디", "고주파+진공 흡입 리프팅. 셀룰라이트·바디 탄력 개선에 특화"),
        ("레이저리프팅", "포텐자", "사이노슈어", "RF 마이크로니들링. 니들 깊이 조절로 모공·흉터·탄력 동시 개선"),
        ("레이저리프팅", "텐써마", "루트로닉", "국산 써마지급 고주파. 대면적 팁으로 효율적 시술"),

        # ── 실리프팅 ──
        ("실리프팅", "민트실", None, "코그(미세돌기) 실. 녹는 실 중 유지 기간이 길고 리프팅력이 강함"),
        ("실리프팅", "코그실", None, "미세돌기가 있는 녹는 실. 처진 피부를 물리적으로 끌어올리는 시술"),
        ("실리프팅", "몰드실", None, "녹는 실의 한 종류. 압축 성형 방식으로 지지력이 우수"),
        ("실리프팅", "녹는실", None, "PDO/PCL/PLLA 등 생분해성 실. 피부 속에서 콜라겐 생성을 촉진"),
        ("실리프팅", "PDO실", None, "Polydioxanone 소재 녹는 실. 6개월~1년 내 자연 분해되며 콜라겐 유도"),

        # ── 스킨부스터 ──
        ("스킨부스터", "리쥬란", "파마리서치", "연어 유래 PN(폴리뉴클레오타이드) 주사. 피부 재생·탄력·보습 효과"),
        ("스킨부스터", "쥬벨룩", "에이비오", "PDLLA 성분 콜라겐 부스터. 피부 속 콜라겐 재생을 촉진"),
        ("스킨부스터", "엑소좀", None, "줄기세포 유래 세포외소포체. 피부 재생·항염·미백 효과"),
        ("스킨부스터", "연어주사", None, "PDRN 성분. 손상된 세포 재생, 피부톤·탄력 개선"),
        ("스킨부스터", "물광주사", None, "HA+비타민 칵테일을 진피층에 주입. 보습·광채·탄력 개선"),
        ("스킨부스터", "PDRN", None, "연어·송어 DNA에서 추출한 재생 인자. 상처 치유·피부 재생 촉진"),
        ("스킨부스터", "볼피주사", "멀츠", "고농도 HA 스킨부스터. 미세 주입으로 피부 보습·탄력 개선"),
        ("스킨부스터", "이니셜", "갈더마", "가교 결합 없는 순수 HA 주입. 피부 속 보습력 강화"),

        # ── 색소/기미 ──
        ("색소", "피코토닝", None, "피코초 레이저 토닝. 기미·잡티를 미세하게 분쇄하여 제거"),
        ("색소", "레블라이트", "사이노슈어", "1064nm Nd:YAG 레이저. 기미·색소침착 토닝에 사용"),
        ("색소", "스펙트라", "루트로닉", "국산 Nd:YAG 레이저. 토닝·필링 모드로 기미·모공 개선"),
        ("색소", "루비레이저", None, "694nm 루비 레이저. 검버섯·주근깨 등 표피 색소 제거에 특화"),
        ("색소", "IPL", None, "광선치료기. 다파장 빛으로 색소·홍조·모세혈관 확장 동시 개선"),
        ("색소", "클라리티", "루트로닉", "알렉산드라이트+Nd:YAG 듀얼 레이저. 색소·제모·혈관 복합 치료"),

        # ── 스킨케어 ──
        ("스킨케어", "아쿠아필", None, "수용성 필링. 모공 속 노폐물 제거 + 보습 세럼 도포"),
        ("스킨케어", "스케일링", None, "피부과 전문 스케일링. 각질·피지 제거로 피부결 개선"),
        ("스킨케어", "LDM", None, "Local Dynamic Micro-massage. 초음파 마사지로 피부 재생 촉진"),
        ("스킨케어", "더마펜", None, "미세 바늘로 피부에 미세 상처 → 자연 재생 유도. 흉터·모공 개선"),

        # ── 여드름/모공 ──
        ("여드름", "MLA", None, "마이크로 레이저 어블레이션. 미세 레이저 홀로 모공·흉터 개선"),
        ("여드름", "프락셀", "솔타메디컬", "비절개 프랙셔널 레이저. 미세 열 기둥으로 피부 재생·모공 축소"),
        ("여드름", "아그네스", None, "피지선 선택적 고주파 치료. 여드름 원인인 피지선을 직접 파괴"),
        ("여드름", "CO2레이저", None, "탄산가스 레이저. 점·사마귀 제거, 흉터 리서페이싱에 사용"),

        # ── 제모 ──
        ("제모", "알렉스레이저", None, "755nm 알렉산드라이트 레이저. 밝은 피부의 제모에 효과적"),
        ("제모", "다이오드", None, "810nm 다이오드 레이저. 다양한 피부 타입의 제모에 범용 사용"),
        ("제모", "젠틀맥스", "캔델라", "알렉산드라이트+Nd:YAG 듀얼 제모 레이저. 모든 피부 타입 적용"),

        # ── 비만/체형 ──
        ("비만", "지방분해주사", None, "PPC/디옥시콜산 주입. 지방세포를 화학적으로 분해하여 제거"),
        ("비만", "HPL", None, "High Power Lipolysis. 고출력 레이저로 지방세포 파괴"),
        ("비만", "크라이오", None, "냉각 지방분해(쿨스컬프팅). 저온으로 지방세포 선택적 제거"),
        ("비만", "인바디", None, "체성분 분석기. 근육량·체지방·수분 등 체성분 측정 (치료 장비 아님)"),

        # ── 윤곽주사 ──
        ("윤곽", "윤곽주사", None, "PPC+디옥시콜산 주사. 얼굴 지방층을 분해하여 얼굴선 개선"),
        ("윤곽", "볼처짐주사", None, "볼 지방을 분해하는 윤곽주사의 일종. V라인 효과"),
        ("윤곽", "V라인주사", None, "턱선 주변 지방 분해 주사. 이중턱·턱살 개선"),

        # ── 활력주사 ──
        ("활력주사", "신데렐라주사", None, "치옥트산(알파리포산) 정맥 주사. 항산화·해독·피로 회복"),
        ("활력주사", "백옥주사", None, "글루타치온 정맥 주사. 항산화·미백·피로 회복 효과"),
        ("활력주사", "마늘주사", None, "비타민B1(푸르설타민) 주사. 마늘 냄새가 나며 피로 회복에 효과"),
    ]

    for cat_name, name, brand, desc in treatments:
        cat_id = cat_map.get(cat_name)
        # 동일 이름이 이미 있으면 description만 업데이트
        c.execute("SELECT id FROM evt_treatments WHERE name = ? AND (brand = ? OR (brand IS NULL AND ? IS NULL))", (name, brand, brand))
        row = c.fetchone()
        if row:
            c.execute("UPDATE evt_treatments SET description = ?, category_id = ? WHERE id = ?", (desc, cat_id, row[0]))
        else:
            c.execute(
                "INSERT INTO evt_treatments (category_id, name, brand, description, is_verified) VALUES (?, ?, ?, ?, 0)",
                (cat_id, name, brand, desc),
            )

    conn.commit()
    print(f"시술 사전 시드 데이터 삽입 완료 ({len(treatments)}개)")


def import_blog_data_if_empty():
    """blog_posts가 비어있고 덤프 파일이 있으면 자동 import."""
    conn = sqlite3.connect(DB_PATH)
    count = conn.execute("SELECT COUNT(*) FROM blog_posts").fetchone()[0]
    conn.close()
    if count > 0:
        return  # 이미 데이터 있음

    dump_path = os.path.join(os.path.dirname(__file__), "blog", "blog_data.json.gz")
    if not os.path.exists(dump_path):
        return

    print("블로그 데이터 자동 import 시작...")
    from blog.export_blog_data import import_data
    import_data()


if __name__ == "__main__":
    init_db()
    import_blog_data_if_empty()

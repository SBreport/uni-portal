"""
시술 정규화 마이그레이션 스크립트

기능:
  1. evt_treatments 에 item_type, device_info_id 컬럼 추가
  2. device_master.json → device_info UPSERT (aliases JSON 배열로 저장)
  3. 118개 device_master 항목 중 DB에 없는 것 INSERT
  4. evt_treatments 전체를 body_part / device / care / treatment / unknown 분류
  5. device_info 매칭 시 device_info_id 설정

사용:
    python scripts/normalize_treatments.py               # 전체 실행
    python scripts/normalize_treatments.py --dry-run     # 실제 반영 없이 미리보기
    python scripts/normalize_treatments.py --stats-only  # 현황 통계만 출력
"""

import json
import os
import re
import sqlite3
import sys
import argparse

# 프로젝트 루트를 sys.path에 추가
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _PROJECT_ROOT)

DB_PATH        = os.path.join(_PROJECT_ROOT, "data", "equipment.db")
MASTER_PATH    = os.path.join(_PROJECT_ROOT, "data", "device_master.json")
PATTERNS_PATH  = os.path.join(_PROJECT_ROOT, "normalization", "treatment_patterns.json")


# ────────────────────────────────────────────────────────────
# 헬퍼
# ────────────────────────────────────────────────────────────

def _load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _normalize_key(text: str) -> str:
    """비교용 정규화: 소문자 + 공백 제거."""
    return re.sub(r"\s+", "", text.lower().strip())


def _strip_gender_prefix(name: str, gender_prefixes: list) -> str:
    """'男) 인중' → '인중', '남) 브라질리언' → '브라질리언'."""
    for prefix in gender_prefixes:
        if name.startswith(prefix):
            return name[len(prefix):].strip()
    return name


# ────────────────────────────────────────────────────────────
# Step 1: 컬럼 추가
# ────────────────────────────────────────────────────────────

def add_columns(conn: sqlite3.Connection, dry_run: bool) -> None:
    """evt_treatments 에 item_type, device_info_id 컬럼 추가."""
    c = conn.cursor()

    # item_type 컬럼
    try:
        c.execute("ALTER TABLE evt_treatments ADD COLUMN item_type TEXT DEFAULT 'unknown'")
        if not dry_run:
            conn.commit()
        print("  [컬럼 추가] evt_treatments.item_type")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e).lower():
            print("  [이미 존재] evt_treatments.item_type")
        else:
            raise

    # device_info_id 컬럼
    try:
        c.execute("ALTER TABLE evt_treatments ADD COLUMN device_info_id INTEGER REFERENCES device_info(id)")
        if not dry_run:
            conn.commit()
        print("  [컬럼 추가] evt_treatments.device_info_id")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e).lower():
            print("  [이미 존재] evt_treatments.device_info_id")
        else:
            raise


# ────────────────────────────────────────────────────────────
# Step 2 & 3: device_master.json → device_info UPSERT
# ────────────────────────────────────────────────────────────

def sync_device_master(conn: sqlite3.Connection, dry_run: bool) -> dict:
    """device_master.json 전체를 device_info 테이블에 UPSERT.

    기존 sync_device_master.py 는 aliases 를 ', '.join() 문자열로 저장했으나
    여기서는 JSON 배열 문자열로 저장하여 이후 파싱이 쉽도록 함.
    """
    master_data = _load_json(MASTER_PATH)
    devices = master_data.get("devices", [])

    c = conn.cursor()
    added, updated = 0, 0

    for dev in devices:
        name = dev.get("name", "").strip()
        if not name:
            continue

        category  = dev.get("category", "")
        summary   = dev.get("summary", "")
        target    = dev.get("target", "")
        mechanism = dev.get("mechanism", "")
        note      = dev.get("note", "")
        aliases   = dev.get("aliases", [])
        # aliases 를 JSON 배열 문자열로 저장
        aliases_json = json.dumps(aliases, ensure_ascii=False)
        is_verified  = 1 if dev.get("is_verified", False) else 0

        c.execute("SELECT id FROM device_info WHERE name = ?", (name,))
        row = c.fetchone()

        if row:
            action = "UPDATE"
            if not dry_run:
                c.execute("""
                    UPDATE device_info
                    SET category=?, summary=?, target=?, mechanism=?, note=?,
                        aliases=?, is_verified=?, updated_at=CURRENT_TIMESTAMP
                    WHERE name=?
                """, (category, summary, target, mechanism, note,
                      aliases_json, is_verified, name))
            updated += 1
        else:
            action = "ADD"
            if not dry_run:
                c.execute("""
                    INSERT INTO device_info
                        (name, category, summary, target, mechanism, note, aliases, is_verified)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (name, category, summary, target, mechanism, note,
                      aliases_json, is_verified))
            added += 1

        if dry_run:
            print(f"    [DRY-RUN] {action}: {name}  aliases={aliases[:2]}")

    if not dry_run:
        conn.commit()

    print(f"\n  device_info 동기화: 추가 {added}건, 수정 {updated}건")
    return {"added": added, "updated": updated}


# ────────────────────────────────────────────────────────────
# Step 4 & 5: evt_treatments 분류 + device_info 매칭
# ────────────────────────────────────────────────────────────

def _build_device_index(conn: sqlite3.Connection) -> dict:
    """device_info 전체를 로드하여 {정규화된_키: (id, name)} 인덱스 생성.

    name + aliases 모두 인덱싱.
    """
    c = conn.cursor()
    c.execute("SELECT id, name, aliases FROM device_info")
    rows = c.fetchall()

    index: dict[str, tuple[int, str]] = {}
    for device_id, name, aliases_raw in rows:
        # name 인덱싱
        key = _normalize_key(name)
        if key and key not in index:
            index[key] = (device_id, name)

        # aliases 인덱싱 (JSON 배열 또는 쉼표 구분 문자열 모두 처리)
        if aliases_raw:
            try:
                alias_list = json.loads(aliases_raw)
            except (json.JSONDecodeError, TypeError):
                # 구버전 쉼표 구분 문자열 호환
                alias_list = [a.strip() for a in aliases_raw.split(",") if a.strip()]

            for alias in alias_list:
                akey = _normalize_key(alias)
                if akey and akey not in index:
                    index[akey] = (device_id, name)

    return index


def _classify_treatment(
    name: str,
    stripped_name: str,
    body_part_set: set,
    care_kw_set: set,
    treatment_kw_set: set,
    device_index: dict,
) -> tuple[str, int | None]:
    """시술명 → (item_type, device_info_id).

    우선순위:
      1. device 매칭 (device_index)
      2. 부위명 (body_part_set 에 exact 또는 startswith)
      3. care 키워드
      4. treatment 키워드
      5. unknown
    """
    # 1. 장비 매칭 (원본 + 성별 제거 버전 모두 시도)
    for candidate in [name, stripped_name]:
        key = _normalize_key(candidate)
        if key and key in device_index:
            return "device", device_index[key][0]

    # 부분 매칭: 시술명이 장비명을 포함 (예: '슈링크 유니버스 1회' → '슈링크유니버스')
    for dev_key, (dev_id, _dev_name) in device_index.items():
        # 장비 key 가 3자 이상이고 치료명 정규화 키에 포함되면 매칭
        if len(dev_key) >= 3:
            norm_stripped = _normalize_key(stripped_name)
            if dev_key in norm_stripped:
                return "device", dev_id

    # 2. 부위명 exact match
    if stripped_name in body_part_set:
        return "body_part", None

    # 부위명 prefix match (예: '겨드랑이 제모' → 겨드랑이 is body part)
    for bp in body_part_set:
        if stripped_name.startswith(bp) and len(bp) >= 2:
            return "body_part", None

    # 3. care 키워드
    for kw in care_kw_set:
        if kw in stripped_name or kw in name:
            return "care", None

    # 4. treatment 키워드
    for kw in treatment_kw_set:
        if kw in stripped_name or kw in name:
            return "treatment", None

    return "unknown", None


def classify_treatments(conn: sqlite3.Connection, dry_run: bool) -> dict:
    """evt_treatments 전체를 순회하며 item_type / device_info_id 설정."""
    patterns = _load_json(PATTERNS_PATH)
    body_part_set    = set(patterns.get("body_parts", []))
    gender_prefixes  = patterns.get("gender_prefixes", [])
    care_kw_set      = set(patterns.get("care_keywords", []))
    # known_brands 도 treatment 키워드로 취급
    treatment_kw_set = set(patterns.get("treatment_keywords", [])) | set(patterns.get("known_brands", []))

    device_index = _build_device_index(conn)
    print(f"  device_info 인덱스: {len(device_index)}개 키 (name + aliases)")

    c = conn.cursor()
    c.execute("SELECT id, name FROM evt_treatments WHERE is_active = 1")
    all_treatments = c.fetchall()

    counts = {"device": 0, "body_part": 0, "care": 0, "treatment": 0, "unknown": 0}
    updates: list[tuple[str, int | None, int]] = []

    for treat_id, name in all_treatments:
        if not name or not name.strip():
            updates.append(("unknown", None, treat_id))
            counts["unknown"] += 1
            continue

        stripped = _strip_gender_prefix(name.strip(), gender_prefixes)

        item_type, device_info_id = _classify_treatment(
            name.strip(), stripped,
            body_part_set, care_kw_set, treatment_kw_set,
            device_index,
        )
        counts[item_type] += 1
        updates.append((item_type, device_info_id, treat_id))

    if dry_run:
        print(f"\n  [DRY-RUN] 분류 결과 (총 {len(updates)}건):")
        for item_type, count in sorted(counts.items(), key=lambda x: -x[1]):
            print(f"    {item_type:12s}: {count:5d}건")

        # 샘플 5건씩 출력
        sample_map: dict[str, list] = {}
        for item_type, device_info_id, treat_id in updates:
            sample_map.setdefault(item_type, []).append((treat_id, device_info_id))

        c.execute("SELECT id, name FROM evt_treatments WHERE is_active = 1")
        id_to_name = {r[0]: r[1] for r in c.fetchall()}

        for itype in ["device", "body_part", "care", "treatment", "unknown"]:
            samples = sample_map.get(itype, [])[:5]
            if samples:
                print(f"\n  [{itype}] 샘플:")
                for tid, did in samples:
                    n = id_to_name.get(tid, "?")
                    suffix = f" → device_info #{did}" if did else ""
                    print(f"    {n}{suffix}")
    else:
        # 실제 업데이트 — 배치로 처리
        batch_size = 500
        for i in range(0, len(updates), batch_size):
            batch = updates[i : i + batch_size]
            c.executemany(
                "UPDATE evt_treatments SET item_type=?, device_info_id=? WHERE id=?",
                batch,
            )
        conn.commit()
        print(f"\n  분류 완료 (총 {len(updates)}건):")
        for item_type, count in sorted(counts.items(), key=lambda x: -x[1]):
            print(f"    {item_type:12s}: {count:5d}건")

    return counts


# ────────────────────────────────────────────────────────────
# 통계 출력
# ────────────────────────────────────────────────────────────

def print_stats(conn: sqlite3.Connection) -> None:
    """현재 분류 현황 통계 출력."""
    c = conn.cursor()

    total = c.execute("SELECT COUNT(*) FROM evt_treatments").fetchone()[0]
    print(f"\n-- evt_treatments 통계 (총 {total}건) --")

    # item_type 분포
    rows = c.execute("""
        SELECT COALESCE(item_type, 'NULL'), COUNT(*)
        FROM evt_treatments
        GROUP BY item_type
        ORDER BY COUNT(*) DESC
    """).fetchall()
    print("\n  item_type 분포:")
    for itype, cnt in rows:
        pct = cnt / total * 100 if total else 0
        print(f"    {itype:12s}: {cnt:5d}건 ({pct:.1f}%)")

    # device 매칭 현황
    matched = c.execute("""
        SELECT COUNT(*) FROM evt_treatments
        WHERE device_info_id IS NOT NULL
    """).fetchone()[0]
    print(f"\n  device_info 연결: {matched}건")

    # device_info 통계
    di_total = c.execute("SELECT COUNT(*) FROM device_info").fetchone()[0]
    print(f"\n-- device_info 통계 (총 {di_total}건) --")
    di_cats = c.execute("""
        SELECT category, COUNT(*) FROM device_info
        GROUP BY category ORDER BY COUNT(*) DESC LIMIT 15
    """).fetchall()
    for cat, cnt in di_cats:
        print(f"    {cat:30s}: {cnt}건")


# ────────────────────────────────────────────────────────────
# 메인
# ────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="시술명 정규화 마이그레이션")
    parser.add_argument("--dry-run",    action="store_true", help="실제 반영 없이 미리보기")
    parser.add_argument("--stats-only", action="store_true", help="현황 통계만 출력")
    args = parser.parse_args()

    if not os.path.exists(DB_PATH):
        print(f"ERROR: DB 파일을 찾을 수 없습니다: {DB_PATH}")
        sys.exit(1)
    if not os.path.exists(MASTER_PATH):
        print(f"ERROR: device_master.json 을 찾을 수 없습니다: {MASTER_PATH}")
        sys.exit(1)
    if not os.path.exists(PATTERNS_PATH):
        print(f"ERROR: treatment_patterns.json 을 찾을 수 없습니다: {PATTERNS_PATH}")
        sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    try:
        if args.stats_only:
            print_stats(conn)
            return

        print("=" * 60)
        print("시술 정규화 마이그레이션 시작")
        if args.dry_run:
            print("  ※ DRY-RUN 모드 - DB 변경 없음")
        print("=" * 60)

        print("\n[Step 1] 컬럼 추가")
        add_columns(conn, dry_run=args.dry_run)

        print("\n[Step 2-3] device_master.json → device_info UPSERT")
        sync_device_master(conn, dry_run=args.dry_run)

        print("\n[Step 4-5] evt_treatments 분류 + device_info 매칭")
        classify_treatments(conn, dry_run=args.dry_run)

        print("\n[결과 통계]")
        print_stats(conn)

        print("\n완료!")
        if args.dry_run:
            print("(dry-run 모드 - 실제 DB에는 반영되지 않았습니다)")

    finally:
        conn.close()


if __name__ == "__main__":
    main()

"""이벤트 시술명에서 부위/장비/재료/목적 태그를 추출하여 DB에 저장.

사용법: python -m treatment.extract_tags
"""

import sqlite3
import re
import logging
from datetime import datetime
from shared.db import get_conn, EQUIPMENT_DB

logger = logging.getLogger(__name__)

# ── 부위 사전 (계층: 대분류 → 소분류) ──
BODY_PARTS = {
    # 얼굴
    "이마": "얼굴",
    "미간": "얼굴",
    "눈가": "얼굴",
    "눈밑": "얼굴",
    "눈썹": "얼굴",
    "코": "얼굴",
    "콧등": "얼굴",
    "콧볼": "얼굴",
    "볼": "얼굴",
    "광대": "얼굴",
    "앞광대": "얼굴",
    "옆볼": "얼굴",
    "앞볼": "얼굴",
    "인중": "얼굴",
    "입술": "얼굴",
    "윗입술": "얼굴",
    "입꼬리": "얼굴",
    "턱": "얼굴",
    "사각턱": "얼굴",
    "이중턱": "얼굴",
    "턱선": "얼굴",
    "팔자": "얼굴",
    "관자놀이": "얼굴",
    "헤어라인": "얼굴",
    # 목
    "목": "목",
    "목주름": "목",
    "뒷목": "목",
    # 두피
    "두피": "두피",
    # 상체
    "겨드랑이": "상체",
    "팔": "상체",
    "팔꿈치": "상체",
    "손": "상체",
    "가슴": "상체",
    "등": "상체",
    "어깨": "상체",
    # 복부
    "배": "복부",
    "복부": "복부",
    "옆구리": "복부",
    "러브핸들": "복부",
    # 하체
    "허벅지": "하체",
    "무릎": "하체",
    "종아리": "하체",
    "발": "하체",
    "허리": "하체",
    "엉덩이": "하체",
    # 비뇨/생식기
    "비키니": "비뇨생식",
    "브라질리언": "비뇨생식",
    "사타구니": "비뇨생식",
    "회음부": "비뇨생식",
    "항문": "비뇨생식",
    "성기": "비뇨생식",
    # 전신
    "얼굴전체": "얼굴",
    "바디": "전신",
    "전신": "전신",
}

# 복합어 우선 매칭 (긴 것부터)
BODY_PARTS_SORTED = sorted(BODY_PARTS.keys(), key=len, reverse=True)

# ── 시술 목적 사전 ──
PURPOSES = {
    "리프팅": "탄력/리프팅",
    "탄력": "탄력/리프팅",
    "주름": "탄력/리프팅",
    "토닝": "색소/미백",
    "미백": "색소/미백",
    "착색": "색소/미백",
    "기미": "색소/미백",
    "잡티": "색소/미백",
    "홍조": "색소/미백",
    "색소": "색소/미백",
    "문신": "색소/미백",
    "제모": "제모",
    "여드름": "여드름/모공",
    "모공": "여드름/모공",
    "흉터": "흉터/재생",
    "재생": "흉터/재생",
    "보습": "보습/광채",
    "물광": "보습/광채",
    "광채": "보습/광채",
    "볼륨": "볼륨",
    "축소": "축소/윤곽",
    "윤곽": "축소/윤곽",
    "다이어트": "체형/다이어트",
    "지방분해": "체형/다이어트",
    "슬리밍": "체형/다이어트",
    "다한증": "다한증",
    "탈모": "탈모",
    "필링": "필링/각질",
    "스케일링": "필링/각질",
    "점": "점/사마귀",
    "사마귀": "점/사마귀",
}
PURPOSES_SORTED = sorted(PURPOSES.keys(), key=len, reverse=True)

# ── 장비/재료 사전 (DB에서 동적 로드 + 추가 키워드) ──
EXTRA_EQUIPMENT = {
    "써마지": "장비",
    "써마지FLX": "장비",
    "온다": "장비",
    "볼뉴머": "장비",
    "텐써마": "장비",
    "올타이트": "장비",
    "네오페이스": "장비",
    "실펌": "장비",
    "실펌X": "장비",
    "덴서티": "장비",
    "리프테라": "장비",
    "컴포트듀얼": "장비",
    "엠페이스": "장비",
    "트리플바디": "장비",
    "엔디야그": "장비",
    "레블라이트": "장비",
    "클라리티": "장비",
    "젠틀맥스": "장비",
    "아포지": "장비",
    "다이오드": "장비",
    "알렉스": "장비",
    "루비레이저": "장비",
    "IPL": "장비",
    "프락셀": "장비",
    "더마펜": "장비",
    "포텐자": "장비",
    "쓰리딥": "장비",
}

EXTRA_MATERIALS = {
    "보톡스": "재료",
    "스킨보톡스": "재료",
    "필러": "재료",
    "쥬베룩": "재료",
    "리쥬란": "재료",
    "물광": "재료",
    "벨로테로": "재료",
    "쥬비덤": "재료",
    "레스틸렌": "재료",
    "엘란쎄": "재료",
    "더모톡신": "재료",
    "코어톡스": "재료",
    "나보타": "재료",
    "리즈톡스": "재료",
    "하이코": "재료",
    "올리디아": "재료",
    "녹는실": "재료",
    "PDO실": "재료",
    "PCL실": "재료",
    "아쎄라": "재료",
    "윤곽주사": "재료",
    "지방분해주사": "재료",
    "PDRN": "재료",
    "콜라겐": "재료",
    "히알루론산": "재료",
}


def _load_equipment_names(conn):
    """device_info에서 장비명 + aliases 로드."""
    equip_map = {}
    rows = conn.execute("SELECT name, aliases FROM device_info").fetchall()
    for r in rows:
        equip_map[r["name"]] = "장비"
        if r["aliases"]:
            for alias in r["aliases"].split(","):
                alias = alias.strip()
                if alias:
                    equip_map[alias] = "장비"
    return equip_map


def _load_treatment_names(conn):
    """evt_treatments에서 시술명 로드."""
    treat_map = {}
    rows = conn.execute("""
        SELECT et.name, ec.name as cat_name
        FROM evt_treatments et
        JOIN evt_categories ec ON et.category_id = ec.id
    """).fetchall()
    for r in rows:
        treat_map[r["name"]] = r["cat_name"]
    return treat_map


def extract_tags_from_name(name: str, equip_dict: dict) -> dict:
    """시술명 하나에서 태그 추출.

    Returns:
        {
            "body_parts": [{"part": "이마", "region": "얼굴"}, ...],
            "purposes": [{"keyword": "리프팅", "category": "탄력/리프팅"}, ...],
            "equipment": [{"name": "써마지", "type": "장비"}, ...],
            "gender": "여" | "남" | None,
        }
    """
    result = {
        "body_parts": [],
        "purposes": [],
        "equipment": [],
        "gender": None,
    }

    # 성별
    if "女)" in name or "여)" in name:
        result["gender"] = "여"
    elif "男)" in name or "남)" in name:
        result["gender"] = "남"

    # 부위
    seen_parts = set()
    for part in BODY_PARTS_SORTED:
        if part in name and part not in seen_parts:
            # "얼굴전체"가 매칭되면 "얼굴"은 스킵
            if part == "얼굴" and "얼굴전체" in name:
                continue
            # "코"는 단독 출현시만 (코어톡스, 코스 등 오탐 방지)
            if part == "코" and not re.search(r'(?:^|[\s(/])코(?:$|[\s)/,])', name):
                continue
            # "등"은 단독 출현시만 (콧등 등 오탐 방지)
            if part == "등" and "콧등" in name:
                continue
            if part == "배" and any(x in name for x in ["배곧", "배꼽"]):
                continue
            seen_parts.add(part)
            result["body_parts"].append({
                "part": part,
                "region": BODY_PARTS[part],
            })

    # 목적
    seen_purposes = set()
    for kw in PURPOSES_SORTED:
        if kw in name and PURPOSES[kw] not in seen_purposes:
            # "물광"은 장비/재료이기도 하므로 목적으로도 추가
            seen_purposes.add(PURPOSES[kw])
            result["purposes"].append({
                "keyword": kw,
                "category": PURPOSES[kw],
            })

    # 장비/재료
    seen_equip = set()
    all_equip = {**equip_dict, **EXTRA_EQUIPMENT, **EXTRA_MATERIALS}
    # 긴 이름부터 매칭
    for eq_name in sorted(all_equip.keys(), key=len, reverse=True):
        if eq_name.lower() in name.lower() and eq_name not in seen_equip:
            seen_equip.add(eq_name)
            result["equipment"].append({
                "name": eq_name,
                "type": all_equip[eq_name],
            })

    return result


def run_extraction():
    """전체 이벤트 시술명에서 태그 추출 → DB 저장."""
    conn = get_conn(EQUIPMENT_DB)
    conn.row_factory = sqlite3.Row

    # 테이블 생성
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS treatment_body_tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            source_id INTEGER,
            source_name TEXT NOT NULL,
            tag_type TEXT NOT NULL CHECK(tag_type IN ('body_part','purpose','equipment','material','gender')),
            tag_value TEXT NOT NULL,
            tag_category TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_tbt_source ON treatment_body_tags(source, source_id);
        CREATE INDEX IF NOT EXISTS idx_tbt_type ON treatment_body_tags(tag_type);
        CREATE INDEX IF NOT EXISTS idx_tbt_value ON treatment_body_tags(tag_value);
    """)

    # 기존 데이터 삭제 (재실행 가능)
    conn.execute("DELETE FROM treatment_body_tags WHERE source = 'evt_items'")
    conn.commit()

    equip_dict = _load_equipment_names(conn)

    # 고유 시술명 + raw_category 조합으로 추출
    rows = conn.execute("""
        SELECT DISTINCT raw_event_name, raw_category, MIN(id) as sample_id
        FROM evt_items
        WHERE raw_event_name IS NOT NULL AND raw_event_name != ''
        GROUP BY raw_event_name, raw_category
    """).fetchall()

    total = len(rows)
    tagged = 0
    total_tags = 0

    for row in rows:
        name = row["raw_event_name"]
        cat = row["raw_category"] or ""
        sample_id = row["sample_id"]

        # 카테고리명도 힌트로 결합
        combined = f"{cat} {name}"
        tags = extract_tags_from_name(combined, equip_dict)

        has_tag = False

        for bp in tags["body_parts"]:
            conn.execute("""
                INSERT INTO treatment_body_tags (source, source_id, source_name, tag_type, tag_value, tag_category)
                VALUES ('evt_items', ?, ?, 'body_part', ?, ?)
            """, (sample_id, name, bp["part"], bp["region"]))
            total_tags += 1
            has_tag = True

        for p in tags["purposes"]:
            conn.execute("""
                INSERT INTO treatment_body_tags (source, source_id, source_name, tag_type, tag_value, tag_category)
                VALUES ('evt_items', ?, ?, 'purpose', ?, ?)
            """, (sample_id, name, p["keyword"], p["category"]))
            total_tags += 1
            has_tag = True

        for eq in tags["equipment"]:
            t = "equipment" if eq["type"] == "장비" else "material"
            conn.execute("""
                INSERT INTO treatment_body_tags (source, source_id, source_name, tag_type, tag_value, tag_category)
                VALUES ('evt_items', ?, ?, ?, ?, ?)
            """, (sample_id, name, t, eq["name"], eq["type"]))
            total_tags += 1
            has_tag = True

        if tags["gender"]:
            conn.execute("""
                INSERT INTO treatment_body_tags (source, source_id, source_name, tag_type, tag_value, tag_category)
                VALUES ('evt_items', ?, ?, 'gender', ?, '')
            """, (sample_id, name, tags["gender"]))
            total_tags += 1
            has_tag = True

        if has_tag:
            tagged += 1

    conn.commit()

    result = {
        "ok": True,
        "total_names": total,
        "tagged_names": tagged,
        "untagged_names": total - tagged,
        "total_tags": total_tags,
        "coverage": f"{(tagged / total * 100):.1f}%" if total > 0 else "0%",
    }
    logger.info(f"[extract_tags] 완료: {result}")
    conn.close()
    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = run_extraction()
    print(f"\n=== 태그 추출 완료 ===")
    for k, v in result.items():
        print(f"  {k}: {v}")

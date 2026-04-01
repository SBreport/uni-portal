"""장비/시술 매칭 공용 엔진.

모든 탭(보유장비, 카페, 논문 등)에서 동일한 매칭 로직을 사용하여
"하나의 장비 = 하나의 진실(Single Source of Truth)" 원칙을 보장.

매칭 우선순위:
    1. 정확 매칭: name == query
    2. 순방향 포함: query ⊃ name (써마지FLX → 써마지)
    3. 역방향 포함: name ⊃ query (써마지 → 써마지FLX)
    4. aliases 매칭: aliases에서 부분 매칭

한글 경계 규칙:
    - 한글 뒤에 한글이 바로 이어지면 다른 단어로 판단 (울쎄라 ≠ 울쎄라피)
    - 한글 뒤에 영문/숫자가 이어지면 모델 변형으로 판단 (써마지 = 써마지FLX)
"""

import sqlite3
import os

from shared.db import get_conn, EQUIPMENT_DB


def _get_conn():
    return get_conn(EQUIPMENT_DB)


# ── 한글 경계 유틸 ──

def _is_hangul(ch: str) -> bool:
    """한글 완성형 음절인지 확인."""
    return '\uAC00' <= ch <= '\uD7A3'


def _is_safe_substring(short: str, long_str: str) -> bool:
    """short가 long_str의 부분문자열일 때, 한글 경계가 안전한지 확인.

    한글 바로 뒤에 한글이 이어지면 다른 단어일 가능성 높음 (울쎄라 ⊂ 울쎄라피).
    영문/숫자/공백이 이어지면 모델 변형일 가능성 높음 (써마지 ⊂ 써마지FLX).
    """
    idx = long_str.find(short)
    if idx < 0:
        return False

    # 앞쪽 경계: short 앞에 한글이 붙어있으면 위험
    if idx > 0 and _is_hangul(long_str[idx - 1]) and _is_hangul(short[0]):
        return False

    # 뒤쪽 경계: short 뒤에 한글이 바로 이어지면 위험
    end_idx = idx + len(short)
    if end_idx < len(long_str) and _is_hangul(long_str[end_idx]) and _is_hangul(short[-1]):
        return False

    return True


# ── 장비 매칭 ──

def _load_device_list() -> list[dict]:
    """device_info 테이블에서 전체 장비 목록 로드."""
    try:
        conn = _get_conn()
        rows = conn.execute(
            "SELECT * FROM device_info ORDER BY usage_count DESC, name"
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception:
        return []


def match_devices(equip_name: str, device_list: list[dict] | None = None) -> list[dict]:
    """장비명 → device_info 매칭. 우선순위별 결과 리스트 반환.

    Args:
        equip_name: 검색할 장비명
        device_list: device_info 목록 (None이면 DB에서 로드)

    Returns:
        매칭된 device_info dict 리스트 (우선순위 순)
    """
    if device_list is None:
        device_list = _load_device_list()

    equip_lower = equip_name.lower().strip()
    if not equip_lower:
        return []

    exact = []
    contains = []      # query ⊃ DB name
    reverse = []       # DB name ⊃ query
    alias_match = []

    for row in device_list:
        db_name_lower = row["name"].lower().strip()

        # 1. 정확 매칭
        if db_name_lower == equip_lower:
            exact.append(row)
            continue

        # 2. 장비명이 DB 시술명을 포함 (써마지FLX → 써마지)
        if len(db_name_lower) >= 2 and db_name_lower in equip_lower:
            if _is_safe_substring(db_name_lower, equip_lower):
                contains.append(row)
            continue

        # 3. DB 시술명이 장비명을 포함 (써마지 → 써마지FLX)
        if len(equip_lower) >= 2 and equip_lower in db_name_lower:
            if _is_safe_substring(equip_lower, db_name_lower):
                reverse.append(row)
            continue

        # 4. aliases 매칭
        aliases_str = (row.get("aliases") or "").lower()
        if aliases_str:
            for alias in aliases_str.split(","):
                alias = alias.strip()
                if not alias:
                    continue
                if alias == equip_lower:
                    alias_match.append(row)
                    break
                if len(alias) >= 2 and len(equip_lower) >= 2:
                    if alias in equip_lower and _is_safe_substring(alias, equip_lower):
                        alias_match.append(row)
                        break
                    if equip_lower in alias and _is_safe_substring(equip_lower, alias):
                        alias_match.append(row)
                        break

    # 중복 제거하면서 우선순위 유지
    seen = set()
    result = []
    for row in exact + contains + reverse + alias_match:
        if row["name"] not in seen:
            seen.add(row["name"])
            result.append(row)

    return result


def match_single(equip_name: str, device_list: list[dict] | None = None) -> tuple:
    """장비명 → 첫 번째 매칭 결과 1건 반환.

    Returns:
        (device_info_id, device_name) 또는 (None, None)
    """
    results = match_devices(equip_name, device_list)
    if results:
        return results[0]["id"], results[0]["name"]
    return None, None


def match_from_names(name_list: list[str], device_list: list[dict] | None = None) -> tuple:
    """여러 장비명 후보에서 첫 번째 매칭 결과 반환.

    논문 분석 등에서 related_devices 리스트를 순회하며 매칭할 때 사용.

    Returns:
        (device_info_id, device_name) 또는 (None, None)
    """
    if device_list is None:
        device_list = _load_device_list()

    for name in name_list:
        if not name or not name.strip():
            continue
        dev_id, dev_name = match_single(name, device_list)
        if dev_id is not None:
            return dev_id, dev_name
    return None, None


# ── 시술(치료) 매칭 ──

def _load_treatment_list() -> list[dict]:
    """evt_treatments 테이블에서 전체 시술 목록 로드."""
    try:
        conn = _get_conn()
        rows = conn.execute(
            "SELECT id, name, brand, category_id FROM evt_treatments ORDER BY name"
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception:
        return []


def match_treatment(name: str, treatment_list: list[dict] | None = None) -> tuple:
    """시술명/브랜드 → evt_treatments 매칭.

    Returns:
        (treatment_id, treatment_name) 또는 (None, None)
    """
    if treatment_list is None:
        treatment_list = _load_treatment_list()

    name_lower = name.lower().strip()
    if not name_lower:
        return None, None

    # 정확 매칭 (name)
    for t in treatment_list:
        if name_lower == t["name"].lower():
            return t["id"], t["name"]

    # 브랜드 매칭
    for t in treatment_list:
        if t.get("brand") and name_lower == t["brand"].lower():
            return t["id"], t["name"]

    return None, None


def match_treatment_from_names(name_list: list[str], treatment_list: list[dict] | None = None) -> tuple:
    """여러 시술명 후보에서 첫 번째 매칭 결과 반환.

    Returns:
        (treatment_id, treatment_name) 또는 (None, None)
    """
    if treatment_list is None:
        treatment_list = _load_treatment_list()

    for name in name_list:
        if not name or not name.strip():
            continue
        t_id, t_name = match_treatment(name, treatment_list)
        if t_id is not None:
            return t_id, t_name
    return None, None


# ── 기술 키워드 → 장비 매칭 (논문 분석용) ──

import re

# 부정/비교 문맥 패턴 — 이 패턴이 매칭되면 해당 장비의 주기술이 아님
_NEGATIVE_PATTERNS_CACHE = {}


def _get_negative_patterns(keyword: str) -> list:
    """keyword에 대한 부정 문맥 패턴 리스트 (캐시)."""
    if keyword not in _NEGATIVE_PATTERNS_CACHE:
        kw = re.escape(keyword)
        _NEGATIVE_PATTERNS_CACHE[keyword] = [
            re.compile(p, re.IGNORECASE) for p in [
                rf'{kw}[와과]\s*다른',       # "HIFU와 다른"
                rf'{kw}[이가]\s*아닌',        # "HIFU가 아닌"
                rf'(?:아닌|않은|없는).*{kw}',  # "~아닌 ... HIFU"
                rf'기존\s*{kw}',              # "기존 HIFU"
                rf'{kw}\s*(?:대비|대신|외)',    # "HIFU 대비"
            ]
        ]
    return _NEGATIVE_PATTERNS_CACHE[keyword]


def _is_primary_technology(mechanism: str, keyword: str) -> bool:
    """mechanism 텍스트에서 keyword가 해당 장비의 주기술인지 판별.

    규칙:
      1. mechanism 첫 절(→ 또는 . 기준)에 keyword가 있으면 주기술
      2. 부정/비교 문맥(~와 다른, ~가 아닌)이면 주기술 아님
      3. 첫 절 이후에만 등장하면 주기술 아님

    Returns:
        True: 주기술로 확정 가능
        False: 주기술이 아님 (비교 대상이거나 보조 언급)
    """
    if not mechanism or not keyword:
        return False

    mechanism_upper = mechanism.upper()
    keyword_upper = keyword.upper()

    # keyword 자체가 mechanism에 없으면 패스
    if keyword_upper not in mechanism_upper:
        return False

    # 부정 문맥 체크
    for pat in _get_negative_patterns(keyword):
        if pat.search(mechanism):
            return False

    # 첫 절에 keyword가 있는지 확인 (→ 또는 . 으로 분할)
    # → 는 유니코드 U+2192, 간혹 > 로 대체될 수 있음
    first_clause = re.split(r'[.\u2192>]', mechanism)[0]
    if keyword_upper in first_clause.upper():
        return True

    return False


def match_by_technology(keyword: str, device_list: list[dict] | None = None) -> list[dict]:
    """기술 키워드로 관련 장비 매칭 (mechanism 필드 기반).

    논문에서 "HIFU", "RF", "KTP" 등 기술명이 나왔지만
    직접적인 장비명 매칭이 안될 때 사용.

    Args:
        keyword: 기술 키워드 (예: "HIFU", "RF", "KTP", "IPL")
        device_list: device_info 목록 (None이면 DB에서 로드)

    Returns:
        주기술로 확정된 장비 리스트 (자동 확정 가능)
    """
    if device_list is None:
        device_list = _load_device_list()

    if not keyword or not keyword.strip():
        return []

    results = []
    for row in device_list:
        mechanism = row.get("mechanism", "") or ""
        if _is_primary_technology(mechanism, keyword):
            results.append(row)

    return results


def match_devices_for_paper(
    related_devices: list[str],
    device_list: list[dict] | None = None
) -> list[dict]:
    """논문 분석용 통합 매칭 — 직접 매칭 + 기술 매칭.

    Returns:
        [
            {"device_info_id": 2, "device_name": "써마지FLX", "match_type": "direct", "match_keyword": "써마지FLX"},
            {"device_info_id": 54, "device_name": "울쎄라", "match_type": "technology", "match_keyword": "HIFU"},
            ...
        ]
    """
    if device_list is None:
        device_list = _load_device_list()

    results = []
    seen_ids = set()

    for name in related_devices:
        if not name or not name.strip():
            continue

        # 1차: 직접 매칭 (이름/aliases)
        direct_matches = match_devices(name, device_list)
        for dev in direct_matches:
            if dev["id"] not in seen_ids:
                seen_ids.add(dev["id"])
                results.append({
                    "device_info_id": dev["id"],
                    "device_name": dev["name"],
                    "match_type": "direct",
                    "match_keyword": name,
                    "is_verified": 1,  # 직접 매칭은 자동 확정
                })

        # 2차: 기술 매칭 (직접 매칭 안된 경우)
        if not direct_matches:
            tech_matches = match_by_technology(name, device_list)
            for dev in tech_matches:
                if dev["id"] not in seen_ids:
                    seen_ids.add(dev["id"])
                    results.append({
                        "device_info_id": dev["id"],
                        "device_name": dev["name"],
                        "match_type": "technology",
                        "match_keyword": name,
                        "is_verified": 1,  # mechanism 기반 = 자동 확정
                    })

    return results

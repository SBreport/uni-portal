# -*- coding: utf-8 -*-
"""
blog/branch_link.py
~~~~~~~~~~~~~~~~~~~
blog_posts / place_daily / webpage_daily 테이블의 branch_name을
evt_branches.id 로 매핑하는 공용 유틸리티.

이 모듈은 순수 함수 집합이며 import 부작용(stdout 교체 등)이 없다.
scripts/link_branches.py와 blog/sync_notion.py 양쪽에서 import해 사용한다.
"""

import re
import sqlite3


# ---------------------------------------------------------------------------
# 상수: Non-유앤아이 키워드 (매핑 제외 대상)
# ---------------------------------------------------------------------------

# 유앤아이 계열이 아닌 의원·클리닉 키워드 → evt_branch_id를 NULL로 둔다
NON_YUANAI_PREFIXES = [
    "파인드", "이효진여성의원", "이효진산부인과", "365봄", "조은", "참조은",
    "로렐의원", "레리", "신현편안", "더편한", "이다움", "이플", "푸른잎",
    "눈피부과", "굿플", "굿플란트", "굿플중랑", "민플", "닥터굿",
    "스브", "연세온아", "10월10일", "유라라", "파인리", "에이", "세련",
    "여울", "청아", "해피", "산부인과", "의원", "클리닉", "피부과",
    "병원", "한의원",
]

# 블로그 특수 케이스: "유앤XXX" 계정명 → evt_branches.name
BLOG_SPECIAL = {
    "유앤검단":  "인천검단점",
    "유앤배곧":  "시흥배곧점",
    "유앤미금":  "분당미금점",
    "유앤목동":  "목동점",
    "유앤하남미사": "하남미사점",
    "유앤경기광주": "경기광주점",
    "유앤화성봉담": "화성봉담점",
}

# 플레이스 특수 케이스: "XXX유앤아이" → evt_branches.name
PLACE_SPECIAL = {
    "미사유앤아이":    "하남미사점",
    "시흥배곧유앤아이": "시흥배곧점",
    "분당미금유앤아이": "분당미금점",
    "경기광주유앤아이": "경기광주점",
    "화성봉담유앤아이": "화성봉담점",
    "인천검단유앤아이": "인천검단점",
}

# 웹페이지 특수 케이스: "유앤아이의원 XXX점" → evt_branches.name
WEBPAGE_SPECIAL = {
    "검단점":   "인천검단점",
    "하남미사점": "하남미사점",
    "서면점":   None,  # 부산 서면 — 아직 독립 지점 없음
}


# ---------------------------------------------------------------------------
# 브랜치 룩업 로드
# ---------------------------------------------------------------------------

def load_branches(conn: sqlite3.Connection):
    """evt_branches 테이블에서 룩업 딕셔너리 두 개를 반환한다.

    sqlite3.Row와 tuple 모두 인덱스 기반으로 처리하므로 row_factory 무관.

    Returns:
        by_name  : { name_str -> id }   예) "강남점" -> 1
        by_short : { short_name -> id } 예) "강남" -> 1
    """
    cur = conn.cursor()
    cur.execute("SELECT id, name, short_name FROM evt_branches")
    rows = cur.fetchall()
    by_name  = {}
    by_short = {}
    for r in rows:
        by_name[r[1]]  = r[0]
        by_short[r[2]] = r[0]
    return by_name, by_short


# ---------------------------------------------------------------------------
# 매핑 함수
# ---------------------------------------------------------------------------

def is_non_yuanai_blog(name: str) -> bool:
    """해당 이름이 유앤아이 계열이 아닌 의원/클리닉이면 True 반환."""
    if not name:
        return False
    for prefix in NON_YUANAI_PREFIXES:
        if name.startswith(prefix):
            return True
    # 숫자만으로 구성된 이름 (예: "6", "7")
    if re.match(r"^\d+$", name):
        return True
    return False


def map_blog(branch_name: str, by_name: dict, by_short: dict):
    """blog_posts.branch_name → evt_branch_id 변환. 매핑 불가 시 None 반환.

    처리 우선순위:
      1. 빈값·숫자 시작 → None
      2. Non-유앤아이 필터
      3. evt_branches.name 직접 일치
      4. BLOG_SPECIAL 특수 케이스
      5. "유앤XXX" 패턴 분해 → core + "점" / short_name
    """
    name = (branch_name or "").strip()

    # 빈값
    if not name:
        return None

    # 숫자로 시작 → NULL
    if re.match(r"^\d", name):
        return None

    # 유앤아이 계열이 아닌 clinic 명
    if is_non_yuanai_blog(name):
        return None

    # evt_branches.name 직접 일치
    if name in by_name:
        return by_name[name]

    # BLOG_SPECIAL 특수 케이스 (exact key)
    if name in BLOG_SPECIAL:
        return by_name.get(BLOG_SPECIAL[name])

    # "유앤XXX" 패턴 — 한글 음절 추출 후 분기 매핑
    #   예) "유앤강남 최적1" → core = "강남"
    #       "유앤하남미사 최적1" → core = "하남미사"
    #       "유앤창원3" → core = "창원"
    if name.startswith("유앤"):
        # 한글 유니코드 범위: AC00–D7A3 (완성형) + 3130–318F (자모) + FFA0–FFDC (반각)
        m = re.match(r"^유앤([가-힣㄰-㆏ﾠ-ￜ]+)", name)
        if m:
            core = m.group(1)  # 예: "강남", "하남미사"

            # BLOG_SPECIAL에 "유앤{core}" 키가 있으면 우선 적용
            yuanai_key = "유앤" + core
            if yuanai_key in BLOG_SPECIAL:
                return by_name.get(BLOG_SPECIAL[yuanai_key])

            # "core점" 으로 branch name 조합 시도
            candidate = core + "점"
            if candidate in by_name:
                return by_name[candidate]

            # short_name 직접 일치
            if core in by_short:
                return by_short[core]

    return None


def resolve_blog(branch_name: str, by_name: dict, by_short: dict):
    """blog_posts 행의 진입점 리졸버."""
    name = (branch_name or "").strip()
    if not name:
        return None
    if is_non_yuanai_blog(name):
        return None
    return map_blog(name, by_name, by_short)


def resolve_place(branch_name: str, by_name: dict, by_short: dict):
    """place_daily.branch_name → evt_branch_id 변환. "XXX유앤아이" 패턴 처리."""
    name = (branch_name or "").strip()
    if not name:
        return None

    # 특수 케이스 우선 적용
    if name in PLACE_SPECIAL:
        target = PLACE_SPECIAL[name]
        return by_name.get(target)

    # "XXX유앤아이" 패턴 → "XXX점"
    if name.endswith("유앤아이"):
        core = name[: -len("유앤아이")]  # 예: "강남"
        candidate = core + "점"
        if candidate in by_name:
            return by_name[candidate]
        if core in by_short:
            return by_short[core]

    # 직접 일치 폴백
    if name in by_name:
        return by_name[name]

    return None


def resolve_webpage(branch_name: str, by_name: dict, by_short: dict):
    """webpage_daily.branch_name → evt_branch_id 변환. "유앤아이의원 XXX점" 패턴 처리."""
    name = (branch_name or "").strip()
    if not name:
        return None

    PREFIX = "유앤아이의원 "
    if name.startswith(PREFIX):
        suffix = name[len(PREFIX):]  # 예: "강남점"
        # 특수 케이스 확인
        if suffix in WEBPAGE_SPECIAL:
            target = WEBPAGE_SPECIAL[suffix]
            return by_name.get(target) if target else None
        if suffix in by_name:
            return by_name[suffix]
        # "점" 접미사 제거 후 short_name 시도
        core = suffix.rstrip("점")
        if core in by_short:
            return by_short[core]

    # 직접 일치 폴백
    if name in by_name:
        return by_name[name]

    return None

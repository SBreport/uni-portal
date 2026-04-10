"""
블로그 데이터 가공 모듈 (재사용 가능, DB 의존 없음)

사용처:
  - blog/migrate_enrich.py  : 기존 데이터 일괄 가공
  - blog/import_csv.py      : 신규 CSV 임포트 시 자동 가공
  - api/routers/blog.py     : 웹 CSV 업로드 시 호출
"""

import re

# ── 상수 ──

POST_TYPE_MAIN_KEYWORDS = [
    "논문글", "정보성글", "홍보성글", "임상글", "키컨텐츠", "소개글",
]

# 이모지 유니코드 범위 패턴
_EMOJI_RE = re.compile(
    "["
    "\U0001F600-\U0001F64F"  # emoticons
    "\U0001F300-\U0001F5FF"  # symbols & pictographs
    "\U0001F680-\U0001F6FF"  # transport & map
    "\U0001F1E0-\U0001F1FF"  # flags
    "\U00002702-\U000027B0"  # dingbats
    "\U000024C2-\U0001F251"
    "\U0001f926-\U0001f937"
    "\U00010000-\U0010FFFF"
    "\u2640-\u2642"
    "\u2600-\u2B55"
    "\u200d"
    "\u23cf"
    "\u23e9"
    "\u231a"
    "\ufe0f"
    "\u20e3"
    "\u2934"
    "\u2935"
    "\u25aa-\u25fe"
    "\u2b05-\u2b07"
    "\u2b1b-\u2b1c"
    "\u3030"
    "\u303d"
    "\u3297"
    "\u3299"
    "\u23ed"  # ⏭
    "]+",
    flags=re.UNICODE,
)


# ── 개별 가공 함수 ──

def parse_content_number(val: str) -> dict:
    """
    '유앤창원 3' → {branch_name: '유앤창원', slot_number: '3'}
    '유앤7_7'   → {branch_name: '유앤7', slot_number: '7'}
    """
    val = val.strip()
    if not val:
        return {"branch_name": "", "slot_number": ""}
    # 패턴1: 공백 + 숫자 (유앤창원 3)
    m = re.match(r"(.+?)\s+(\d+)$", val)
    if m:
        return {"branch_name": m.group(1).strip(), "slot_number": m.group(2)}
    # 패턴2: 언더스코어 + 숫자 (유앤7_7)
    m = re.match(r"(.+?)_(\d+)$", val)
    if m:
        return {"branch_name": m.group(1).strip(), "slot_number": m.group(2)}
    # 숫자 없는 경우
    return {"branch_name": val, "slot_number": ""}


def normalize_post_type(val: str) -> dict:
    """
    '정보성글, 홍보성글' → {main: '정보성글', sub: '홍보성글'}
    '로컬최적1 - 메디썰' → {main: '최적', sub: '로컬최적1 - 메디썰'}
    """
    val = val.strip()
    if not val:
        return {"main": "", "sub": ""}

    parts = [p.strip() for p in val.split(",")]

    main = ""
    subs = []
    for p in parts:
        if not main and p in POST_TYPE_MAIN_KEYWORDS:
            main = p
        else:
            subs.append(p)

    # 대분류가 없고 최적 계정명이 있는 경우
    if not main and subs:
        first = subs[0]
        if any(kw in first for kw in ["최적", "NB", "준최", "배포", "알선"]):
            main = "최적"

    return {"main": main, "sub": ", ".join(subs) if subs else ""}


def parse_project(val: str) -> dict:
    """
    '26.3월 - 유앤아이 천안 (https://...)' → {month: '2026-03', branch: '유앤아이 천안'}
    '25.12월 - 하남미사 막글 작업 (...)' → {month: '2025-12', branch: '하남미사 막글 작업'}
    """
    val = val.strip()
    if not val:
        return {"month": "", "branch": ""}

    m = re.match(r"(\d+)\.(\d+)월\s*-\s*(.+?)(?:\s*\(https?://|\s*$)", val)
    if m:
        yy = int(m.group(1))
        mm = int(m.group(2))
        year = 2000 + yy if yy < 100 else yy
        branch = m.group(3).strip()
        return {"month": f"{year}-{mm:02d}", "branch": branch}

    return {"month": "", "branch": ""}


def clean_status(val: str) -> str:
    """'👏보고 완료' → '보고 완료'"""
    val = val.strip()
    if not val:
        return ""
    # 알려진 상태값 매핑 (이모지 포함 원본 → 정제본)
    _STATUS_MAP = {
        "보고 완료": "보고 완료",
        "발행 완료": "발행 완료",
        "예약 발행": "예약 발행",
        "진행 취소": "진행 취소",
        "밀림": "밀림",
    }
    for key, clean in _STATUS_MAP.items():
        if key in val:
            return clean
    # 매핑 안 되면 이모지 제거 시도
    cleaned = _EMOJI_RE.sub("", val).strip()
    return cleaned if cleaned else val


def clean_title(title: str, keyword: str = "", content_number: str = "") -> dict:
    """
    제목에서 URL/[출처] 제거, 빈 제목은 keyword → content_number 순으로 대체.
    Returns: {clean_title: str, needs_review: int}
    """
    original = title.strip()
    keyword = keyword.strip()
    content_number = content_number.strip()

    if not original:
        # scraped_title이 있으면 우선 사용 (스크래핑으로 수집된 실제 제목)
        fallback = keyword or content_number
        return {"clean_title": fallback, "needs_review": 1}

    cleaned = original

    # [출처] 이후 제거
    idx = cleaned.find("[출처]")
    if idx >= 0:
        cleaned = cleaned[:idx].strip()

    # 줄바꿈 + URL 패턴 제거 (줄바꿈 이후 전체 삭제)
    cleaned = re.sub(r"\n\s*https?://\S+.*$", "", cleaned, flags=re.DOTALL).strip()

    # [공지]\n 접두사 정리
    cleaned = re.sub(r"^\[공지\]\s*\n?\s*", "", cleaned).strip()

    # 텍스트에 직접 붙은 URL 제거 (예: "광명 셀르디엠https://blog.naver.com/...")
    # 한글/영문/숫자/공백 뒤에 바로 https:// 가 오는 패턴
    cleaned = re.sub(r"https?://\S+", "", cleaned).strip()

    # |작성자 ... 패턴 제거
    cleaned = re.sub(r"\|작성자\s*\S*", "", cleaned).strip()

    needs_review = 0
    if not cleaned:
        cleaned = keyword or content_number
        needs_review = 1

    return {"clean_title": cleaned, "needs_review": needs_review}


def split_author(val: str) -> dict:
    """'김다혜, 김보라' → {main: '김다혜', sub: '김보라'}"""
    val = val.strip()
    if not val:
        return {"main": "", "sub": ""}

    parts = [p.strip() for p in val.split(",")]
    main = parts[0]
    sub = ", ".join(parts[1:]) if len(parts) > 1 else ""
    return {"main": main, "sub": sub}


def enrich_row(row: dict) -> dict:
    """
    원본 행 dict를 받아 가공 컬럼 dict를 반환.

    입력 키: content_number, post_type, project, status, title, keyword, author,
             blog_channel (optional)
    출력 키: branch_name, slot_number, post_type_main, post_type_sub,
             project_month, project_branch, status_clean, clean_title,
             author_main, author_sub, needs_review
    """
    cn = parse_content_number(row.get("content_number", ""))
    pt = normalize_post_type(row.get("post_type", ""))
    pj = parse_project(row.get("project", ""))
    sc = clean_status(row.get("status", ""))
    ct = clean_title(row.get("title", ""), row.get("keyword", ""), row.get("content_number", ""))
    au = split_author(row.get("author", ""))

    needs_review = ct["needs_review"]
    # 비최적(br) 채널인데 제목이 비어있으면 추가 검토 필요
    channel = row.get("blog_channel", "")
    if channel != "opt" and not ct["clean_title"]:
        needs_review = 1

    return {
        "branch_name": cn["branch_name"],
        "slot_number": cn["slot_number"],
        "post_type_main": pt["main"],
        "post_type_sub": pt["sub"],
        "project_month": pj["month"],
        "project_branch": pj["branch"],
        "status_clean": sc,
        "clean_title": ct["clean_title"],
        "author_main": au["main"],
        "author_sub": au["sub"],
        "needs_review": needs_review,
    }

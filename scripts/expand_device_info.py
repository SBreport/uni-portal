"""
expand_device_info.py

Part A: 125개 미매칭 장비명을 device_info에 INSERT
Part B: equipment.device_info_id 컬럼 추가 후 전체 1811건 매칭

사용:
    python scripts/expand_device_info.py
"""

import json
import os
import re
import sqlite3
import sys
from datetime import datetime

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(_PROJECT_ROOT, "data", "equipment.db")

NOW = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# ─────────────────────────────────────────────────────────────────────────────
# 카테고리 매핑 (equipment.categories → device_info.category)
# ─────────────────────────────────────────────────────────────────────────────

CATEGORY_MAP = {
    "리프팅": "리프팅",
    "비만": "바디",
    "색소": "색소",
    "여드름 치료": "여드름",
    "여드름 흉터": "여드름",
    "주사 시술": "주사/부스터",
    "기타": "기타",
    "제모": "제모",
}

# ─────────────────────────────────────────────────────────────────────────────
# Part A: 등록할 신규 device_info 항목 정의
# 형식: (canonical_name, device_info_category, summary, aliases_list)
# ─────────────────────────────────────────────────────────────────────────────

NEW_DEVICES = [
    # ── 리프팅 ──────────────────────────────────────────────────────────────
    ("컴포트듀얼", "리프팅",
     "듀얼 핸들 초음파 리프팅 장비",
     ["듀얼컴포트"]),
    ("D리프팅", "리프팅",
     "초음파 HIFU 계열 리프팅 장비 (앤코어 제조)",
     ["D 리프팅(엔코어)", "d 리프팅(앤코어)", "DEEP", "DEEP PRO", "Deep"]),
    ("네오페이스", "리프팅",
     "HIFU 계열 페이스 리프팅 장비",
     []),
    ("네오페이스(바디)", "바디",
     "HIFU 계열 바디 리프팅 장비",
     []),
    ("이브시너지", "리프팅",
     "복합 에너지 리프팅·피부 활성화 장비",
     []),
    ("르반타", "리프팅",
     "HIFU 계열 리프팅 장비",
     []),
    ("스킨아우라", "리프팅",
     "초음파 피부 활성화 리프팅 장비",
     []),
    ("써니", "리프팅",
     "리프팅 전용 장비",
     []),
    ("잼버실", "리프팅",
     "초음파 리프팅 장비",
     []),
    ("코레지", "리프팅",
     "HIFU 계열 리프팅 장비",
     []),
    ("쿨소닉", "리프팅",
     "초음파 냉각 리프팅 장비",
     []),
    ("튠페이스", "리프팅",
     "RF/초음파 리프팅 장비",
     []),
    ("트리니티", "리프팅",
     "복합 에너지 리프팅 장비",
     []),
    # ── 바디(비만) ───────────────────────────────────────────────────────────
    ("엑스웨이브", "바디",
     "체외충격파(ESWT) 기반 바디 시술 장비",
     ["엑스웨이브(체외충격파)"]),
    ("디톡스돔", "바디",
     "온열·원적외선 바디 디톡스 장비",
     []),
    ("라필로", "바디",
     "바디 지방 분해 레이저 장비",
     []),
    ("메가스키니", "바디",
     "EMS/RF 기반 바디 슬리밍 장비",
     []),
    ("아큐커브", "바디",
     "냉각 지방 분해 바디 장비",
     []),
    ("엠브이핏", "바디",
     "EMS 바디 슬리밍 장비",
     []),
    ("울핏", "바디",
     "HIFU 바디 리프팅·슬리밍 장비",
     []),
    ("웨이브핏", "바디",
     "체외충격파·진동 기반 바디 슬리밍 장비",
     []),
    ("위고비", "바디",
     "세마글루타이드 계열 비만 치료 주사제",
     []),
    ("마운자로", "바디",
     "티르제파타이드 계열 비만 치료 주사제",
     []),
    ("인퓨전 펌프", "바디",
     "정맥주사 인퓨전 제어 장비",
     []),
    ("트리플바디", "바디",
     "복합 에너지 바디 슬리밍 장비",
     []),
    ("파셀라", "바디",
     "레이저 기반 바디 지방 분해 장비",
     []),
    # ── 색소 ─────────────────────────────────────────────────────────────────
    ("GV laser", "색소",
     "그린·바이올렛 파장 색소 레이저 장비",
     []),
    ("더미V레이저", "색소",
     "색소 제거용 레이저 장비",
     []),
    ("디오레듀얼", "색소",
     "듀얼 파장 다이오드 레이저 (색소·여드름 복합)",
     []),
    ("로터스 3", "색소",
     "피코초 레이저 3세대 장비",
     []),
    ("리팟레이저", "색소",
     "색소·피부 재생 레이저 장비",
     []),
    ("브라이톤", "색소",
     "색소 개선 레이저 장비",
     []),
    ("브이레이저", "색소",
     "다목적 레이저 장비 (색소·제모 겸용)",
     []),
    ("아비오", "색소",
     "색소 레이저 장비",
     []),
    ("엘라덤", "색소",
     "색소 개선·피부 재생 레이저 장비",
     []),
    ("큐라스", "색소",
     "피코초 레이저 색소 장비",
     []),
    ("파스텔토닝", "색소",
     "저출력 레이저 토닝 장비",
     ["파스텔"]),
    # ── 여드름 ───────────────────────────────────────────────────────────────
    ("더마아크네", "여드름",
     "여드름 치료 전용 레이저/고주파 장비",
     ["더마아크네(테라클리어)"]),
    ("더블타이트", "여드름",
     "RF 기반 여드름·흉터·리프팅 복합 장비",
     []),
    ("미라클리어", "여드름",
     "여드름 피지 제어 레이저 장비",
     []),
    ("미라클필", "여드름",
     "여드름 화학 박피 필링 제품",
     []),
    ("아트레이저", "여드름",
     "여드름 치료용 레이저 장비",
     []),
    ("카프리 레이저", "여드름",
     "여드름·피지 제어 레이저 장비",
     []),
    ("키오머", "여드름",
     "여드름 치료 장비",
     []),
    ("로투스2", "여드름",
     "피코초 레이저 2세대 장비 (여드름 흉터 치료)",
     []),
    ("로투스3", "여드름",
     "피코초 레이저 3세대 장비 (여드름 흉터 치료)",
     []),
    ("라비앙", "여드름",
     "여드름 흉터 치료 레이저 장비",
     []),
    ("미라젯", "여드름",
     "여드름 흉터 치료 장비 (마이크로 니들링/제트 타입)",
     []),
    ("미모레이저", "여드름",
     "여드름 흉터 피부 재생 레이저 장비",
     []),
    ("뷰레인", "여드름",
     "여드름 흉터·피부 재생 장비",
     []),
    ("아이콘레이저", "여드름",
     "여드름 흉터·색소 복합 레이저 장비",
     []),
    ("에어다이섹터", "여드름",
     "서브시전(에어 다이섹터) 여드름 흉터 치료 장비",
     []),
    ("큐어젯", "여드름",
     "여드름 흉터 치료 장비",
     []),
    ("플로라셀", "여드름",
     "여드름 흉터 재생 레이저 장비",
     []),
    # ── 주사/부스터 ──────────────────────────────────────────────────────────
    ("고우리", "주사/부스터",
     "피부 보습·재생 스킨부스터 주사제",
     []),
    ("리바이브", "주사/부스터",
     "피부 재생·보습 스킨부스터 주사제",
     ["리바이브 (스킨부스터)", "리바이브 (스킨 부스터)"]),
    ("리즈네", "주사/부스터",
     "피부 재생 스킨부스터 주사제",
     ["리즈네  (스킨부스터)", "리즈네 (스킨부스터)"]),
    ("벨라콜린", "주사/부스터",
     "지방 분해 주사제",
     []),
    ("미라콜", "주사/부스터",
     "피부 재생 스킨부스터 주사제",
     []),
    ("브이올렛", "주사/부스터",
     "피부 미백·활성화 주사제",
     []),
    ("순백주사", "주사/부스터",
     "피부 미백 복합 주사제",
     []),
    ("채움", "주사/부스터",
     "필러 계열 피부 충전 주사제",
     []),
    ("엘스코", "주사/부스터",
     "피부 재생 스킨부스터 주사제",
     []),
    ("큐오필", "주사/부스터",
     "피부 보습·재생 주사제",
     []),
    ("노바스템", "주사/부스터",
     "줄기세포 기반 피부 재생 주사제",
     []),
    ("에스테필", "주사/부스터",
     "피부 재생 스킨부스터 주사제",
     ["에스테필 (스킨부스터)"]),
    ("아기주사", "주사/부스터",
     "피부 보습·진정 복합 주사제 (통칭)",
     []),
    ("사이모신알파", "주사/부스터",
     "면역 조절 펩타이드 주사제",
     ["사이모신알파 Ⅰ"]),
    ("줄기세포주사", "주사/부스터",
     "줄기세포 기반 피부·전신 재생 주사제",
     ["줄기세포 (피부 주사, IV)"]),
    ("티파니 주사", "주사/부스터",
     "피부 미백·재생 복합 주사제",
     []),
    ("피부재생힐러", "주사/부스터",
     "피부 재생 촉진 주사제",
     []),
    ("잔주름 개선주사", "주사/부스터",
     "잔주름 개선용 필러·부스터 주사제",
     []),
    ("이중턱 개선주사", "주사/부스터",
     "이중턱 지방 분해 주사제",
     []),
    ("다이아 주사", "주사/부스터",
     "피부 재생·미백 복합 주사제",
     []),
    ("릴리이드", "주사/부스터",
     "피부 재생 스킨부스터 주사제",
     ["릴리이드 (스킨부스터)"]),
    ("릴리이드M", "주사/부스터",
     "릴리이드 M 모델 스킨부스터 주사제",
     ["릴리이드M (스킨부스터)"]),
    ("리제반", "주사/부스터",
     "피부 재생 스킨부스터 주사제",
     ["리제반 (스킨 부스터)", "리제반(재고소진 시 종료)"]),
    ("뉴디엔", "주사/부스터",
     "피부 재생 주사제",
     ["뉴디엔 (스킨부스터)"]),
    ("힐로웨이브", "주사/부스터",
     "피부 보습·탄력 스킨부스터 주사제",
     ["힐로웨이브 (스킨부스터)", "힐로웨이브 (스킨 부스터)"]),
    ("플라비셀 방탄주사", "주사/부스터",
     "고농도 복합 영양 스킨부스터 주사제",
     ["플라비셀 방탄주사(스킨부스터)"]),
    ("하이쿡스", "주사/부스터",
     "피부 재생·보습 스킨부스터 주사제",
     []),
    # ── 기타/소모품 ──────────────────────────────────────────────────────────
    ("스티머", "기타",
     "피부 증기·수분 공급 보조 장비",
     []),
    ("고주파기기", "기타",
     "고주파 피부 관리 기기 (일반 관리용)",
     []),
    ("확대경", "기타",
     "피부 확대 관찰 보조 기기",
     []),
    ("인바디", "기타",
     "신체 성분 분석 장비 (InBody)",
     []),
    ("산소테라피", "기타",
     "산소 고압 피부 공급 관리 장비",
     ["산소테라피 (옥시젠슈티컬스의 오투플러스 최신장비"]),
    ("수분관리", "기타",
     "피부 수분 공급 관리 장비/프로그램",
     []),
    ("바이오라이트3", "기타",
     "생체 활성화 LED 복합 관리 장비 3세대",
     []),
    ("스마트룩스", "기타",
     "피부 분석 스마트 광학 기기",
     []),
    ("리젠X", "기타",
     "피부 재생 복합 관리 장비",
     []),
    ("리쥬메이트", "기타",
     "피부 재생·보습 관리 장비",
     []),
    ("오니코레이저", "기타",
     "네일(조갑) 진균 치료 레이저 장비",
     []),
    ("위코우노", "기타",
     "피부 관리 복합 장비",
     []),
    ("스킨블리플러스쿨", "기타",
     "피부 쿨링·진정 복합 관리 장비",
     []),
    ("리들부스터", "기타",
     "마이크로 니들 리들 부스터 장비",
     []),
    ("히라셀", "기타",
     "피부 관리 복합 장비",
     []),
    # ── 기타 (기존 기타 분류 중 장비로 확인된 것들) ─────────────────────────
    ("에어녹스", "기타",
     "진정 마취 가스(아산화질소) 공급 장비",
     ["에어녹스 (가스 마취)", "에어녹스(진정마취장비)"]),
    ("써마트릭스", "기타",
     "RF 기반 피부 재생·탄력 장비",
     []),
    ("헬륨레이저", "기타",
     "헬륨 가스 레이저 피부 진정·재생 장비",
     []),
    ("트라이덤", "기타",
     "RF 캐뉼라 흉터·주름 치료 장비",
     ["트라이덤(RF캐뉼라 ) 흉터및 깊은 주름, 목전체 탄력목적시술 가능",
      "트라이덤(UM-101)"]),
    # ── 기타에서 써마트릭스가 이미 기타 ────────────────────────────────────
    # 이미 위에 포함됨
    # ── 종기기(기타 → 기타) ─────────────────────────────────────────────────
]

# ─────────────────────────────────────────────────────────────────────────────
# 헬퍼 함수
# ─────────────────────────────────────────────────────────────────────────────

def normalize_key(text: str) -> str:
    """비교용 정규화: 소문자 + 공백 제거."""
    return re.sub(r"\s+", "", text.lower().strip())


def clean_name(name: str) -> str:
    """장비명에서 괄호 주석 제거하여 정식명 반환."""
    # 괄호 안 내용이 부가 설명인 경우만 제거
    # 예: "에어녹스 (가스 마취)" → "에어녹스"
    # 단, "로투스 3" 같은 버전 번호는 유지
    cleaned = re.sub(r"\s*\([^)]*\)", "", name).strip()
    # 빈 결과 방지
    return cleaned if cleaned else name


def build_lookup(conn: sqlite3.Connection) -> dict:
    """device_info의 name + 모든 alias → device_info_id 매핑 반환."""
    c = conn.cursor()
    c.execute("SELECT id, name, aliases FROM device_info")
    rows = c.fetchall()
    lookup = {}
    for did, dname, aliases_raw in rows:
        # 정식명
        key = normalize_key(dname)
        lookup[key] = did
        # 별칭
        if aliases_raw:
            try:
                if aliases_raw.strip().startswith("["):
                    aliases = json.loads(aliases_raw)
                else:
                    aliases = [a.strip() for a in aliases_raw.split(",")]
                for a in aliases:
                    if a:
                        lookup[normalize_key(a)] = did
            except Exception:
                pass
    return lookup


# ─────────────────────────────────────────────────────────────────────────────
# Part A: INSERT new device_info entries
# ─────────────────────────────────────────────────────────────────────────────

def part_a_insert(conn: sqlite3.Connection) -> None:
    c = conn.cursor()
    inserted = 0
    skipped = 0

    print("\n[Part A] device_info 신규 등록")
    print("=" * 60)

    for canonical, category, summary, aliases in NEW_DEVICES:
        aliases_json = json.dumps(aliases, ensure_ascii=False)
        try:
            c.execute(
                """
                INSERT OR IGNORE INTO device_info
                    (name, category, summary, aliases, is_verified, created_at, updated_at)
                VALUES (?, ?, ?, ?, 0, ?, ?)
                """,
                (canonical, category, summary, aliases_json, NOW, NOW),
            )
            if c.rowcount > 0:
                inserted += 1
                print(f"  [INSERT] {canonical!r}  ({category})")
            else:
                skipped += 1
                print(f"  [SKIP]   {canonical!r}  (이미 존재)")
        except Exception as e:
            print(f"  [ERROR]  {canonical!r}: {e}")

    conn.commit()
    print(f"\n  → 신규 등록: {inserted}건, 스킵: {skipped}건")


# ─────────────────────────────────────────────────────────────────────────────
# Part B: equipment.device_info_id 컬럼 추가 및 매칭
# ─────────────────────────────────────────────────────────────────────────────

def part_b_add_column(conn: sqlite3.Connection) -> None:
    c = conn.cursor()
    try:
        c.execute("ALTER TABLE equipment ADD COLUMN device_info_id INTEGER REFERENCES device_info(id)")
        conn.commit()
        print("\n[Part B] equipment.device_info_id 컬럼 추가 완료")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e).lower():
            print("\n[Part B] equipment.device_info_id 이미 존재")
        else:
            raise


def part_b_match(conn: sqlite3.Connection) -> None:
    c = conn.cursor()

    print("\n[Part B] equipment 행 매칭 시작")
    print("=" * 60)

    # 최신 lookup 빌드 (Part A 삽입 포함)
    lookup = build_lookup(conn)
    print(f"  lookup 키 수: {len(lookup)}")

    # 모든 device_info 정식명 목록 (substring 매칭용)
    c.execute("SELECT id, name FROM device_info")
    all_devices = [(did, dname, normalize_key(dname)) for did, dname in c.fetchall()]

    # 전체 equipment 행 가져오기
    c.execute("SELECT id, name FROM equipment")
    eq_rows = c.fetchall()
    print(f"  equipment 전체: {len(eq_rows)}건")

    matched = 0
    unmatched = []

    updates = []
    for eid, ename in eq_rows:
        did = _find_device_id(ename, lookup, all_devices)
        if did is not None:
            updates.append((did, eid))
            matched += 1
        else:
            unmatched.append(ename)

    # bulk UPDATE
    c.executemany("UPDATE equipment SET device_info_id = ? WHERE id = ?", updates)
    conn.commit()

    print(f"\n  매칭 성공: {matched}건 / {len(eq_rows)}건")
    print(f"  미매칭:   {len(unmatched)}건")
    if unmatched:
        print("\n  [미매칭 장비명 목록]")
        seen = set()
        for n in sorted(set(unmatched)):
            print(f"    - {n!r}")


def _find_device_id(
    ename: str,
    lookup: dict,
    all_devices: list,
) -> int | None:
    """장비명에서 device_info_id를 찾는다 (3단계 매칭)."""
    raw_key = normalize_key(ename)

    # 1) 정확한 매칭 (name 또는 alias 포함)
    if raw_key in lookup:
        return lookup[raw_key]

    # 2) 괄호 제거 후 재시도
    cleaned = normalize_key(clean_name(ename))
    if cleaned and cleaned in lookup:
        return lookup[cleaned]

    # 3) 부분 포함 매칭: device_info 정식명이 장비명 안에 있거나 그 반대
    #    단, 너무 짧은 키(2자 미만)는 제외
    best_did = None
    best_len = 0
    for did, dname, dkey in all_devices:
        if len(dkey) < 2:
            continue
        if dkey in raw_key or dkey in cleaned:
            if len(dkey) > best_len:
                best_len = len(dkey)
                best_did = did
        elif raw_key and raw_key in dkey:
            if len(raw_key) > best_len:
                best_len = len(raw_key)
                best_did = did

    return best_did


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print(f"DB: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")

    # Part A
    part_a_insert(conn)

    # Part B
    part_b_add_column(conn)
    part_b_match(conn)

    # 최종 통계
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM device_info")
    total_di = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM equipment WHERE device_info_id IS NOT NULL")
    linked = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM equipment")
    total_eq = c.fetchone()[0]

    print(f"\n{'=' * 60}")
    print(f"완료 요약")
    print(f"  device_info 총 항목: {total_di}건")
    print(f"  equipment 연결 완료: {linked} / {total_eq}건 ({linked/total_eq*100:.1f}%)")
    print(f"{'=' * 60}")

    conn.close()


if __name__ == "__main__":
    main()
